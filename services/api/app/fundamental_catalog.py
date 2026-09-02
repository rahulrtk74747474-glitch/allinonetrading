from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any


# These labels intentionally stay close to the terminology used by Indian
# financial-data vendors.  Headings from the source picker (for example,
# "Legacy Fundamentals", "Shareholding pattern" and "Cash flow") are modeled
# as categories instead of fake numeric fields.
FINANCIAL_RESULTS = """
TTM Operating profit margin
TTM Gross profit
TTM Gross profit margin
TTM Net profit
TTM Net profit Variance
TTM EPS
TTM PE
TTM CPS
TTM Depreciation
Total Loans
Advance Given By Bank
Net non performing assets
TTM Sales
TTM Operating Profit
Net Sales[quarter]
Price to Book Value
Networth
BSE Value in lakhs
NSE Value in lakhs
Market Cap
Operating profit margin[yr]
Operating profit margin[qr]
Gross profit margin
Gross Block
Sales Turnover[yearly]
Net Profit[yearly]
Net Profit Variance[yr]
Net Profit[quarter]
Net Profit Variance[qr]
Earning Per Share[EPS]
Prev Year EPS
Cash Per Share[yr]
Cash Per Share[qr]
Cash per share[mt]
Equity
Reserves
Dividend
Yearly PE Ratio
Yearly PC Ratio
Face value
Eps after extraordinary items basic
Eps after extraordinary items diluted
Book value
Dividend per share rupees
Prior year dividend paid
Equity dividend
Preference dividend
"""


SHAREHOLDING = """
Adr shareholders
Adr number
Adr percentage
Gdr shareholders
Gdr number
Gdr percentage
Other custodians shareholders
Other custodians number
Other custodians percentage
Foreignpromoter institutional number
Foreignpromoter institutional percentage
Promoter others shareholders
Promoter others number
Promoter others percentage
Foreign institution other shareholders
Foreign institution other number
Foreign institution other percentage
Foreign non institution other shareholders
Foreign non institution other number
Societies percentage
Trust and foundation shareholders
Trust and foundation number
Trust and foundation percentage
Nora shareholders
Nora number
Nora percentage
Non promoter non institution shareholders
Non promoter non institution number
Non promoter non institution percentage
Custodians against depository receipts shareholders
Custodians against depository receipts number
Custodians against depository receipts percentage
Total shareholders
Total number
Total percentage
Foreignpromoter institutional shareholders
Market maker number
Market maker percentage
Nsdl transit shareholders
Nsdl transit number
Nsdl transit percentage
Shares in transit shareholders
Shares in transit number
Shares in transit percentage
Societies shareholders
Societies number
Indian public shareholders
Indian public number
Indian public percentage
Individuals share capital up to rs 1 lakh shareholders
Individuals share capital up to rs 1 lakh number
Individuals share capital up to rs 1 lakh percentage
Individuals share capital in excess of rs 1 lakh shareholders
Individuals share capital in excess of rs 1 lakh number
Individuals share capital in excess of rs 1 lakh percentage
Market maker shareholders
Directors and relatives indian promoter and group number
Directors and relatives indian promoter and group percentage
Financial institutions indian promoter and group shareholders
Financial institutions indian promoter and group number
Financial institutions indian promoter and group percentage
Individuals or family indian promoter and group shareholders
Individuals or family indian promoter and group number
Individuals or family indian promoter and group percentage
Partnership firms indian promoter and group shareholders
Partnership firms indian promoter and group number
Others promoter or group percentage
Indian promoter and group shareholders
Indian promoter and group number
Indian promoter and group percentage
Govt central or state shareholders
Govt central or state number
Govt central or state percentage
Clearing members shareholders
Clearing members number
Clearing members percentage
Corporate bodies shareholders
Corporate bodies number
Corporate bodies percentage
Foreign direct investments institutions shareholders
Foreign direct investments institutions number
Foreign direct investments institutions percentage
Foreign bank shareholders
Foreign bank number
Foreign bank percentage
Foreign bodies corporateorocbsorfbc shareholders
Foreign bodies corporateorocbsorfbc number
Foreign bodies corporateorocbsorfbc percentage
Foreign collaborators shareholders
Foreign collaborators number
Foreign collaborators percentage
Foreign institutional investors shareholders
Foreign institutional investors number
Foreign institutional investors percentage
Foreign venture capital investors shareholders
Foreign venture capital investors number
Foreign venture capital investors percentage
Others institutions shareholders
Others institutions number
Others institutions percentage
Financial institutions or banks shareholders
Financial institutions or banks number
Financial institutions or banks percentage
Insurance companies shareholders
Insurance companies number
Insurance companies percentage
Mutual funds or uti shareholders
Mutual funds or uti number
Mutual funds or uti percentage
Individuals non resident or foreign shareholders
Individuals non resident or foreign number
Individuals non resident or foreign percentage
Nsdl intransit shareholders
Nsdl intransit number
Nsdl intransit percentage
Trusts institutes shareholders
Trusts institutes number
Trusts institutes percentage
Venture capital funds shareholders
Venture capital funds number
Venture capital funds percentage
Non promoter institution shareholders
Non promoter institution number
Non promoter institution percentage
Bodies corporate shareholders
Bodies corporate number
Bodies corporate percentage
Clearing members non promoter non institution shareholders
Clearing members non promoter non institution number
Clearing members non promoter non institution percentage
Directors and their relatives shareholders
Directors and their relatives number
Directors and their relatives percentage
Employees shareholders
Employees number
Employees percentage
Escrow account shareholders
Escrow account number
Escrow account percentage
Foreign corporate bodies shareholders
Foreign corporate bodies number
Foreign corporate bodies percentage
Foreign direct investments shareholders
Foreign direct investments number
Foreign direct investments percentage
Nrisorforeign individualsorforeign nationals shareholders
Nrisorforeign individualsorforeign nationals number
Nrisorforeign individualsorforeign nationals percentage
Hindu undivided families shareholders
Hindu undivided families number
Hindu undivided families percentage
Others non promoter non institution shareholders
Others non promoter non institution number
Others non promoter non institution percentage
Foreign promoter and group bodies corporate shareholders
Foreign promoter and group bodies corporate number
Foreign promoter and group bodies corporate percentage
Foreign promoter and group individuals shareholders
Foreign promoter and group individuals number
Foreign promoter and group individuals percentage
Total foreign promoter and group shareholders
Total foreign promoter and group number
Total foreign promoter and group percentage
Bodies corporate indian promoter and group shareholders
Bodies corporate indian promoter and group number
Bodies corporate indian promoter and group percentage
Govt central or state indian promoter and group shareholders
Govt central or state indian promoter and group number
Govt central or state indian promoter and group percentage
Directors and relatives indian promoter and group shareholders
Directors and relatives indian promoter and group number
Directors and relatives indian promoter and group percentage
Partnership firms indian promoter and group percentage
Persons acting in concert shareholders
Persons acting in concert number
Persons acting in concert percentage
Trusts promoter or group shareholders
Trusts promoter or group number
Trusts promoter or group percentage
Others promoter or group shareholders
Others promoter or group number
Public shareholding
Public shareholding percentage
Percentage of shares held by goi
Encumbered number of shares
Encumbered percentage in total promoters holding
Encumbered percentage in total equity
Non encumbered number of shares
Non encumbered percentage in total promoters holding
Non encumbered percentage in total equity
"""


CASH_FLOW = """
Total adjustments pbt and extraordinary items
Operating profit before working capital changes
Trade and other receivables
Trade payables
Loans and advances
Net stock on hire
Leased assets net of sale
Trade bills purchased
Change in borrowing
Change in deposits
Others adjustments for working capital changes operating activities
Total adjustments op before working capital changes
Cash generated from or used in operations
Interest paidnet
Direct taxes paid
Advance tax paid
Others cash generated from or used in operations
Total adjustments cash generated from or used in operations
Cash flow before extraordinary items
Excess depreciation w or b
Premium on lease of land
Payment towards vrs
Prior years taxation
Gain on forex exch transactions
Others extraordinary items operating activities
Total extraordinary items
Net cash from operating activities
Purchased of fixed assets
Sale of fixed assets
Purchase of investments
Sale of investments
Capital wip
Capital subsidy received
Investment income
Interest received
Dividend received cash flow from investing activities
Investment in subsidiaries
Loans to subsidiaries
Investment in group companies
Issue of shares on acquisition of companies
Cancellation of investment in companies acquired
Acquisition of companies
Inter corporate deposits
Others cash flow from investing activities
Net cash used in investing activities
Proceeds from issue of shares including share premium
Proceed from issue of debentures
Proceed from other long term borrowings
Proceed from bank borrowings
Proceed from short tem borrowings
Proceed from deposits
Share application money
Share application money refund
Cash or capital investment subsidy
Loans from a corporate body
On redemption of debenture
Of the long tem borrowings
Of the short term borrowings
Of financial liabilities
Dividend paid
Shelter assistance reserve
Others cash flow from financing activities
Net cash used in financing activities
Net increase or decrease in cash and cash equivalent
Cash and cash equivalents at beginning of the year
Cash and cash equivalents at end of the year
Interest paid
Net profit before tax and extraordinary items
Interest net
Dividend received adjustments operating activities
Pl on sales of assets
Pl on sales of invest
Provisions and wo net
Pl in forex
Fin lease and rental charges
Others adjustments pbt and extraordinary items operating activities
"""


BANK_FUNDAMENTALS = """
Capital adequacy ratio
Tier I capital
Tier ii capital
Gross non performing assets
Percentage gross non performing assets
Percentage net non performing assets
Return on assets annualised
Return on assets
Net interest margin percentage
Current deposits
Saving deposits
Term deposits
Total deposits
Total advances
Provision coverage ratio percentage
Casa ratio percentage
Number of branches
Number of atms
Number of employees
Dividend percentage
Percentage net non performing assets to net advance
Interest income percentage average working fund
Non interest income percentage average working fund
Operating profit percentage average working fund
Credit deposit ratio
Investment deposit ratio
Cash deposit ratio
Interest expended to interest earned
Other income to total income
Operating expense to total income
Interest income to total funds
Interest expended to total funds
Net interest income to total funds
Non interest income to total funds
Operating expense to total funds
Profit before provisions to total funds
Net profit to total funds
Loans turnover
Advances to loan funds percentage
Total income to capital employed percentage
Interest expended to capital employed percentage
"""


FINANCIAL_RATIOS = """
Debt equity ratio
Long term debt equity ratio
Current ratio
Fixed assets turnover ratio
Inventory turnover ratio
Debtors turnover ratio
Interest cover
Operating profit margin percentage
Profit before interest and tax margin percentage
Gross profit margin percentage
Cash profit margin percentage
Adjusted net profit margin percentage
Return on capital employed percentage
Return on net worth percentage
Total assets turnover ratios
"""


CATEGORY_META = {
    "financial_results": {
        "label": "Financial results & valuation",
        "availability": "fundamentals_required",
        "description": "Latest imported company financials and valuation metrics.",
        "labels": FINANCIAL_RESULTS,
    },
    "shareholding": {
        "label": "Shareholding pattern",
        "availability": "shareholding_required",
        "description": "Latest imported shareholding-pattern snapshot.",
        "labels": SHAREHOLDING,
    },
    "cash_flow": {
        "label": "Cash-flow statement",
        "availability": "cashflow_required",
        "description": "Latest imported cash-flow statement values.",
        "labels": CASH_FLOW,
    },
    "bank_fundamentals": {
        "label": "Bank fundamentals",
        "availability": "fundamentals_required",
        "description": "Banking-specific operating and balance-sheet metrics.",
        "labels": BANK_FUNDAMENTALS,
    },
    "financial_ratios": {
        "label": "Financial ratios",
        "availability": "fundamentals_required",
        "description": "Latest imported profitability, solvency and turnover ratios.",
        "labels": FINANCIAL_RATIOS,
    },
}


def _labels(block: str) -> Iterable[str]:
    return (line.strip() for line in block.splitlines() if line.strip())


def slugify_label(label: str) -> str:
    normalized = label.casefold().replace("%", " percentage ").replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")


def infer_unit(label: str) -> str:
    lowered = label.casefold()
    if "percentage" in lowered or "margin" in lowered or lowered.endswith(" ratio"):
        return "percentage_or_ratio"
    if "shareholders" in lowered or lowered.startswith("number of"):
        return "count"
    if "number" in lowered or "shares" in lowered:
        return "count_or_shares"
    if "eps" in lowered or "per share" in lowered or lowered == "face value":
        return "inr_per_share"
    if "value in lakhs" in lowered:
        return "inr_lakh"
    return "provider_native"


def fundamental_field_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for category, metadata in CATEGORY_META.items():
        for label in _labels(str(metadata["labels"])):
            field_id = f"fund_{slugify_label(label)}"
            if field_id in seen:
                continue
            seen.add(field_id)
            records.append(
                {
                    "id": field_id,
                    "label": label,
                    "category": category,
                    "kind": "field",
                    "valueType": "number",
                    "description": str(metadata["description"]),
                    "availability": str(metadata["availability"]),
                    "parameters": [],
                    "unit": infer_unit(label),
                    "historyMode": "latest_snapshot",
                    "dataSource": "fundamentals_import",
                }
            )
    return records


FUNDAMENTAL_FIELDS = fundamental_field_records()
FUNDAMENTAL_FIELD_IDS = frozenset(item["id"] for item in FUNDAMENTAL_FIELDS)
FUNDAMENTAL_LABEL_TO_ID = {item["label"].casefold(): item["id"] for item in FUNDAMENTAL_FIELDS}


def normalize_fundamental_field_key(value: str) -> str | None:
    key = value.strip()
    if key in FUNDAMENTAL_FIELD_IDS:
        return key
    return FUNDAMENTAL_LABEL_TO_ID.get(key.casefold())
