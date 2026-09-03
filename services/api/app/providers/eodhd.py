from __future__ import annotations

import math
import os
import re
import time
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any
from urllib.parse import quote

import httpx

from ..fundamental_catalog import FUNDAMENTAL_FIELD_IDS
from ..fundamental_store import FundamentalStore


EODHD_FUNDAMENTALS_URL = "https://eodhd.com/api/v1.1/fundamentals"
EODHD_PROVIDER_NAME = "EODHD Fundamentals API v1.1"
INDIAN_CRORE = 10_000_000
MAX_SYNC_SYMBOLS = 25

_SYMBOL_PATTERN = re.compile(r"^[A-Z0-9._&-]{1,50}$")
_EXCHANGE_PATTERN = re.compile(r"^[A-Z0-9_-]{1,20}$")
_MISSING_TEXT = {"", "-", "na", "n/a", "nan", "none", "null"}
_PLACEHOLDER_TOKENS = {
    "replace_with_eodhd_api_token",
    "replace_with_api_token",
    "your_api_token",
    "your_token",
}


class EodhdProviderError(RuntimeError):
    """Safe provider failure that never contains the API token."""


@dataclass(frozen=True)
class EodhdMappedSnapshot:
    symbol: str
    ticker: str
    as_of: str
    currency: str | None
    values: dict[str, float]
    skipped_currency_amounts: bool

    def import_row(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "as_of": self.as_of,
            "source": f"{EODHD_PROVIDER_NAME} ({self.ticker})",
            "values": self.values,
        }


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, str):
        value = value.strip()
        if value.casefold() in _MISSING_TEXT:
            return None
        value = value.replace(",", "")
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _first_number(source: Mapping[str, Any], *keys: str) -> float | None:
    for key in keys:
        result = _number(source.get(key))
        if result is not None:
            return result
    return None


def _iso_date(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    candidate = value.strip()[:10]
    try:
        date.fromisoformat(candidate)
    except ValueError:
        return None
    return candidate


def _reports(payload: Mapping[str, Any], statement: str, cadence: str) -> list[Mapping[str, Any]]:
    financials = _mapping(payload.get("Financials"))
    statement_data = _mapping(financials.get(statement))
    report_data = statement_data.get(cadence)
    if isinstance(report_data, Mapping):
        rows = [row for row in report_data.values() if isinstance(row, Mapping)]
    elif isinstance(report_data, list):
        rows = [row for row in report_data if isinstance(row, Mapping)]
    else:
        rows = []
    return sorted(
        rows,
        key=lambda row: _iso_date(row.get("date")) or "0001-01-01",
        reverse=True,
    )


def _complete_sum(
    reports: list[Mapping[str, Any]],
    keys: tuple[str, ...],
    count: int,
    *,
    offset: int = 0,
) -> float | None:
    selected = reports[offset : offset + count]
    if len(selected) != count:
        return None
    numbers = [_first_number(report, *keys) for report in selected]
    if any(value is None for value in numbers):
        return None
    return sum(value for value in numbers if value is not None)


def _average_reports(
    reports: list[Mapping[str, Any]],
    keys: tuple[str, ...],
) -> float | None:
    if not reports:
        return None
    current = _first_number(reports[0], *keys)
    if current is None:
        return None
    if len(reports) < 2:
        return current
    previous = _first_number(reports[1], *keys)
    return current if previous is None else (current + previous) / 2


def _percent(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator * 100


def _growth_percent(current: float | None, previous: float | None) -> float | None:
    if current is None or previous in (None, 0):
        return None
    return (current - previous) / abs(previous) * 100


def _ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def _total_debt(report: Mapping[str, Any]) -> float | None:
    total = _first_number(report, "shortLongTermDebtTotal", "totalDebt")
    if total is not None:
        return total
    short_term = _first_number(report, "shortTermDebt", "shortLongTermDebt")
    long_term = _first_number(report, "longTermDebt", "longTermDebtTotal")
    if short_term is None and long_term is None:
        return None
    return (short_term or 0) + (long_term or 0)


def _currency(payload: Mapping[str, Any]) -> str | None:
    general = _mapping(payload.get("General"))
    candidate = general.get("CurrencyCode")
    if isinstance(candidate, str) and candidate.strip():
        return candidate.strip().upper()
    financials = _mapping(payload.get("Financials"))
    for statement in ("Income_Statement", "Balance_Sheet", "Cash_Flow"):
        value = _mapping(financials.get(statement)).get("currency_symbol")
        if isinstance(value, str) and value.strip():
            normalized = value.strip().upper()
            return "INR" if normalized in {"₹", "RS", "RS."} else normalized
    return None


def _as_of(payload: Mapping[str, Any], report_groups: Iterable[list[Mapping[str, Any]]]) -> str:
    general = _mapping(payload.get("General"))
    highlights = _mapping(payload.get("Highlights"))
    candidates = [
        _iso_date(general.get("UpdatedAt")),
        _iso_date(highlights.get("MostRecentQuarter")),
    ]
    for reports in report_groups:
        if reports:
            candidates.extend(
                (_iso_date(reports[0].get("date")), _iso_date(reports[0].get("filing_date")))
            )
    valid = [candidate for candidate in candidates if candidate is not None]
    if not valid:
        raise EodhdProviderError("EODHD returned data without a usable as-of date.")
    return max(valid)


def map_eodhd_fundamentals(
    payload: Mapping[str, Any],
    *,
    symbol: str,
    ticker: str,
) -> EodhdMappedSnapshot:
    """Map only equivalent EODHD facts into the Chartink-style field catalog.

    EODHD monetary statement values are raw reporting-currency units. This
    India-first screener stores those values in INR crore. Currency-sensitive
    values are therefore skipped for non-INR responses instead of silently
    mixing dollars, rupees and different magnitude scales.
    """

    if not isinstance(payload, Mapping):
        raise EodhdProviderError("EODHD returned an invalid fundamentals document.")
    if payload.get("error") or payload.get("errors"):
        raise EodhdProviderError("EODHD rejected the fundamentals request.")

    general = _mapping(payload.get("General"))
    highlights = _mapping(payload.get("Highlights"))
    valuation = _mapping(payload.get("Valuation"))

    income_yearly = _reports(payload, "Income_Statement", "yearly")
    income_quarterly = _reports(payload, "Income_Statement", "quarterly")
    balance_yearly = _reports(payload, "Balance_Sheet", "yearly")
    balance_quarterly = _reports(payload, "Balance_Sheet", "quarterly")
    cashflow_yearly = _reports(payload, "Cash_Flow", "yearly")
    cashflow_quarterly = _reports(payload, "Cash_Flow", "quarterly")
    report_groups = (
        income_yearly,
        income_quarterly,
        balance_yearly,
        balance_quarterly,
        cashflow_yearly,
        cashflow_quarterly,
    )

    currency = _currency(payload)
    is_inr = currency == "INR"
    values: dict[str, float] = {}

    def put(field_id: str, value: Any) -> None:
        number = _number(value)
        if number is None or field_id in values:
            return
        if field_id not in FUNDAMENTAL_FIELD_IDS:
            raise RuntimeError(f"EODHD mapping targets unknown field {field_id}.")
        values[field_id] = number

    def put_percent_fraction(field_id: str, value: Any) -> None:
        number = _number(value)
        put(field_id, None if number is None else number * 100)

    def put_inr_crore(field_id: str, value: Any) -> None:
        number = _number(value)
        if is_inr and number is not None:
            put(field_id, number / INDIAN_CRORE)

    put("fund_ttm_pe", _first_number(valuation, "TrailingPE") or _first_number(highlights, "PERatio"))
    put_percent_fraction("fund_ttm_operating_profit_margin", highlights.get("OperatingMarginTTM"))
    put_percent_fraction("fund_return_on_assets", highlights.get("ReturnOnAssetsTTM"))
    put_percent_fraction("fund_return_on_assets_annualised", highlights.get("ReturnOnAssetsTTM"))
    put_percent_fraction("fund_return_on_net_worth_percentage", highlights.get("ReturnOnEquityTTM"))
    put(
        "fund_ttm_gross_profit_margin",
        _percent(
            _first_number(highlights, "GrossProfitTTM"),
            _first_number(highlights, "RevenueTTM"),
        ),
    )
    put("fund_price_to_book_value", _first_number(valuation, "PriceBookMRQ"))
    put("fund_number_of_employees", general.get("FullTimeEmployees"))

    if is_inr:
        put("fund_ttm_eps", _first_number(highlights, "DilutedEpsTTM", "EarningsShare"))
        put("fund_book_value", highlights.get("BookValue"))
        put("fund_dividend_per_share_rupees", highlights.get("DividendShare"))
        put_inr_crore("fund_market_cap", highlights.get("MarketCapitalization"))
        put_inr_crore("fund_ttm_sales", highlights.get("RevenueTTM"))
        put_inr_crore("fund_ttm_gross_profit", highlights.get("GrossProfitTTM"))

    ttm_revenue = _complete_sum(income_quarterly, ("totalRevenue",), 4)
    ttm_gross_profit = _complete_sum(income_quarterly, ("grossProfit",), 4)
    ttm_operating_profit = _complete_sum(income_quarterly, ("operatingIncome",), 4)
    ttm_net_profit = _complete_sum(income_quarterly, ("netIncome",), 4)
    ttm_depreciation = _complete_sum(
        cashflow_quarterly,
        ("depreciation", "depreciationAndAmortization"),
        4,
    )
    if is_inr:
        put_inr_crore("fund_ttm_sales", ttm_revenue)
        put_inr_crore("fund_ttm_gross_profit", ttm_gross_profit)
        put_inr_crore("fund_ttm_operating_profit", ttm_operating_profit)
        put_inr_crore("fund_ttm_net_profit", ttm_net_profit)
        put_inr_crore("fund_ttm_depreciation", ttm_depreciation)
    put("fund_ttm_gross_profit_margin", _percent(ttm_gross_profit, ttm_revenue))
    put("fund_ttm_operating_profit_margin", _percent(ttm_operating_profit, ttm_revenue))

    if len(income_quarterly) >= 8:
        prior_ttm_net_profit = _complete_sum(income_quarterly, ("netIncome",), 4, offset=4)
        put("fund_ttm_net_profit_variance", _growth_percent(ttm_net_profit, prior_ttm_net_profit))

    latest_year = income_yearly[0] if income_yearly else {}
    previous_year = income_yearly[1] if len(income_yearly) > 1 else {}
    latest_quarter = income_quarterly[0] if income_quarterly else {}
    year_ago_quarter = income_quarterly[4] if len(income_quarterly) > 4 else {}

    yearly_revenue = _first_number(latest_year, "totalRevenue")
    yearly_net_profit = _first_number(latest_year, "netIncome")
    yearly_gross_profit = _first_number(latest_year, "grossProfit")
    yearly_operating_profit = _first_number(latest_year, "operatingIncome")
    previous_year_net_profit = _first_number(previous_year, "netIncome")
    if is_inr:
        put_inr_crore("fund_sales_turnover_yearly", yearly_revenue)
        put_inr_crore("fund_net_profit_yearly", yearly_net_profit)
    put("fund_net_profit_variance_yr", _growth_percent(yearly_net_profit, previous_year_net_profit))
    put("fund_operating_profit_margin_yr", _percent(yearly_operating_profit, yearly_revenue))
    put("fund_gross_profit_margin", _percent(yearly_gross_profit, yearly_revenue))

    yearly_eps = _first_number(latest_year, "dilutedEPS", "basicEPS")
    previous_year_eps = _first_number(previous_year, "dilutedEPS", "basicEPS")
    if is_inr:
        put("fund_earning_per_share_eps", yearly_eps)
        put("fund_prev_year_eps", previous_year_eps)

    quarterly_revenue = _first_number(latest_quarter, "totalRevenue")
    quarterly_net_profit = _first_number(latest_quarter, "netIncome")
    quarterly_gross_profit = _first_number(latest_quarter, "grossProfit")
    quarterly_operating_profit = _first_number(latest_quarter, "operatingIncome")
    if is_inr:
        put_inr_crore("fund_net_sales_quarter", quarterly_revenue)
        put_inr_crore("fund_net_profit_quarter", quarterly_net_profit)
    put(
        "fund_net_profit_variance_qr",
        _growth_percent(quarterly_net_profit, _first_number(year_ago_quarter, "netIncome")),
    )
    put("fund_operating_profit_margin_qr", _percent(quarterly_operating_profit, quarterly_revenue))

    latest_balance = balance_quarterly[0] if balance_quarterly else (balance_yearly[0] if balance_yearly else {})
    latest_balance_year = balance_yearly[0] if balance_yearly else {}
    if is_inr:
        put_inr_crore("fund_networth", _first_number(latest_balance, "totalStockholderEquity"))
        put_inr_crore("fund_equity", _first_number(latest_balance, "capitalStock", "commonStock"))

    annual_cash = _first_number(latest_balance_year, "cashAndEquivalents", "cash")
    annual_shares = _first_number(latest_balance_year, "commonStockSharesOutstanding", "commonStockSharesIssued")
    quarterly_cash = _first_number(latest_balance, "cashAndEquivalents", "cash")
    quarterly_shares = _first_number(latest_balance, "commonStockSharesOutstanding", "commonStockSharesIssued")
    if is_inr:
        put("fund_cash_per_share_yr", _ratio(annual_cash, annual_shares))
        put("fund_cash_per_share_qr", _ratio(quarterly_cash, quarterly_shares))

    equity = _first_number(latest_balance_year, "totalStockholderEquity")
    total_debt = _total_debt(latest_balance_year)
    long_term_debt = _first_number(latest_balance_year, "longTermDebt", "longTermDebtTotal")
    current_assets = _first_number(latest_balance_year, "totalCurrentAssets")
    current_liabilities = _first_number(latest_balance_year, "totalCurrentLiabilities")
    put("fund_debt_equity_ratio", _ratio(total_debt, equity))
    put("fund_long_term_debt_equity_ratio", _ratio(long_term_debt, equity))
    put("fund_current_ratio", _ratio(current_assets, current_liabilities))

    average_ppe = _average_reports(balance_yearly, ("propertyPlantAndEquipmentNet", "propertyPlantEquipment"))
    average_inventory = _average_reports(balance_yearly, ("inventory",))
    average_receivables = _average_reports(balance_yearly, ("netReceivables",))
    average_assets = _average_reports(balance_yearly, ("totalAssets",))
    cost_of_revenue = _first_number(latest_year, "costOfRevenue")
    ebit = _first_number(latest_year, "ebit")
    interest_expense = _first_number(latest_year, "interestExpense", "interestExpenseNonOperating")
    put("fund_fixed_assets_turnover_ratio", _ratio(yearly_revenue, average_ppe))
    put("fund_inventory_turnover_ratio", _ratio(cost_of_revenue, average_inventory))
    put("fund_debtors_turnover_ratio", _ratio(yearly_revenue, average_receivables))
    put("fund_total_assets_turnover_ratios", _ratio(yearly_revenue, average_assets))
    put("fund_interest_cover", _ratio(ebit, abs(interest_expense) if interest_expense is not None else None))
    put("fund_operating_profit_margin_percentage", _percent(yearly_operating_profit, yearly_revenue))
    put("fund_profit_before_interest_and_tax_margin_percentage", _percent(ebit, yearly_revenue))
    put("fund_gross_profit_margin_percentage", _percent(yearly_gross_profit, yearly_revenue))
    capital_employed = None
    total_assets = _first_number(latest_balance_year, "totalAssets")
    if total_assets is not None and current_liabilities is not None:
        capital_employed = total_assets - current_liabilities
    put("fund_return_on_capital_employed_percentage", _percent(ebit, capital_employed))

    latest_cashflow = cashflow_yearly[0] if cashflow_yearly else {}
    if is_inr:
        cashflow_mappings = {
            "fund_net_cash_from_operating_activities": ("totalCashFromOperatingActivities",),
            "fund_purchased_of_fixed_assets": ("capitalExpenditures",),
            "fund_net_cash_used_in_investing_activities": ("totalCashflowsFromInvestingActivities",),
            "fund_proceeds_from_issue_of_shares_including_share_premium": ("issuanceOfCapitalStock",),
            "fund_dividend_paid": ("dividendsPaid",),
            "fund_net_cash_used_in_financing_activities": ("totalCashFromFinancingActivities",),
            "fund_net_increase_or_decrease_in_cash_and_cash_equivalent": ("cashAndCashEquivalentsChanges", "changeInCash"),
            "fund_cash_and_cash_equivalents_at_beginning_of_the_year": ("beginPeriodCashFlow",),
            "fund_cash_and_cash_equivalents_at_end_of_the_year": ("endPeriodCashFlow",),
            "fund_interest_paid": ("interestPaid",),
        }
        for field_id, keys in cashflow_mappings.items():
            put_inr_crore(field_id, _first_number(latest_cashflow, *keys))

    return EodhdMappedSnapshot(
        symbol=symbol,
        ticker=ticker,
        as_of=_as_of(payload, report_groups),
        currency=currency,
        values=values,
        skipped_currency_amounts=not is_inr,
    )


JsonFetcher = Callable[[str], Mapping[str, Any]]


class EodhdFundamentalsProvider:
    """Backend-only EODHD client and normalized fundamentals importer."""

    def __init__(
        self,
        *,
        api_token: str | None = None,
        default_exchange: str | None = None,
        timeout_seconds: float | None = None,
        fetch_json: JsonFetcher | None = None,
    ) -> None:
        self.api_token = (api_token if api_token is not None else os.getenv("EODHD_API_TOKEN", "")).strip()
        self.default_exchange = (
            default_exchange if default_exchange is not None else os.getenv("EODHD_DEFAULT_EXCHANGE", "NSE")
        ).strip().upper()
        configured_timeout = timeout_seconds
        if configured_timeout is None:
            try:
                configured_timeout = float(os.getenv("EODHD_TIMEOUT_SECONDS", "20"))
            except ValueError:
                configured_timeout = 20.0
        self.timeout_seconds = min(max(configured_timeout, 1.0), 60.0)
        self._fetch_json_override = fetch_json

    @property
    def configured(self) -> bool:
        normalized = self.api_token.casefold()
        return bool(self._fetch_json_override or (self.api_token and normalized not in _PLACEHOLDER_TOKENS))

    def configuration_status(self) -> dict[str, Any]:
        return {
            "provider": "EODHD",
            "configured": self.configured,
            "apiVersion": "v1.1",
            "defaultExchange": self.default_exchange,
            "maxSymbolsPerSync": MAX_SYNC_SYMBOLS,
            "credentialLocation": "backend environment only",
            "coverage": [
                "financial statements",
                "TTM highlights",
                "valuation ratios",
                "selected derived ratios",
            ],
            "limitations": [
                "Indian promoter/FII/DII shareholding is not inferred from generic institutional ownership.",
                "NPA, CASA and other India-specific bank disclosures remain unavailable when EODHD omits them.",
                "Missing provider values remain null and do not match screener rules.",
            ],
            "message": (
                "EODHD token is available to the backend."
                if self.configured
                else "Add EODHD_API_TOKEN to the backend .env file and restart the API."
            ),
        }

    @staticmethod
    def ticker_for(symbol: str, exchange: str) -> tuple[str, str]:
        normalized_symbol = symbol.strip().upper()
        normalized_exchange = exchange.strip().upper()
        if not _SYMBOL_PATTERN.fullmatch(normalized_symbol):
            raise EodhdProviderError(f"Unsupported symbol format: {symbol!r}.")
        if not _EXCHANGE_PATTERN.fullmatch(normalized_exchange):
            raise EodhdProviderError(f"Unsupported exchange format: {exchange!r}.")
        return normalized_symbol, f"{normalized_symbol}.{normalized_exchange}"

    def _fetch_json(self, ticker: str) -> Mapping[str, Any]:
        if self._fetch_json_override is not None:
            return self._fetch_json_override(ticker)
        if not self.configured:
            raise EodhdProviderError("EODHD_API_TOKEN is not configured in the backend environment.")

        url = f"{EODHD_FUNDAMENTALS_URL}/{quote(ticker, safe='._-&')}"
        for attempt in range(2):
            try:
                with httpx.Client(timeout=self.timeout_seconds, follow_redirects=False) as client:
                    response = client.get(
                        url,
                        params={"api_token": self.api_token, "fmt": "json"},
                        headers={"Accept": "application/json", "User-Agent": "allinonetrading/0.1"},
                    )
            except httpx.TimeoutException as error:
                if attempt == 0:
                    time.sleep(0.25)
                    continue
                raise EodhdProviderError("EODHD fundamentals request timed out.") from error
            except httpx.HTTPError as error:
                raise EodhdProviderError("EODHD fundamentals request could not be completed.") from error

            if response.status_code == 429:
                if attempt == 0:
                    time.sleep(0.5)
                    continue
                raise EodhdProviderError("EODHD rate limit was reached; retry later.")
            if response.status_code in {401, 403}:
                raise EodhdProviderError("EODHD rejected the API token or the plan lacks fundamentals access.")
            if response.status_code == 404:
                raise EodhdProviderError(f"EODHD has no fundamentals ticker named {ticker}.")
            if response.status_code >= 500:
                if attempt == 0:
                    time.sleep(0.25)
                    continue
                raise EodhdProviderError("EODHD fundamentals service is temporarily unavailable.")
            if response.status_code >= 400:
                raise EodhdProviderError(f"EODHD fundamentals request failed with HTTP {response.status_code}.")
            try:
                result = response.json()
            except ValueError as error:
                raise EodhdProviderError("EODHD returned non-JSON fundamentals data.") from error
            if not isinstance(result, Mapping):
                raise EodhdProviderError("EODHD returned an invalid fundamentals document.")
            return result
        raise EodhdProviderError("EODHD fundamentals request failed.")

    def sync(
        self,
        symbols: Iterable[str],
        *,
        exchange: str | None,
        store: FundamentalStore,
    ) -> dict[str, Any]:
        if not self.configured:
            raise EodhdProviderError("EODHD_API_TOKEN is not configured in the backend environment.")
        selected_exchange = (exchange or self.default_exchange).strip().upper()
        unique_symbols = list(dict.fromkeys(str(symbol).strip().upper() for symbol in symbols if str(symbol).strip()))
        if not unique_symbols:
            raise EodhdProviderError("At least one symbol is required for an EODHD sync.")
        if len(unique_symbols) > MAX_SYNC_SYMBOLS:
            raise EodhdProviderError(f"An EODHD sync is limited to {MAX_SYNC_SYMBOLS} symbols.")

        rows: list[dict[str, Any]] = []
        results: list[dict[str, Any]] = []
        for requested_symbol in unique_symbols:
            try:
                symbol, ticker = self.ticker_for(requested_symbol, selected_exchange)
                payload = self._fetch_json(ticker)
                snapshot = map_eodhd_fundamentals(payload, symbol=symbol, ticker=ticker)
                if not snapshot.values:
                    raise EodhdProviderError(
                        "EODHD returned no fields that can be mapped safely into the current screener catalog."
                    )
                rows.append(snapshot.import_row())
                results.append(
                    {
                        "symbol": symbol,
                        "ticker": ticker,
                        "status": "mapped",
                        "asOf": snapshot.as_of,
                        "currency": snapshot.currency,
                        "fieldsMapped": len(snapshot.values),
                        "currencyAmountsSkipped": snapshot.skipped_currency_amounts,
                    }
                )
            except EodhdProviderError as error:
                results.append({"symbol": requested_symbol, "status": "failed", "message": str(error)})

        imported = {
            "symbolsImported": 0,
            "valuesSubmitted": 0,
            "valuesImported": 0,
            "staleValuesIgnored": 0,
            "nullValuesIgnored": 0,
        }
        if rows:
            imported = store.upsert(rows)
        return {
            "provider": "EODHD",
            "exchange": selected_exchange,
            "symbolsRequested": len(unique_symbols),
            "symbolsMapped": len(rows),
            "symbolsFailed": len(unique_symbols) - len(rows),
            **imported,
            "results": results,
            "storeStatus": store.status(),
            "warning": "Only documented equivalent fields are imported. Unsupported Indian shareholding and bank fields remain null.",
        }
