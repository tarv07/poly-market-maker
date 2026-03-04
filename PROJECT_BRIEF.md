# PROJECT_BRIEF — Polymarket CLOB Market-Making Engine (Python)

## TL;DR
Build a modular market-making engine for prediction markets on Polymarket’s Central Limit Order Book (CLOB).
Start from a safe, read-only market-data pipeline, then add a dry-run quoting engine, then controlled order
placement with strict risk limits.

This repo begins as a fork of `Polymarket/poly-market-maker` (baseline keeper that cancels/places around midpoint),
and evolves into a more event-driven, testable, and risk-aware engine.

---

## Motivation / Why this exists
My previous futures quoting work was a foundation + interview story, but not something I trusted with capital.
Prediction markets have slimmer edge and more “flow/gambler” behavior; the goal here is to build a robust,
repeatable market-making system where operational quality and risk controls matter more than tiny pricing edges.

---

## Starting Point (Template Behavior)
The upstream keeper (`poly-market-maker`) is an automated market maker for CLOB markets:
- Places and cancels orders to keep open orders near the midpoint price
- Supports two strategies (“Bands” and “AMM”)
- Runs a strategy lifecycle every `sync_interval` (default ~30s): fetch midpoint → compute desired orders → diff vs open orders → cancel → place
- On SIGTERM, cancels all orders and exits gracefully

We will keep the “diff open orders vs desired orders” concept but improve the architecture:
- Add a true local orderbook model (WS-driven)
- Add a dry-run mode + kill switch
- Add explicit inventory/risk layer
- Improve test coverage and observability
- Reduce polling and prefer WebSockets where possible

---

## Non-goals (for v0)
- No predictive model / “alpha” signal (initially)
- No cross-exchange arbitrage
- No multi-market portfolio optimizer (start single-market, then scale)
- No extreme latency optimization (Python-first); C/C++ only if justified later

---

## Core Requirements (v0/v1)
### Market data
- Subscribe to Polymarket WebSocket market channel(s) for near real-time updates (book + trades)
- Maintain a local L2 book model (snapshot + updates), and compute best bid/ask + midpoint

### Quoting engine
- Generate two-sided quotes around a reference price (midpoint), using:
  - base spread / bands
  - tick-size rounding (market-specific; orders must conform or are rejected)
  - size logic and minimum size constraints (if applicable)

### Order management
- Maintain a target set of resting orders:
  - cancel stale orders
  - replace orders when the reference price moves enough
  - optionally batch submissions/cancels when supported

### Risk / safety
- Hard kill switch (stop placing new orders; cancel all)
- Max open orders
- Max inventory / exposure per outcome token
- Max notional per market
- “Dry-run” mode: compute + log intended actions, but never send orders
- Always assume API rate limits / throttling exist; backoff on throttling

### Observability
- Structured logs: market state, orders desired, orders live, diffs, errors
- Metrics hooks (optional): counts of cancels/places, WS disconnects, loop latency

---

## Configuration
### Secrets (never commit)
Create `.env` locally (do not commit). For compatibility with the current template:
- `PRIVATE_KEY=...`
- `RPC_URL=...`
- `CLOB_API_URL=...`

### Runtime config
`config.env` controls which market + strategy file is used:
- `CONDITION_ID=` (hex string market condition id)
- `STRATEGY="amm" | "bands"`
- `CONFIG="./config/<strategy>.json"`

---

## Milestones & Acceptance Criteria
### M0 — Repo boot + tooling
- Can create venv, install deps, run unit tests
- CI/lint optional, but local dev loop is stable

### M1 — Read-only market data
- WS client connects and streams book updates for a chosen market
- Local book model produces: best bid/ask, midpoint, spread
- Unit tests for book update logic

### M2 — Dry-run quoting
- Given market state (best bid/ask), produce expected quote set
- Correct tick-size rounding
- Log diffs vs current target orders
- 100% dry-run: no order submission

### M3 — Paper/live-small with strict risk limits
- Place/cancel orders with:
  - max inventory
  - max orders
  - kill switch
  - backoff on throttling
- Reconciliation: open orders on startup vs desired state
- Integration test / smoke run checklist exists

### M4 — Refinement
- Inventory skew
- Better re-quote triggers (event-driven)
- Batching and reduced churn
- Monitoring hooks

---

## Testing Strategy
- Unit tests: tick rounding, quote generation, order diff logic, book model
- Smoke tests: WS connect/disconnect/reconnect, read-only run for N minutes
- “No-trade” invariant tests for dry-run mode

---

## Operational Guardrails
- Never run with funded keys until dry-run is stable.
- Start with smallest possible size and strict limits.
- Always monitor logs during runs.
- Keep a manual kill switch available.

---

## Glossary
- CONDITION_ID: identifier for the underlying market condition
- Tick size: minimum price increment; orders must conform
- “Market order”: implemented as an aggressive limit order on Polymarket