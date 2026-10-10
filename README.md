# Bitcoin Intelligence V1 — LONG / SHORT PAPER

An English Streamlit prototype adapted from the Gold Intelligence V6.6 causal indicator, regime-routing and diagnostic components. It runs a separate BTC-denominated simulated ledger, with BTC/USD public reference data from Coinbase and a compact chart. **No real orders, exchange account access or credentials are used.** The experimental preset is UNVALIDATED; a profitable BTC strategy has not been established.

## Deployment

Extract `bitcoin_intelligence_v1_long_short_paper.zip`; upload its three files to a **separate GitHub repository** so the gold app remains intact. Streamlit Community Cloud entrypoint: `app.py`, Python 3.11 or 3.12. Install `requirements.txt`.

No Coinbase or Twelve Data API key is required. Optional Streamlit Secrets:

```toml
DATABASE_URL = "postgresql+psycopg2://user:password@host/bitcoin_paper"
```

Use a database dedicated to this project; never reuse the gold database. Without Secrets, SQLite defaults to `bitcoin_intelligence_v1.db`. SQLite can disappear after Cloud restart/redeployment; export the forward journal and decision audit regularly. PostgreSQL is supported through SQLAlchemy but has not been verified live. Single process, single operator only; cross-replica admission is not atomic.

Auto PAPER and active-session monitoring default ON. Reference simulation is explicitly selected by default for this requested experiment. Configure starting equity and cost assumptions before beginning a fresh forward period. Missing data, missing calendar, stale quotes or rejected setups can mean **no trades**; automatic entry is not unconditional.

## Scope of LONG / SHORT

LONG earns simulated P/L from rising BTC/USD; SHORT earns simulated P/L from falling BTC/USD. Both use the same public **spot** reference market in a virtual derivative-style ledger. There is no spot short borrowing, exchange margin, perpetual contract basis, leverage, liquidation, real funding or broker execution. These results are not a faithful replica of a particular futures venue.

The app caps new-entry total notional at 1× realized equity, including entry-fee allowance. Market movement can change exposure afterward. Quantity is BTC, not gold lots; there is no 0.03 lot or 100-ounce assumption. Default per-trade estimated stop loss is 0.5% of equity, including assumed entry/exit fees and adverse stop-fill costs; quantity also obeys the notional cap. Stops can gap, so actual simulated loss may exceed the estimate.

## Architecture

Public closed OHLCV + reference ticker → causal indicators → closed-15m regime → independent LONG/SHORT setups → cost-aware plan → scheduled-news guard → Risk Engine → Execution Engine → journal and decision audit.

Only Execution Engine creates or modifies positions. It verifies approved plan hashes/expiry, persistent activation, costs, quotes and risk conditions under a local transaction lock before admission. Existing positions are processed before new-entry news, activation, kill-switch and setup gates. Model deactivation is persistent and does not turn back on silently.

The public client only sends GET requests to fixed Coinbase BTC-USD candles/ticker routes and the scheduled calendar export. There are no order-submission endpoints or private exchange secrets. Provider exceptions and database errors are sanitized. TradingView `COINBASE:BTCUSD` is visual only; no widget data is scraped or used in calculations.

## Data and rate limits

Coinbase Exchange public candles use `[time, low, high, open, close, volume]`, with at most 300 per request. Four paced 299-interval windows request approximately 1,200 five-minute candles; overlaps are deduplicated and windows trimmed. A separate recent one-minute window supports protection. Closed candles only are retained; malformed/nonfinite/negative or inconsistent OHLC data is rejected. No synthetic market data or missing candles are fabricated.

Five-minute history is cached per five-minute bucket, one-minute history per minute; ticker is fetched for each cycle. Retry/backoff and HTTP 429 Retry-After delays are bounded; errors stop the cycle. Provider availability, geographic access, incomplete intervals and schema changes can block operation. The last 650 primary bars must be continuous; incomplete higher-timeframe groups are discarded. 15m derives locally from 5m, with no repeated higher-timeframe download.

The ticker includes last-trade reference price/time and supplied bid/ask. Receipt and source ages must both be 0–30 seconds for entry/manual close. Data age checks also require closed 5m ≤360 seconds and 1m ≤180 seconds for entry. STRICT_EXECUTABLE requires actual supplied bid/ask; missing quotes are never fabricated. It remains **PAPER execution**, even in STRICT policy. Historical OHLC protection uses assumed adverse costs, not reconstructed historical order books.

Coinbase volume represents that venue only, not total cryptocurrency-market volume. Relative volume uses the previous 20 bars as its reference. Requiring valid volume with relative volume ≥1.1 defaults ON; it can be explicitly disabled for an experiment. No cross-venue funding, open interest, liquidation or order-flow feed is implemented.

## Strategy and regime routing

Preserved indicators: RSI14, Bollinger20/2, EMA20/50/100/200, ATR14, ADX14, ROC10, MACD and Stochastic. Some are diagnostic evidence, not mandatory signal filters.

An interpretable fixed classifier uses ADX, EMA slope and separation normalized by ATR, and the past ATR percentile to label TREND_UP, TREND_DOWN, RANGE or VOLATILE. Incomplete data yields UNKNOWN. A 15m regime is available only when that candle closes; backward as-of merging attaches it to 5m decision-close timestamps. Levels exclude the current candle; no future backward filling or random train/test split.

- **TREND_UP:** LONG breakout/retest.
- **TREND_DOWN:** SHORT breakout/retest.
- **RANGE:** independent LONG/SHORT rejection at support/resistance and outer Bollinger bands.
- **VOLATILE / UNKNOWN:** no new entries.

These are illustrative presets adapted from the prior architecture, **not tuned or robustly validated for Bitcoin**. BUY in internal rule tables corresponds to LONG; SELL corresponds to SHORT. LONG/SHORT parameters differ: breakout buffers 0.10/0.15 ATR; minimum stops 1.3/1.5 ATR; RR factors 1.2/1.3. Trend RSI ranges are 52–75 LONG and 25–48 SHORT. RANGE RSI is ≤45 LONG or ≥55 SHORT, plus pin/engulf, band/level touch and a directional closed candle.

Breakouts require a close beyond the preceding ten-candle level plus buffer, matching candle direction, body ≥50% of range and Bollinger expansion. Wick-only penetration is insufficient. Retests consider only the immediately following candle on the frozen pre-breakout level. Successful retests have priority over same-direction breakouts; there is no universal strategy vote. Conflicting directions block entries. The rule table displays actual versus required values.

## Risk and costs

Default starting PAPER equity: $10,000. Default per-trade estimated risk: 0.5%; selectable up to 2%. Aggregate frozen risk limit: 2%. Max two global positions, max one own position; candidate duplicates and same direction blocked; five-minute rolling-fill spacing; kill switch; persistent daily 3% marked-equity drawdown latch; fresh quote/1m checks; spread cap 10 bps. Daily marked equity is observed on successful cycles independently of whether a signal exists. Gaps/downtime can hide peaks or worsen losses; the guard is not an exchange guarantee.

Cost inputs are **assumptions**, not verified Coinbase fee-tier quotes:

- Fee: 10 bps each side (0.10%).
- Full reference spread: 2 bps.
- Slippage: 1 bp each side.
- Replay stress: 20 bps fee each side, 4 bps full spread, 2 bps each-side slippage.

Fees are charged separately on entry and every partial/full exit; entry fee is included in net realized P/L immediately. Base/stress replay applies each set of assumptions independently. Spread/slippage worsen both entry and exit. Structure stop uses signal low/high plus 0.15 ATR, with a minimum directional ATR distance. Rejects stop >3 ATR, movement >0.4 ATR after signal, stop less than 2.5× estimated roundtrip costs, or TP1 less than 1.5× those costs. High assumed fees can therefore reject many short scalps; this is shown as COSTS_TOO_HIGH_FOR_SETUP rather than silently forcing entries.

Optional financing input is an assumed **positive cost charged to both directions per eight hours**; zero means unmodeled. It is not an actual signed perpetual funding rate and cannot be used to claim futures-net profitability.

## TP lifecycle and protection

Targets retain RR scaling of the legacy 0.4/0.7/1.0/1.3/1.7 ladder. With LONG RR1.2 they are 0.48R/0.84R/1.2R/1.56R/2.04R; SHORT RR1.3 uses 0.52R/0.91R/1.3R/1.69R/2.21R.

TP1 schedules SL to TP1 for the next candle; TP2 holds; TP3 closes **exactly half of original BTC quantity**; TP4 schedules remaining SL to TP3; TP5 closes the remainder. Original size is quantized to an even number of satoshis so the half is exact. No quantity increases or averaging down. Stops are checked first if SL and TP both occur inside a candle; stop gaps use the adverse open. Pre-entry minutes are excluded; intraminute movement may be missed.

Protection uses the recent 1m OHLC, with last-processed timestamps to avoid duplicate exits. Missing continuity flags a position with `gap=True`; later observed bars may still protect it, but lost history is not reconstructed. New entries are blocked while an open gap position needs reconciliation. A manual **simulated reference close** through Execution Engine is provided, requiring a fresh quote and recording the close in the journal. It cannot recover the true missed fill.

## Dashboard, journal and forward workflow

Eleven English tabs: Live Dashboard, Analysis & Patterns, Regime Engine, Paper Positions, Journal, Performance, Risk Control, News Calendar, Cycle Health, Replay & Lab, Setup. Backend charts are 480 px high; optional TradingView is about 460 px. Entry, current SL and targets overlay the recent chart. Journal includes opening costs, version, regime and reason, TP/SL events, partial quantities, net P/L, assumed financing and exit regime observations.

Cycle Health persists attempts, successes, failures, current reason and candle timestamps. Counts are unique candle/version records, not repeated polling counts; signal/news/risk/fill flags latch and may overlap. Last 10,000 records retained. A success means data/evaluation completed, not a trade or profit. Stale/error states are displayed separately. Exports: rules, journal, decision audit and replay positions.

1. Deploy separately from the gold app.
2. Set costs/equity, verify public data freshness and scheduled calendar status.
3. Run the independent synthetic lab; this checks a manufactured signal through risk/execution and exact-half TP3/TP5 in a temporary database.
4. Observe closed-bar decisions and real PAPER journal fills. Do not infer full execution health merely from a moving chart.
5. Freeze assumptions for a future test period. Compare enough LONG/SHORT/setup/regime trades and adverse costs before considering changes. Parameter changes require a new version and new future evaluation.

## Replay and validation limits

The cached replay is a **frozen diagnostic**, using causal setup features, next-bar-open reference entries, the same quantity/cost filters, Risk Engine and Execution Engine in a separate temporary ledger. It uses coarse 5m protection rather than forward 1m precision; final positions are force-closed at the last data close. Historical news is not applied, and this limited history is not a 12-month research study. It uses risk-based BTC sizing with a 1× cap, not constant-full-notional return sizing. It cannot reproduce every real fill, borrow, margin or funding detail.

No nested BTC parameter optimization, neighboring-parameter robustness gate, validated ML, final untouched BTC holdout or automatic robust-model activation is implemented in this first crypto edition. The experimental preset is labelled UNVALIDATED throughout; it must not be described as a robust PASS. Previous gold historical outcomes are not evidence for BTC. A 15% quarterly return, if used as a research objective, is a target rather than a guarantee.

Scheduled-news guard uses the Forex Factory/Fair Economy weekly export, USD/ALL HIGH/MEDIUM releases ±20 minutes. Missing/stale/invalid calendar blocks entries by default. Optional unprotected mode is explicit and shown in the UI. This is not breaking-news/crypto sentiment or complete macro coverage.

Monitoring runs approximately every 30 seconds only in an active Streamlit session. Closing the page or Cloud sleeping can stop both entry checks and protection, despite crypto markets operating on weekends. This is not a 24/7 service. PostgreSQL, production-provider access/quotas and future PAPER results are not verified live in this delivery. Telegram, cTrader, live broker/exchange execution and liquidation feeds are disabled.

## Official provider references

- https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-product-candles
- https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-product-ticker
- https://www.forexfactory.com/calendar

Local verification results are included with the delivery report; test fixtures are not included in the three deployment files.

Executed delivery verification: **34 unittest checks passed**, Python compile and AST parse passed, initial/offline and populated 11-tab Streamlit UI passed, synthetic lab and base/stress replay UI buttons passed. Provider production access and forward outcomes were not verified live.
