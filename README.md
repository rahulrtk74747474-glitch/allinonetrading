# All In One Trading

A private, single-user research terminal for Indian markets and crypto research.

The first milestone is deliberately paper-only. It provides a cross-platform foundation for:

- Chartink-style technical and fundamental screening
- RRG with smooth 20-bar trails
- Indian universes: NIFTY 50, BANKNIFTY, MIDCAP 150 and custom lists
- Backtesting and strategy metrics
- Margin, charges and order-preview calculations
- Options chain and payoff modules
- Strategy optimization
- Crypto and arbitrage research
- A future advisory research layer using TradingAgents-style agents

## Safety

SmartAPI credentials never belong in source control, a browser bundle, an APK or an IPA.

1. Copy .env.example to .env.
2. Enter rotated credentials locally.
3. Keep PAPER_TRADING=true and LIVE_TRADING=false.
4. Never commit .env.

If a credential was ever committed to a repository, treat it as compromised even
if the file is later removed. Revoke it at the broker and create a fresh one.

The repository currently contains demo data only. Demo signals are not trading advice and must not be used as live orders.

## Architecture

- services/api: FastAPI backend. It will own broker sessions, market data, risk checks and order routing.
- apps/web: React/Vite trading terminal for desktop and mobile browsers.
- apps/mobile: Expo/React Native client for Android and iOS.
- packages/contracts: shared TypeScript API and strategy contracts.
- data: local market-data storage will be added later; credentials and private data stay outside Git.

The browser and mobile clients will call the same backend. Broker credentials and the TOTP secret will never be sent to either client.

## Run the current demo

Install Node.js, pnpm and Python 3.11+.

From the repository root:

    pnpm install
    pnpm --filter @allinone/web dev

In another terminal:

    python -m venv .venv
    .venv\Scripts\activate
    pip install -e services/api
    pip install -r services/api/requirements-broker.txt
    uvicorn app.main:app --reload --app-dir services/api

The website runs on the Vite URL shown by the command, normally http://localhost:5173.
The API runs on http://127.0.0.1:8000.

After .env is configured, the local launcher starts both services:

    # Windows PowerShell
    .\scripts\start-local.ps1

    # macOS/Linux
    bash scripts/start-local.sh

The launcher creates the virtual environment when needed and installs the
read-only broker adapter. It never prints or uploads the values in .env.

For macOS/Linux, activate the environment with:

    source .venv/bin/activate

## Mobile preview

Install the Expo tooling, then run:

    pnpm --filter @allinone/mobile start

Set EXPO_PUBLIC_API_URL to the reachable API URL when mobile is connected to the backend. A phone cannot reach 127.0.0.1 on the development computer; use the computer's LAN address or a private VPN.

For example, copy apps/mobile/.env.example to apps/mobile/.env and replace
127.0.0.1 with the computer's LAN address when using a physical phone.

## Repository integration

The external repository decisions and licence boundaries are documented in docs/REPOSITORY_INTEGRATION.md. The first shared research workflow is available at POST /api/v1/research/analyze; it is advisory-only and paper-only.

## First vertical slice

Load normalized market data -> run a saved scan -> inspect a chart -> view RRG -> backtest the same rule -> preview a paper order with margin and charges.

## Roadmap

1. Connect Angel One SmartAPI for read-only instruments, candles and quotes.
2. Replace demo data with a normalized India market-data service.
3. Add the existing RRG calculations and 20-bar trails.
4. Add event-driven backtesting with no-lookahead checks.
5. Add options, optimizer and risk reports.
6. Add crypto data and paper arbitrage.
7. Add live broker execution only after explicit safety and compliance review.
