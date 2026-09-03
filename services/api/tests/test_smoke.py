from fastapi.testclient import TestClient

from app import main as main_module
from app.fundamental_store import FundamentalStore
from app.main import SAMPLE_QUOTES, app
from app.screener import SCREENER_FIELDS, resolve_value


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_demo_screener() -> None:
    response = client.post(
        "/api/v1/screener/scan",
        json={
            "universe": "nifty50",
            "timeframe": "1d",
            "conditions": [
                {"id": "rsi", "field": "rsi", "operator": ">", "value": 50}
            ],
        },
    )
    assert response.status_code == 200
    assert response.json()["mode"] == "demo"
    assert response.json()["results"]


def test_screener_catalog_contains_chartink_field_groups() -> None:
    response = client.get("/api/v1/screener/catalog")
    assert response.status_code == 200
    payload = response.json()
    categories = {category["id"]: category for category in payload["categories"]}
    assert {
        "stock_attributes",
        "trade_book",
        "order_book",
        "group_functions",
        "math_functions",
        "pivots",
        "indicators",
        "financial_results",
        "shareholding",
        "cash_flow",
        "bank_fundamentals",
        "financial_ratios",
    }.issubset(categories)
    item_ids = {
        item["id"]
        for category in payload["categories"]
        for item in category["items"]
    }
    assert {
        "ha_close",
        "buyer_seller_trades_ratio",
        "cancelled_orders_ratio",
        "group_avg",
        "countstreak",
        "pivot_point",
        "hma",
        "bollinger_upper",
        "fund_ttm_operating_profit_margin",
        "fund_foreign_institutional_investors_percentage",
        "fund_net_cash_from_operating_activities",
        "fund_capital_adequacy_ratio",
        "fund_return_on_capital_employed_percentage",
    }.issubset(item_ids)
    assert len(item_ids) >= 450
    assert payload["operatorLabels"][">"] == "Greater than"
    assert payload["operatorLabels"]["crosses_above"] == "Crossed above"
    fields = {
        item["id"]: item
        for category in payload["categories"]
        for item in category["items"]
    }
    assert fields["fund_market_cap"]["unit"] == "inr_crore"
    assert fields["fund_ttm_eps"]["unit"] == "inr_per_share"
    assert fields["fund_return_on_assets"]["unit"] == "percentage_or_ratio"
    assert fields["fund_interest_cover"]["unit"] == "ratio"


def test_screener_math_function_and_field_comparison() -> None:
    response = client.post(
        "/api/v1/screener/scan",
        json={
            "universe": "nifty50",
            "timeframe": "1d",
            "logic": "all",
            "conditions": [
                {
                    "id": "absolute-change",
                    "field": "abs",
                    "operator": ">",
                    "value": 1,
                    "parameters": {"source": "change_pct"},
                },
                {
                    "id": "valid-range",
                    "field": "high",
                    "operator": ">",
                    "value": 0,
                    "compare_field": "low",
                },
            ],
        },
    )
    assert response.status_code == 200
    symbols = {row["symbol"] for row in response.json()["results"]}
    assert symbols == {"RELIANCE", "ICICIBANK", "SUNPHARMA"}


def test_screener_any_logic_and_nested_group() -> None:
    response = client.post(
        "/api/v1/screener/scan",
        json={
            "universe": "nifty50",
            "timeframe": "1d",
            "logic": "all",
            "conditions": [],
            "groups": [
                {
                    "id": "technology-or-pharma",
                    "logic": "any",
                    "conditions": [
                        {"id": "it", "field": "sector", "operator": "=", "value": "IT"},
                        {"id": "pharma", "field": "sector", "operator": "=", "value": "Pharma"},
                    ],
                }
            ],
        },
    )
    assert response.status_code == 200
    symbols = {row["symbol"] for row in response.json()["results"]}
    assert symbols == {"TCS", "INFY", "SUNPHARMA"}


def test_depth_fields_are_disclosed_as_demo_only() -> None:
    response = client.post(
        "/api/v1/screener/scan",
        json={
            "conditions": [
                {
                    "id": "depth-ratio",
                    "field": "buy_sell_order_quantity_ratio",
                    "operator": ">",
                    "value": 1,
                }
            ]
        },
    )
    assert response.status_code == 200
    assert response.json()["fieldWarnings"]
    assert "depth" in response.json()["fieldWarnings"][0].lower()


def test_every_catalog_calculation_has_a_demo_value() -> None:
    quote = SAMPLE_QUOTES[0]
    for definition in SCREENER_FIELDS:
        if definition["kind"] in {"group", "measure"}:
            continue
        if definition["availability"] in {
            "fundamentals_required",
            "shareholding_required",
            "cashflow_required",
        }:
            assert resolve_value(quote, definition["id"], {}, SAMPLE_QUOTES) is None
            continue
        parameters = {
            parameter["name"]: parameter["default"]
            for parameter in definition["parameters"]
        }
        assert resolve_value(
            quote,
            definition["id"],
            parameters,
            SAMPLE_QUOTES,
        ) is not None, definition["id"]

    fast_ema = resolve_value(quote, "ema", {"period": 5}, SAMPLE_QUOTES)
    slow_ema = resolve_value(quote, "ema", {"period": 55}, SAMPLE_QUOTES)
    assert fast_ema != slow_ema


def test_imported_fundamental_values_drive_scan_without_synthesis(tmp_path, monkeypatch) -> None:
    store = FundamentalStore(tmp_path / "fundamentals.sqlite3")
    monkeypatch.setattr(main_module, "fundamental_store", store)

    imported = client.post(
        "/api/v1/fundamentals/import",
        json={
            "rows": [
                {
                    "symbol": "RELIANCE",
                    "as_of": "2026-08-31",
                    "source": "verified-test-fixture",
                    "values": {
                        "TTM PE": 18.5,
                        "fund_market_cap": 1990000,
                        "Foreign institutional investors percentage": 22.4,
                    },
                }
            ]
        },
    )
    assert imported.status_code == 200
    assert imported.json()["valuesImported"] == 3

    response = client.post(
        "/api/v1/screener/scan",
        json={
            "conditions": [
                {
                    "id": "pe-cap",
                    "field": "fund_ttm_pe",
                    "operator": "<",
                    "value": 20,
                }
            ]
        },
    )
    assert response.status_code == 200
    assert [row["symbol"] for row in response.json()["results"]] == ["RELIANCE"]
    assert response.json()["results"][0]["metrics"]["fund_ttm_pe"] == 18.5
    assert "1/8" in response.json()["fieldWarnings"][0]

    snapshot = client.get("/api/v1/fundamentals/RELIANCE")
    assert snapshot.status_code == 200
    assert snapshot.json()["values"]["fund_market_cap"] == 1990000


def test_fundamental_import_rejects_unknown_fields(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(main_module, "fundamental_store", FundamentalStore(tmp_path / "fundamentals.sqlite3"))
    response = client.post(
        "/api/v1/fundamentals/import",
        json={
            "rows": [
                {
                    "symbol": "RELIANCE",
                    "as_of": "2026-08-31",
                    "source": "test",
                    "values": {"Made up financial metric": 123},
                }
            ]
        },
    )
    assert response.status_code == 422
    assert "Unknown fundamental fields" in response.json()["detail"]


def test_missing_fundamental_function_source_is_safe_and_disclosed(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(main_module, "fundamental_store", FundamentalStore(tmp_path / "fundamentals.sqlite3"))
    response = client.post(
        "/api/v1/screener/scan",
        json={
            "conditions": [
                {
                    "id": "minimum-pe",
                    "field": "min",
                    "operator": ">",
                    "value": 0,
                    "parameters": {"period": 4, "source": "fund_ttm_pe"},
                }
            ]
        },
    )
    assert response.status_code == 200
    assert response.json()["results"] == []
    assert "financial-results" in response.json()["fieldWarnings"][0]


def test_older_import_does_not_replace_newer_snapshot(tmp_path) -> None:
    store = FundamentalStore(tmp_path / "fundamentals.sqlite3")
    newer = {
        "symbol": "RELIANCE",
        "as_of": "2026-08-31",
        "source": "verified",
        "values": {"TTM PE": 18.5},
    }
    older = {**newer, "as_of": "2026-03-31", "values": {"TTM PE": 99}}
    assert store.upsert([newer])["valuesImported"] == 1
    result = store.upsert([older])
    assert result["valuesImported"] == 0
    assert result["staleValuesIgnored"] == 1
    assert store.snapshot_for_symbol("RELIANCE")["values"]["fund_ttm_pe"] == 18.5
