# Fundamental-data providers and import

The screener exposes 367 provider-backed financial, valuation, ownership,
cash-flow, bank and ratio fields. It never derives these values from price data
and never replaces missing values with zero.

## Data boundary

- Angel One SmartAPI remains the read-only broker adapter for instruments,
  quotes, candles, depth and account data.
- EODHD is the first automated fundamentals provider. A verified exchange
  filing pipeline or user-owned export can supplement fields EODHD does not
  publish.
- The API validates every imported key against the screener catalog and stores
  the latest value per symbol and field in `data/local/fundamentals.sqlite3`.
- The database is ignored by Git. Do not commit licensed datasets or account
  data unless their terms explicitly allow it.

## Configure EODHD locally

EODHD uses its Fundamentals API v1.1. The token must exist only in the FastAPI
backend environment; it must never be added to React, Expo, an APK or an IPA.

1. Copy `.env.example` to `.env` if `.env` does not already exist.
2. Open `.env` and replace only the placeholder below with the token shown in
   your EODHD dashboard:

```dotenv
EODHD_API_TOKEN=paste_your_real_token_here
EODHD_DEFAULT_EXCHANGE=NSE
EODHD_TIMEOUT_SECONDS=20
```

Do not put the real value in `.env.example`. Restart FastAPI after editing
`.env`, because provider configuration is loaded when the backend starts.

Check configuration without exposing the token:

```bash
curl http://127.0.0.1:8000/api/v1/fundamentals/providers/eodhd/status
```

Sync one or more Indian symbols:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/fundamentals/providers/eodhd/sync \
  -H 'Content-Type: application/json' \
  -d '{"symbols":["RELIANCE","TCS","HDFCBANK"],"exchange":"NSE"}'
```

The website and Android/iOS screener use the same endpoint through the
**Sync fundamentals** control. In a GitHub Codespace or other Bash terminal,
the complete connection check is:

```bash
bash scripts/test-eodhd.sh RELIANCE NSE
```

Each ticker is requested as `SYMBOL.EXCHANGE`, such as `RELIANCE.NSE`. The
sync request is capped at 25 symbols so an accidental click cannot consume a
large number of provider calls. See the
[official EODHD Fundamentals API documentation](https://eodhd.com/financial-apis/stock-etfs-fundamental-data-feeds)
for plan coverage and API limits.

## EODHD normalization rules

- Only documented, semantically equivalent values enter the screener.
- Raw INR statement totals are divided by `10,000,000` and stored in INR
  crore, matching the India-first screener convention.
- Per-share values remain INR per share.
- EODHD decimal margins and returns are converted to percentage points. For
  example, `0.20` becomes `20`, not `0.20`.
- TTM totals are calculated only when all four latest quarterly values exist.
- Turnover and solvency ratios are calculated from complete statement values;
  division by zero or missing inputs produces no value.
- Generic `PercentInstitutions` is not relabelled as Indian FII/DII ownership.
  Promoter/public/FII/DII fields remain unavailable until a verified Indian
  shareholding source is added.
- NPA, CASA, capital adequacy and similar bank-only disclosures also remain
  unavailable when EODHD does not return an equivalent value.
- A failed ticker does not block successful tickers in the same sync, and API
  errors never include the token.

## Discover field names

Open `GET /api/v1/screener/catalog`. Imported `values` keys may use either the
stable field ID, such as `fund_ttm_pe`, or the exact display label, such as
`TTM PE`.

## Import a verified snapshot manually

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
