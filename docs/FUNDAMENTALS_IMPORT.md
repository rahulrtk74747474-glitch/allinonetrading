# Fundamental-data import

The screener exposes 367 provider-backed financial, valuation, ownership,
cash-flow, bank and ratio fields. It never derives these values from price data
and never replaces missing values with zero.

## Data boundary

- Angel One SmartAPI remains the read-only broker adapter for instruments,
  quotes, candles, depth and account data.
- A licensed financial-data provider, exchange filing pipeline or user-owned
  export supplies fundamentals and shareholding values.
- The API validates every imported key against the screener catalog and stores
  the latest value per symbol and field in `data/local/fundamentals.sqlite3`.
- The database is ignored by Git. Do not commit licensed datasets or account
  data unless their terms explicitly allow it.

## Discover field names

Open `GET /api/v1/screener/catalog`. Imported `values` keys may use either the
stable field ID, such as `fund_ttm_pe`, or the exact display label, such as
`TTM PE`.

## Import a verified snapshot

From a terminal with the backend running:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/fundamentals/import \
  -H 'Content-Type: application/json' \
  -d '{
    "rows": [
      {
        "symbol": "RELIANCE",
        "as_of": "2026-08-31",
        "source": "replace-with-your-verified-provider",
        "values": {
          "TTM PE": 0,
          "fund_market_cap": 0,
          "Foreign institutional investors percentage": 0
        }
      }
    ]
  }'
```

The zeros above are schema placeholders, not market data. Replace them and the
date/source with verified values before importing.

Useful read endpoints:

- `GET /api/v1/fundamentals/status`
- `GET /api/v1/fundamentals/RELIANCE`
- `GET /api/v1/screener/catalog`

## Evaluation behavior

- A row matches a financial rule only when the requested value exists.
- Unknown fields, booleans, non-numeric values and non-finite values are
  rejected atomically.
- An import updates only the supplied fields; it does not delete other values.
- The current store is latest-snapshot only. `Crossed above` and `Crossed
  below` for fundamental fields require dated history and therefore return no
  match with an explicit warning in this version.

## Before public deployment

Protect the import and read endpoints with authentication and authorization,
encrypt production storage, enforce provider licence/redistribution terms, add
filing-period and restatement metadata, and retain an auditable source record.
