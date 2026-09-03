from __future__ import annotations

from copy import deepcopy

from fastapi.testclient import TestClient

from app import main as main_module
from app.fundamental_store import FundamentalStore
from app.main import app
from app.providers.eodhd import EodhdFundamentalsProvider, map_eodhd_fundamentals


client = TestClient(app)


def eodhd_fixture() -> dict:
    quarterly_income = {
        "2026-06-30": {"date": "2026-06-30", "totalRevenue": "260000000000", "grossProfit": "104000000000", "operatingIncome": "52000000000", "netIncome": "26000000000"},
        "2026-03-31": {"date": "2026-03-31", "totalRevenue": "250000000000", "grossProfit": "100000000000", "operatingIncome": "50000000000", "netIncome": "25000000000"},
        "2025-12-31": {"date": "2025-12-31", "totalRevenue": "240000000000", "grossProfit": "96000000000", "operatingIncome": "48000000000", "netIncome": "24000000000"},
        "2025-09-30": {"date": "2025-09-30", "totalRevenue": "230000000000", "grossProfit": "92000000000", "operatingIncome": "46000000000", "netIncome": "23000000000"},
        "2025-06-30": {"date": "2025-06-30", "totalRevenue": "210000000000", "grossProfit": "84000000000", "operatingIncome": "42000000000", "netIncome": "20000000000"},
        "2025-03-31": {"date": "2025-03-31", "totalRevenue": "205000000000", "grossProfit": "82000000000", "operatingIncome": "41000000000", "netIncome": "19000000000"},
        "2024-12-31": {"date": "2024-12-31", "totalRevenue": "200000000000", "grossProfit": "80000000000", "operatingIncome": "40000000000", "netIncome": "18000000000"},
        "2024-09-30": {"date": "2024-09-30", "totalRevenue": "195000000000", "grossProfit": "78000000000", "operatingIncome": "39000000000", "netIncome": "17000000000"},
    }
    quarterly_cashflow = {
        date_key: {"date": date_key, "depreciation": "2500000000"}
        for date_key in list(quarterly_income)[:4]
    }
    return {
        "General": {
            "Code": "RELIANCE",
            "CurrencyCode": "INR",
            "UpdatedAt": "2026-08-31",
            "FullTimeEmployees": 389000,
        },
        "Highlights": {
            "MarketCapitalization": 19_900_000_000_000,
            "PERatio": 18.5,
            "BookValue": 612.4,
            "DividendShare": 10,
            "EarningsShare": 101.2,
            "DilutedEpsTTM": 101.2,
            "MostRecentQuarter": "2026-06-30",
            "OperatingMarginTTM": 0.20,
            "ReturnOnAssetsTTM": 0.087,
            "ReturnOnEquityTTM": 0.125,
            "RevenueTTM": 980_000_000_000,
            "GrossProfitTTM": 392_000_000_000,
        },
        "Valuation": {"TrailingPE": 18.5, "PriceBookMRQ": 3.2},
        "Financials": {
            "Income_Statement": {
                "currency_symbol": "INR",
                "quarterly": quarterly_income,
                "yearly": {
                    "2026-03-31": {
                        "date": "2026-03-31",
                        "filing_date": "2026-05-20",
                        "totalRevenue": "900000000000",
                        "costOfRevenue": "540000000000",
                        "grossProfit": "360000000000",
                        "operatingIncome": "180000000000",
                        "netIncome": "90000000000",
                        "ebit": "170000000000",
                        "interestExpense": "-10000000000",
                        "dilutedEPS": "50",
                    },
                    "2025-03-31": {
                        "date": "2025-03-31",
                        "totalRevenue": "800000000000",
                        "netIncome": "80000000000",
                        "dilutedEPS": "44",
                    },
                },
            },
            "Balance_Sheet": {
                "currency_symbol": "INR",
                "quarterly": {
                    "2026-06-30": {
                        "date": "2026-06-30",
                        "totalStockholderEquity": "520000000000",
                        "capitalStock": "10000000000",
                        "cashAndEquivalents": "110000000000",
                        "commonStockSharesOutstanding": "10000000000",
                    }
                },
                "yearly": {
                    "2026-03-31": {
                        "date": "2026-03-31",
                        "totalAssets": "1000000000000",
                        "totalCurrentAssets": "400000000000",
                        "totalCurrentLiabilities": "200000000000",
                        "totalStockholderEquity": "500000000000",
                        "shortLongTermDebtTotal": "250000000000",
                        "longTermDebt": "150000000000",
                        "propertyPlantAndEquipmentNet": "300000000000",
                        "inventory": "100000000000",
                        "netReceivables": "80000000000",
                        "cashAndEquivalents": "100000000000",
                        "commonStockSharesOutstanding": "10000000000",
                    },
                    "2025-03-31": {
                        "date": "2025-03-31",
                        "totalAssets": "900000000000",
                        "propertyPlantAndEquipmentNet": "250000000000",
                        "inventory": "80000000000",
                        "netReceivables": "70000000000",
                    },
                },
            },
            "Cash_Flow": {
                "currency_symbol": "INR",
                "quarterly": quarterly_cashflow,
                "yearly": {
                    "2026-03-31": {
                        "date": "2026-03-31",
                        "totalCashFromOperatingActivities": "120000000000",
                        "capitalExpenditures": "-40000000000",
                        "totalCashflowsFromInvestingActivities": "-60000000000",
                        "issuanceOfCapitalStock": "5000000000",
                        "dividendsPaid": "-15000000000",
                        "totalCashFromFinancingActivities": "-30000000000",
                        "changeInCash": "30000000000",
                        "beginPeriodCashFlow": "70000000000",
                        "endPeriodCashFlow": "100000000000",
                        "interestPaid": "-10000000000",
                    }
                },
            },
        },
    }


def test_eodhd_mapper_normalizes_inr_units_and_percentages() -> None:
    snapshot = map_eodhd_fundamentals(
        eodhd_fixture(),
        symbol="RELIANCE",
        ticker="RELIANCE.NSE",
    )

    assert snapshot.as_of == "2026-08-31"
    assert snapshot.currency == "INR"
    assert snapshot.skipped_currency_amounts is False
    assert snapshot.values["fund_market_cap"] == 1_990_000
    assert snapshot.values["fund_ttm_sales"] == 98_000
    assert snapshot.values["fund_ttm_operating_profit"] == 19_600
    assert snapshot.values["fund_ttm_net_profit"] == 9_800
    assert snapshot.values["fund_ttm_operating_profit_margin"] == 20
    assert snapshot.values["fund_ttm_gross_profit_margin"] == 40
    assert snapshot.values["fund_return_on_net_worth_percentage"] == 12.5
    assert snapshot.values["fund_net_profit_variance_qr"] == 30
    assert snapshot.values["fund_debt_equity_ratio"] == 0.5
    assert snapshot.values["fund_current_ratio"] == 2
    assert snapshot.values["fund_net_cash_from_operating_activities"] == 12_000
    assert "fund_foreign_institutional_investors_percentage" not in snapshot.values


def test_eodhd_mapper_does_not_mix_non_inr_monetary_values() -> None:
    payload = deepcopy(eodhd_fixture())
    payload["General"]["CurrencyCode"] = "USD"
    payload["Financials"]["Income_Statement"]["currency_symbol"] = "USD"

    snapshot = map_eodhd_fundamentals(payload, symbol="AAPL", ticker="AAPL.US")

    assert snapshot.skipped_currency_amounts is True
    assert snapshot.values["fund_ttm_pe"] == 18.5
    assert snapshot.values["fund_ttm_operating_profit_margin"] == 20
    assert "fund_market_cap" not in snapshot.values
    assert "fund_ttm_sales" not in snapshot.values
    assert "fund_ttm_eps" not in snapshot.values
    assert "fund_book_value" not in snapshot.values


def test_eodhd_sync_imports_without_exposing_token(tmp_path) -> None:
    requested: list[str] = []

    def fetch(ticker: str) -> dict:
        requested.append(ticker)
        return eodhd_fixture()

    provider = EodhdFundamentalsProvider(api_token="super-secret-token", fetch_json=fetch)
    store = FundamentalStore(tmp_path / "fundamentals.sqlite3")
    result = provider.sync(["RELIANCE", "RELIANCE"], exchange="NSE", store=store)

    assert requested == ["RELIANCE.NSE"]
    assert result["symbolsRequested"] == 1
    assert result["symbolsMapped"] == 1
    assert result["valuesImported"] > 20
    snapshot = store.snapshot_for_symbol("RELIANCE")
    assert snapshot is not None
    assert snapshot["values"]["fund_ttm_pe"] == 18.5
    assert "super-secret-token" not in str(result)
    assert "super-secret-token" not in str(snapshot)


def test_eodhd_api_status_and_sync_endpoint(tmp_path, monkeypatch) -> None:
    provider = EodhdFundamentalsProvider(
        api_token="test-token",
        fetch_json=lambda _ticker: eodhd_fixture(),
    )
    monkeypatch.setattr(main_module, "eodhd_provider", provider)
    monkeypatch.setattr(main_module, "fundamental_store", FundamentalStore(tmp_path / "fundamentals.sqlite3"))

    status = client.get("/api/v1/fundamentals/providers/eodhd/status")
    assert status.status_code == 200
    assert status.json()["configured"] is True
    assert "test-token" not in status.text

    synced = client.post(
        "/api/v1/fundamentals/providers/eodhd/sync",
        json={"symbols": ["RELIANCE"], "exchange": "NSE"},
    )
    assert synced.status_code == 200
    assert synced.json()["symbolsMapped"] == 1
    assert synced.json()["valuesImported"] > 20


def test_eodhd_placeholder_is_not_treated_as_a_configured_token() -> None:
    provider = EodhdFundamentalsProvider(api_token="replace_with_eodhd_api_token")
    status = provider.configuration_status()
    assert status["configured"] is False
    assert "replace_with_eodhd_api_token" not in str(status)


def test_eodhd_sync_endpoint_rejects_missing_token_without_leaking_it(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(main_module, "eodhd_provider", EodhdFundamentalsProvider(api_token=""))
    monkeypatch.setattr(main_module, "fundamental_store", FundamentalStore(tmp_path / "fundamentals.sqlite3"))

    response = client.post(
        "/api/v1/fundamentals/providers/eodhd/sync",
        json={"symbols": ["RELIANCE"], "exchange": "NSE"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "EODHD_API_TOKEN is not configured in the backend environment."
