# External repository integration map

Reviewed on 2026-09-01 for the private, single-user paper-trading build.

This project uses external repositories as reference material or behind explicit adapter boundaries. It does not copy whole applications into the core product. Every signal, backtest, option calculation and order preview must carry a source, timestamp, mode, and data-quality warning.

## Capability matrix

| Repository | Capability we will use | Integration boundary | Licence |
| --- | --- | --- | --- |
| [NautilusTrader](https://github.com/nautechsystems/nautilus_trader) | Deterministic event-driven backtests and a future live/research execution seam | Optional Python/Rust engine adapter behind the BacktestEngine interface; no frontend dependency | LGPL-3.0 |
| [TradingAgents](https://github.com/TauricResearch/TradingAgents) | Specialist research roles, evidence snapshots, decision logs and checkpoints | Research Copilot produces typed advisory reports; it has no order authority | Apache-2.0 |
| [Ruflo](https://github.com/ruvnet/ruflo) | Job orchestration, role-based agents, memory and guardrails | Reimplement the useful queue/audit ideas first; pin and test any future dependency | MIT |
| [OpenAlice](https://github.com/TraderAlice/OpenAlice) | Local-first workspaces, tracked entities, inbox and approval-gated Trading-as-Git workflow | Strategy registry, research queue and paper-order approval ledger | AGPL-3.0 |
| [httpSMS](https://github.com/NdoleStudio/httpsms) | HTTP notification transport through an Android phone | Optional notification adapter only; never for TOTP, OTP, trade approval or secrets | AGPL-3.0 |
| [Pocket TTS](https://github.com/kyutai-labs/pocket-tts) | Local CPU text-to-speech for briefings and alerts | Optional local HTTP sidecar; keep it out of the mobile bundle and trading critical path | MIT |

Licences are recorded so a later public/commercial launch can receive a proper legal review. In particular, AGPL projects are not copied into the core repository in this phase.

## Target architecture

1. Data adapters normalize Angel One, India market data, crypto venues and later options feeds into one snapshot format.
2. Pure indicator functions calculate RSI, moving averages, ATR, breadth, relative strength and volatility.
3. The screener and strategy registry consume the same conditions, so a saved Chartink-style rule can produce a scan, signal and backtest.
4. The Research Copilot reads a frozen snapshot and returns technical, fundamental, news and risk findings with evidence IDs.
5. Backtesting runs event-by-event with no-lookahead checks, realistic charges, slippage, liquidity and corporate actions.
6. Paper trading uses the same order-preview/risk path as the future live adapter, but the live endpoint remains disabled.
7. Web, Android and iOS call the same API and never receive broker credentials.

## What is implemented in this slice

- POST /api/v1/research/analyze returns a typed, advisory-only research packet.
- The packet includes an agent trace, confidence, evidence status, risks, next actions and an explicit approval_required flag.
- The web client has a Research Copilot screen.
- The mobile client exposes the same research workflow through the shared API base URL.
- Shared TypeScript contracts mirror the API response.

The current packet is deterministic demo output. It must not be interpreted as investment advice or a live signal.

## Delivery order

### Phase 1: private paper workspace

- verified read-only SmartAPI candles/quotes
- instrument master and corporate-action-aware local storage
- Chartink-style condition groups and saved scans
- RRG from normalized benchmark/sector data
- event-driven backtest with a reproducible data snapshot
- margin, charges and slippage preview
- options chain and payoff analytics
- optimizer with train/test and walk-forward separation
- paper ledger, manual approval and audit history

### Phase 2: research quality

- verified news/RSS and fundamentals adapters
- specialist research roles with retry/timeouts and persistent decision logs
- NautilusTrader-backed backtest adapter for multi-venue studies
- crypto venue adapters and paper arbitrage after fees, funding, transfer cost and latency checks
- local voice briefing through Pocket TTS
- push notifications; httpSMS remains optional and isolated

### Phase 3: scale only after validation

- authentication, encrypted secret storage and tenant isolation
- background job queue and Postgres/Timescale or equivalent production storage
- observability, rate limits, replayable audit logs and disaster recovery
- broker/exchange compliance review and explicit live-order release gate
- Play Store, App Store and web production release

## Non-negotiable safety boundaries

- No credentials, TOTP secrets, access tokens or session tokens in Git, web JavaScript, APKs or IPAs.
- AI/research agents may explain evidence and create a proposed paper order, but cannot place or approve an order.
- Backtests must show data range, fees, slippage, survivorship/corporate-action assumptions and out-of-sample results.
- Arbitrage must be executable-after-costs, not merely a displayed price difference.
- Every live-capable feature stays disabled until separately reviewed and tested.
