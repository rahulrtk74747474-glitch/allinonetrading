from fastapi.testclient import TestClient

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
    }.issubset(item_ids)


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
