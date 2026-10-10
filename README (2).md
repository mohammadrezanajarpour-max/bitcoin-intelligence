# Gold Intelligence V6.6 — Observable Scalp PAPER

A Streamlit XAU/USD research and simulated forward-execution application, upgraded from V6.5 while preserving its strategy presets, risk controls and TP lifecycle. The interface and reports are English. Charts are compact: 480 px for analysis and 500 px for the optional TradingView widget.

**Experimental PAPER only. The scalp preset is UNVALIDATED, with gate_pass=False. No profitability or immediate entry is promised.** Research candidates that fail the robust gate remain ineligible. The explicitly requested experimental reference-simulation preset is a separate, labelled exception, not a research PASS.

## Deployment

1. Extract the ZIP and upload exactly `app.py`, `requirements.txt`, and `README.md` to your GitHub repository.
2. Deploy on Streamlit Community Cloud with `app.py` as entrypoint and Python 3.11 or 3.12.
3. Configure Secrets privately:

```toml
TWELVEDATA_API_KEY = "YOUR_KEY"
# Optional durable database dedicated to this PAPER project:
# DATABASE_URL = "postgresql+psycopg2://user:password@host/scalp_db"
```

4. Auto PAPER and active-session monitoring default ON; quote policy defaults to REFERENCE_SIMULATION for this explicitly requested experimental edition. Starting PAPER equity defaults to $10,000. This is not deposited money.
5. Check Cycle Health, News Calendar and Diagnostic Lab. New positions require a confirmed closed-candle setup, fresh data, a cost-aware plan, news clearance and risk approval. No setup means no trade.
6. To stop new entries, disable Auto PAPER or enable Kill switch. Keep monitoring active to manage existing positions. Model deactivation persists; reactivation has a separate button.

V6.6 keeps the **V6.5 database identity `gold_v6_5_scalp_paper.db`**, its parameter version and its position tables so existing V6.5 trades can continue to be managed if the database survives deployment. It adds `scalp_candle_audit_v66` without rewriting existing trades. V6.3/V6.4 databases are not imported. SQLite files on Cloud can disappear on restarts/redeployment: export the old journal first. PostgreSQL is preferred for durable storage; its deployment has not been verified live here. Do not point DATABASE_URL at an unrelated project database. A previous inactive model is not silently reactivated.

## Architecture and authority

Actual Twelve Data reference quote + closed OHLC → causal indicators → closed-15m regime → directional scalp setup → cost-aware TradePlan → news guard → Risk Engine → Execution Engine → Journal.

Only Execution Engine creates or changes positions. Protective replay of existing positions runs before new-entry gates. Every new PAPER position must pass risk approval and execution-time rechecks. The news guard is rechecked immediately before execution. TradingView `FXPRO:XAUUSD` is **visual only**, never scraped or used for calculations. Backend symbol is Twelve Data `XAU/USD`. No secrets are embedded or printed; provider errors are sanitized.

## V6.6 additions

- **Readable entry decisions:** current reason plus a route-by-route table of actual values, required values and pass/fail results. Explains regime, RSI, body size, Bollinger expansion/touch, prior levels, retests, patterns, session and optional volume. Rules explain the unchanged signal predicates; they are not a second trading model or confidence probability.
- **Persistent opportunity audit:** one record per account/closed-5m-candle/parameter-version. Repeated monitoring updates an attempt count rather than inventing extra opportunities. Signal/fill/block flags remain latched when later checks reject an already filled candidate. Counters cover the most recent 10,000 records, starting at V6.6 installation; block categories may overlap. A cycle rejected before signal evaluation must not be interpreted as “no market opportunity.” Errors remain in Cycle Health; failed cycles are not counted as successfully evaluated candles.
- **Frozen scalper research replay:** uses cached 5m OHLC and locally derived 15m context, the current independent BUY/SELL parameters, identical signal predicates, structure/ATR/cost plan filters and the existing conservative TP lifecycle. Base and stress results and CSV exports are separate from the forward journal. No parameter fitting, no automatic activation, no robust PASS.
- **Position overlays:** actual PAPER entry, initial SL, five TP levels, current SL marker and recorded entry/SL/partial-close/exit events. Only the latest ten positions are overlaid. Closed history outside the visible window is not displayed. An open position may extend beyond the last fully closed candle; no synthetic market candle is generated there.
- **Independent lifecycle lab:** explicitly manufactured OHLC/indicator fixture → actual scalp signal → actual Risk Engine → actual Execution Engine → TP3 → TP5 → Journal. Separate temporary databases also test SL closure with new entries disabled and strict-policy rejection without bid/ask. It never uses the main database or an API, and its synthetic results are never mixed with PAPER performance. Passing it proves only this technical test path, not live connectivity, all possible execution conditions or profitability.

## Regime engine and BUY/SELL specialization

A fixed interpretable classifier uses ADX, EMA slope/separation normalized by ATR and trailing ATR percentile, with supporting Bollinger width, volatility and momentum evidence. Regimes are TREND_UP, TREND_DOWN, RANGE and VOLATILE; incomplete evidence yields UNKNOWN. The 15m candle becomes available only at its closing time. Backward as-of merging into 5m close decisions prevents same-bar higher-timeframe leakage. Prior levels exclude the current bar. No backward filling of future observations or random time-series splits.

The experimental router permits BUY breakout/retest in TREND_UP, SELL breakout/retest in TREND_DOWN, and separate BUY/SELL rejection setups in RANGE. VOLATILE/UNKNOWN block entries. These are experimental design assumptions, not historically demonstrated universal truths. Setup priority is retest, then breakout/rejection as eligible; conflicting directions block entry. There is no vote across all strategies.

BUY parameters: breakout buffer 0.10 ATR, trend RSI 52–75, minimum stop 1.3 ATR, RR 1.2. SELL: buffer 0.15 ATR, RSI 25–48, minimum stop 1.5 ATR, RR 1.3. These presets are not fitted to the observed V6.3 audit. Default session filter is ALL; optional UTC London 07–15, New York 12–20 and overlap 12–15 are fixed illustrative windows, not DST-aware exchange schedules or validated session advantages. UTC is used internally; Istanbul timestamps are displayed where useful.

### Setups

**Scalp Breakout:** close beyond the prior ten-candle high/low plus ATR buffer, matching candle direction, body at least 50% of range, directional RSI, correct side of Bollinger midpoint. Band width must increase from the previous bar and be at least 80% of the trailing median width. Wick-only penetrations fail.

**Scalp Retest:** prior candle closes beyond its already-known breakout level; the current candle retests that frozen level within ATR tolerance and closes in the breakout direction. BUY low tolerance is −0.30/+0.15 ATR; SELL high tolerance is the mirror. This version checks only the immediate next candle, not a multi-candle pending-order state.

**Scalp Rejection:** RANGE only. BUY touches prior support within 0.2 ATR and the lower Bollinger band, closes back above the band with a bullish pin/engulf and bullish candle, RSI ≤45. SELL mirrors resistance/upper band with bearish pin/engulf, bearish close and RSI ≥55.

RSI14, Bollinger20/2, EMA20/50/100/200, ATR14, ADX14, ROC10, MACD and Stochastic are available as evidence. Not every displayed indicator is an entry filter. Provider volume is retained if supplied; it is not fabricated or represented as consolidated gold-market volume. Relative volume uses current volume / mean of the previous 20 valid bars. Requiring volume is opt-in; when enabled, missing volume blocks entries and relative volume must be ≥1.1.

## Risk, exposure and cost model

Fixed original PAPER volume **0.03 lot**. PAPER assumption: 1 lot = 100 oz, therefore 3 oz. Displays risk USD, risk %, notional and notional/equity. This fixed lot may exceed 1× equity; historical research uses 1× notional sizing and is not equivalent to fixed-lot PAPER returns.

Max two global open positions, max one own strategy position, same-direction protection, candidate/hash duplication protection, five-minute rolling-fill protection, 2% per-trade risk, 4% aggregate risk, 3% daily drawdown, kill switch, quote freshness and spread protection are retained. Execution rechecks admission and fill risk. Local process locks do not establish atomic admission across multiple replicas; this prototype is single-process.

STRICT_EXECUTABLE blocks entries without genuine executable bid/ask. No fabricated bid/ask is produced. The unvalidated scalp preset is additionally restricted to opt-in/reference-simulation policy, even with executable quotes present.

Base costs: spread **$0.30/oz**, slippage **$0.05/oz each side**. Stress: **$0.50/oz**, **$0.10/oz each side**. PAPER costs are configurable in the sidebar; replay comparison uses fixed base/stress assumptions. Stop distance is the larger of the ATR minimum and the signal-candle structure stop with a 0.15 ATR margin. Entry rejects stop >3 ATR, stop <2.5×roundtrip cost, TP1 <1.5×roundtrip cost, or reference displacement >0.4 ATR from signal close. Price gaps and adverse exit costs are modeled conservatively.

## TP lifecycle

- TP1: move SL to TP1 from the next candle.
- TP2: hold.
- TP3: close exactly **50% of original volume = 0.015 lot**.
- TP4: move remaining SL to TP3 from the next candle.
- TP5: close all remaining volume.

Stops take priority when stop and target are both inside an OHLC candle. Target distances retain the legacy RR scaling: BUY RR1.2 uses 0.48R/0.84R/1.20R/1.56R/2.04R; SELL RR1.3 uses 0.52R/0.91R/1.30R/1.69R/2.21R. TP state transitions and original-volume half-close are unchanged. A minute that began before a PAPER fill is excluded from replay to avoid using pre-fill price action; some intraminute movement may be missed.

## Research methodology and replay limits

Base deterministic research families are EMA Pullback, Donchian Breakout, Bollinger Mean Reversion, MACD Trend, Liquidity Sweep, BOS / Structure Break, Candlestick + Trend, Multi-Timeframe Breakout, Session Breakout and Regime Ensemble. Regime-Adaptive Composite routes among sub-strategies; the current 5m scalp composite is an experimental execution preset.

The preserved V6.4 family research uses time-ordered inner/outer walk-forward, separate regime/BUY/SELL route selection, neighboring-parameter robustness, minimum trades, month concentration penalties, regime coverage/consistency, fold consistency and base/stress/spread/slippage comparisons. Score components are displayed individually and are not probabilities. Default historical development is 400 days before a conservative observed-audit boundary, plus a separately labelled historical audit. The V6.3 observed 90-day audit (approximately −2.77%, PF 0.69, gate FAIL) is not reused as untouched or fitted to create a pass. Exact prior dates were unavailable; do not move the boundary later to incorporate observed outcomes. ML remains a time-ordered research benchmark, never executable.

The base-family robust results **do not validate the new scalp composite**, and their activation button is disabled for this edition. The V6.6 scalp replay adds an inspectable frozen-rule diagnostic, not nested optimization or a new robust approval gate.

Replay entries use **next-bar open**, not the current live reference quote. The stop formula uses that next open, signal-bar ATR/structure, and adverse fill costs. Research uses one active position at 1× notional; it cannot replicate fixed-lot equity, account limits, quote freshness, rolling fills or daily loss guard. Historical news is unavailable from the weekly feed and is not applied. Replay exits are evaluated on 5m OHLC, while forward protection uses 1m; terminal/time exits are forced to calculate a finite research return. Consequently replay and actual forward fills can differ. Do not call this an exact broker replay or use it to retune against the observed audit. No future forward results are read during replay or fitting. Changing a preset requires a new version and a new future observation period.

**15% over approximately three months at 1× is a target, not a guarantee.** Missing evidence or failed robustness means FAIL/NOT TESTED, not a fabricated pass. Historical success does not ensure future returns.

## News, data pacing and health

Economic calendar: official weekly Forex Factory/Fair Economy JSON export:
https://nfs.faireconomy.media/ff_calendar_thisweek.json

Calendar requests are cached for about ten minutes, schema/timezone/current-week checked, and snapshot freshness is required. USD/ALL HIGH/MEDIUM releases block new entries from 20 minutes before through 20 minutes after. Missing/stale/invalid calendar blocks entries by default. “Allow PAPER without a valid calendar” is opt-in, labelled UNPROTECTED_OPT_IN and journaled; it does not mean there are no news events. This is a scheduled-release guard, not news sentiment, complete geopolitical coverage or prediction of market direction.

Active-session fragment runs approximately every 30 seconds. 5m bars are cached per five-minute bucket; 1m per minute; reference quote fetched per cycle. 15m/30m/1h derive locally from the downloaded 5m base. Up to 4800 current 5m bars and a short 1m window are requested. Historical research downloads the lowest selected interval once, with local resampling, chunk caches, pacing, retry/backoff, HTTP/API 429 and Retry-After handling. Long 5m research remains optional. API access, quota and data availability depend on the user's plan.

Closed 5m age ≤360 seconds and 1m age ≤180 seconds are checked; future timestamps fail. Risk applies additional quote freshness. Cycle Health records successful/failed attempts, timestamps, data ages, reason, regime, news/volume and fill identity. A successful data cycle does not prove that a setup or a risk-approved trade exists. Stale/error states must not be dismissed as “waiting for a signal.”

## Forward procedure and known limits

1. Deploy, inspect fresh Cycle Health, news availability and active experimental preset.
2. Run the isolated lab to inspect technical lifecycle without touching main trades.
3. Observe real closed-bar decisions and audit counts. A confirmed signal still needs cost/news/risk clearance.
4. Inspect Paper Positions, overlays and Journal for actual PAPER SL/TP events; export both journal and decision audit regularly.
5. Assess setup/BUY/SELL/regime/session results across enough future trades. Do not change parameters merely because one screenshot has no signal.

Journal preserves timestamp, setup/regime/side, entry/stop/targets, signal reason, parameter version, assumed costs, news/volume/session evidence, result, P/L, R multiple and regime change observations. Starting equity is manual; account returns need capital reconciliation.

Monitoring is **not a 24/7 background service**. Closing the page or Cloud sleeping can stop entry checks and protective management. A short 1m history cannot guarantee reconstruction after long downtime. Reference prices are not executable broker quotes. OHLC cannot resolve intrabar order beyond conservative assumptions. SQLite is ephemeral; multi-replica concurrency, PostgreSQL, live provider quotas, production calendar access and future profitability are not verified live. This delivery does not deploy to or operate the user's account.

Telegram, cTrader and live broker execution are **DISABLED**. No Telethon dependency.

## Local verification for this delivery

Python compile and AST parse; English-only runtime string check; compact chart height; synthetic regime and causal higher-timeframe tests; independent BUY/SELL; nested split ordering and audit exclusion; signal → risk → execution; fixed 0.03 lot and exact TP3 0.015; stop-first/kill/duplicates/daily loss; protective management with entries disabled; failed activation; sanitized API errors and 429 Retry-After; decision deduplication; diagnostics versus masks; replay feature causality/cost stress; chart overlays; isolated TP/SL lifecycle; Streamlit initial/populated UI and replay/lab buttons. Detailed executed counts are reported with the delivered files; test scripts and synthetic fixtures are not part of the three-file deployment ZIP.

Executed result: **55 unittest checks passed** (26 retained scalp, 16 risk/research/data/security and 13 new diagnostics/replay/lab checks), plus initial and populated Streamlit UI, replay button and independent lab button checks. Compile/AST and ZIP integrity verified.
