# Gold Intelligence V6.6 — Observable Scalp PAPER; preserved V6.3-V6.5 components
# Unified XAUUSD strategy research + paper-forward deployment.
# The modular source remains the canonical development structure.



# ===== BEGIN domain/enums.py =====
from enum import Enum


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class Grade(str, Enum):
    A_PLUS = "A+"
    A = "A"
    B = "B"
    C = "C"


class QuotePolicy(str, Enum):
    STRICT_EXECUTABLE = "STRICT_EXECUTABLE"
    REFERENCE_SIMULATION = "REFERENCE_SIMULATION"


class PositionStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"
    UNMARKABLE = "UNMARKABLE"


class CandidateStatus(str, Enum):
    WATCH_ONLY = "WATCH_ONLY"
    APPROVED = "APPROVED"
    BLOCKED = "BLOCKED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    EXECUTED = "EXECUTED"


class FeedState(str, Enum):
    OK = "OK"
    STALE = "STALE"
    DISCONNECTED = "DISCONNECTED"
    MARKET_CLOSED = "MARKET_CLOSED"
    ERROR = "ERROR"
# ===== END domain/enums.py =====


# ===== BEGIN domain/schemas.py =====

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional



@dataclass(frozen=True)
class Quote:
    symbol: str
    reference_price: Decimal
    bid: Optional[Decimal]
    ask: Optional[Decimal]
    source_timestamp: Optional[datetime]
    received_timestamp: datetime
    source: str
    price_type: str = "REFERENCE"
    quality_flags: tuple[str, ...] = ()

    @property
    def spread(self) -> Optional[Decimal]:
        if self.bid is None or self.ask is None:
            return None
        return self.ask - self.bid


@dataclass(frozen=True)
class FeedHealth:
    state: str
    quote_source_age_seconds: Optional[float]
    latest_closed_1m_age_seconds: Optional[float]
    provider_status: str
    details: tuple[str, ...] = ()


@dataclass(frozen=True)
class PatternDetection:
    pattern_type: str
    timeframe: str
    direction: str
    quality_score: int
    level: Optional[Decimal]
    zone_low: Optional[Decimal]
    zone_high: Optional[Decimal]
    detected_at: datetime
    confirmed_at: datetime
    explanation: str
    detector_version: str = "v6-strategy-1"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvidenceGroup:
    name: str
    value: float
    weight: float
    contribution: float
    explanation: str


@dataclass(frozen=True)
class SignalEvaluation:
    side: Side
    buy_index: int
    sell_index: int
    evidence_completeness: int
    setup_quality: int
    grade: Grade
    status: CandidateStatus
    evidence: tuple[EvidenceGroup, ...]
    reasons_for: tuple[str, ...]
    reasons_against: tuple[str, ...]
    evaluated_at: datetime

    @property
    def directional_gap(self) -> int:
        return abs(self.buy_index - self.sell_index)


@dataclass(frozen=True)
class TradePlan:
    candidate_id: str
    side: Side
    entry_reference: Decimal
    initial_sl: Decimal
    provisional_targets: tuple[Decimal, Decimal, Decimal, Decimal, Decimal]
    original_lot: Decimal
    gross_risk_usd: Decimal
    risk_pct: Decimal
    grade: Grade
    buy_index: int
    sell_index: int
    evidence_completeness: int
    setup_quality: int
    quote_policy: QuotePolicy
    reasons_for: tuple[str, ...]
    reasons_against: tuple[str, ...]
    plan_hash: str
    created_at: datetime
    source: str = "OWN_SYSTEM"
    research_authorized: bool = False
    target_multipliers: tuple[Decimal, Decimal, Decimal, Decimal, Decimal] = (
        Decimal("0.40"), Decimal("0.70"), Decimal("1.00"), Decimal("1.30"), Decimal("1.70")
    )


@dataclass(frozen=True)
class RiskDecision:
    approved: bool
    reason_codes: tuple[str, ...]
    explanation: tuple[str, ...]
    approved_at: datetime
    expires_at: datetime
    plan_hash: str


@dataclass(frozen=True)
class AnalysisBundle:
    by_timeframe: dict[str, dict[str, float]]
    patterns: tuple[PatternDetection, ...]
    latest_closed_1m_at: Optional[datetime]
    complete: bool
    missing: tuple[str, ...] = ()
# ===== END domain/schemas.py =====


# ===== BEGIN config.py =====

from dataclasses import dataclass
from decimal import Decimal
import os
from typing import Mapping, Any



@dataclass(frozen=True)
class Settings:
    symbol: str = "XAU/USD"
    tradingview_symbol: str = "FXPRO:XAUUSD"
    database_url: str = "sqlite:///gold_v6_5_scalp_paper.db"
    twelve_data_api_key: str = ""
    quote_policy: QuotePolicy = QuotePolicy.STRICT_EXECUTABLE
    quote_freshness_seconds: int = 90
    max_spread_usd: Decimal = Decimal("0.50")
    reference_assumed_spread_usd: Decimal = Decimal("0.30")
    reference_slippage_usd: Decimal = Decimal("0.05")
    fixed_lot: Decimal = Decimal("0.03")
    contract_oz_per_lot: Decimal = Decimal("100")
    max_open_positions: int = 2
    max_own_positions: int = 1
    max_risk_per_trade_pct: Decimal = Decimal("2.0")
    max_aggregate_risk_pct: Decimal = Decimal("4.0")
    monitor_interval_seconds: int = 60


def _get(name: str, secrets: Mapping[str, Any] | None, default: str = "") -> str:
    if secrets and name in secrets:
        value = secrets[name]
        return str(value) if value is not None else default
    return os.getenv(name, default)


def load_settings(secrets: Mapping[str, Any] | None = None, overrides: dict[str, Any] | None = None) -> Settings:
    base = Settings(
        database_url=_get("DATABASE_URL", secrets, "sqlite:///gold_v6_5_scalp_paper.db"),
        twelve_data_api_key=_get("TWELVEDATA_API_KEY", secrets, ""),
    )
    if not overrides:
        return base
    data = dict(base.__dict__)
    data.update(overrides)
    if isinstance(data.get("quote_policy"), str):
        data["quote_policy"] = QuotePolicy(data["quote_policy"])
    for key in [
        "max_spread_usd", "reference_assumed_spread_usd", "reference_slippage_usd",
        "fixed_lot", "contract_oz_per_lot", "max_risk_per_trade_pct", "max_aggregate_risk_pct"
    ]:
        if key in data and not isinstance(data[key], Decimal):
            data[key] = Decimal(str(data[key]))
    return Settings(**data)
# ===== END config.py =====


# ===== BEGIN database.py =====

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


class Account(Base):
    __tablename__ = "accounts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    equity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    kill_switch: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    auto_paper_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ActiveStrategyModel(Base):
    __tablename__ = "active_strategy_v6"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    family: Mapped[str] = mapped_column(String(120), nullable=False)
    params_json: Mapped[str] = mapped_column(Text, nullable=False)
    metrics_json: Mapped[str] = mapped_column(Text, nullable=False)
    gate_pass: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    activated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SignalCandidateModel(Base):
    __tablename__ = "signal_candidates"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source: Mapped[str] = mapped_column(String(40), nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    buy_index: Mapped[int] = mapped_column(Integer, nullable=False)
    sell_index: Mapped[int] = mapped_column(Integer, nullable=False)
    completeness: Mapped[int] = mapped_column(Integer, nullable=False)
    setup_quality: Mapped[int] = mapped_column(Integer, nullable=False)
    grade: Mapped[str] = mapped_column(String(8), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    entry_reference: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    sl: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    tp1: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    tp2: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    tp3: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    tp4: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    tp5: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    plan_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    reasons_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PaperPosition(Base):
    __tablename__ = "paper_positions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False, index=True)
    candidate_id: Mapped[str] = mapped_column(ForeignKey("signal_candidates.id"), nullable=False, unique=True)
    source: Mapped[str] = mapped_column(String(40), nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    quote_policy: Mapped[str] = mapped_column(String(40), nullable=False)
    entry: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    sl_initial: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    sl_current: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    pending_sl: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    pending_sl_effective_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tp1: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    tp2: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    tp3: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    tp4: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    tp5: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    original_lot: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    remaining_lot: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    frozen_initial_risk_usd: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=Decimal("0"))
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    tp1_hit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tp2_hit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tp3_hit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tp4_hit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tp5_hit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_processed_market_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TradeEvent(Base):
    __tablename__ = "trade_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    position_id: Mapped[int] = mapped_column(ForeignKey("paper_positions.id"), nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    price: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    pnl: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    details_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")


class MarketSnapshot(Base):
    __tablename__ = "market_snapshots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(24), nullable=False)
    reference_price: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    bid: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    ask: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    source: Mapped[str] = mapped_column(String(40), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


def create_db_engine(database_url: str):
    kwargs = {"pool_pre_ping": True, "future": True}
    if database_url.startswith("sqlite"):
        kwargs["connect_args"] = {"timeout": 30, "check_same_thread": False}
    engine = create_engine(database_url, **kwargs)
    if database_url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _sqlite_pragmas(dbapi_connection, _record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            try:
                cursor.execute("PRAGMA journal_mode=WAL")
            except Exception:
                pass
            cursor.close()
    return engine


def init_database(engine):
    Base.metadata.create_all(engine)


def make_session_factory(engine):
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
# ===== END database.py =====


# ===== BEGIN repositories/trading_repository.py =====

import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError



class TradingRepository:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    def ensure_account(self, name: str = "paper-main", equity: Decimal = Decimal("2500")) -> Account:
        with self.session_factory.begin() as s:
            account = s.scalar(select(Account).where(Account.name == name))
            if account is None:
                account = Account(
                    name=name,
                    equity=equity,
                    kill_switch=False,
                    auto_paper_enabled=False,
                    created_at=datetime.now(timezone.utc),
                )
                s.add(account)
                s.flush()
            return account

    def update_account(self, account_id: int, *, equity: Decimal | None = None, kill_switch: bool | None = None, auto_paper_enabled: bool | None = None):
        with self.session_factory.begin() as s:
            account = s.get(Account, account_id)
            if equity is not None:
                account.equity = equity
            if kill_switch is not None:
                account.kill_switch = kill_switch
            if auto_paper_enabled is not None:
                account.auto_paper_enabled = auto_paper_enabled
            s.flush()
            return account

    def get_account(self, account_id: int) -> Account:
        with self.session_factory() as s:
            return s.get(Account, account_id)

    def get_active_strategy(self):
        with self.session_factory() as s:
            return s.scalar(select(ActiveStrategyModel).where(
                ActiveStrategyModel.id == 1,
                ActiveStrategyModel.active == True,
            ))

    def set_active_strategy(self, family: str, params: dict, metrics: dict, gate_pass: bool):
        now = datetime.now(timezone.utc)
        with self.session_factory.begin() as s:
            obj = s.get(ActiveStrategyModel, 1)
            values = dict(
                family=family,
                params_json=json.dumps(params, ensure_ascii=False, sort_keys=True, default=str),
                metrics_json=json.dumps(metrics, ensure_ascii=False, sort_keys=True, default=str),
                gate_pass=bool(gate_pass),
                active=True,
                activated_at=now if obj is None else obj.activated_at,
                updated_at=now,
            )
            if obj is None:
                obj = ActiveStrategyModel(id=1, **values)
                s.add(obj)
            else:
                obj.family = family
                obj.params_json = values["params_json"]
                obj.metrics_json = values["metrics_json"]
                obj.gate_pass = bool(gate_pass)
                obj.active = True
                obj.activated_at = now
                obj.updated_at = now
            s.flush()
            return obj

    def deactivate_strategy(self):
        with self.session_factory.begin() as s:
            obj = s.get(ActiveStrategyModel, 1)
            if obj is not None:
                obj.active = False
                obj.updated_at = datetime.now(timezone.utc)

    def save_market_snapshot(self, quote):
        with self.session_factory.begin() as s:
            s.add(MarketSnapshot(
                symbol=quote.symbol,
                reference_price=quote.reference_price,
                bid=quote.bid,
                ask=quote.ask,
                source=quote.source,
                received_at=quote.received_timestamp,
            ))

    def save_candidate(self, candidate_id: str, evaluation, plan=None, source: str = "OWN_SYSTEM"):
        with self.session_factory.begin() as s:
            existing = s.get(SignalCandidateModel, candidate_id)
            reasons = json.dumps({
                "for": list(evaluation.reasons_for),
                "against": list(evaluation.reasons_against),
            }, ensure_ascii=False)
            values = dict(
                source=source,
                side=evaluation.side.value,
                buy_index=evaluation.buy_index,
                sell_index=evaluation.sell_index,
                completeness=evaluation.evidence_completeness,
                setup_quality=evaluation.setup_quality,
                grade=evaluation.grade.value,
                status=evaluation.status.value,
                reasons_json=reasons,
            )
            if plan:
                values.update(
                    entry_reference=plan.entry_reference,
                    sl=plan.initial_sl,
                    tp1=plan.provisional_targets[0],
                    tp2=plan.provisional_targets[1],
                    tp3=plan.provisional_targets[2],
                    tp4=plan.provisional_targets[3],
                    tp5=plan.provisional_targets[4],
                    plan_hash=plan.plan_hash,
                )
            if existing is None:
                obj = SignalCandidateModel(id=candidate_id, created_at=evaluation.evaluated_at, **values)
                s.add(obj)
            else:
                for k, v in values.items():
                    setattr(existing, k, v)

    def open_positions(self, account_id: int) -> list[PaperPosition]:
        with self.session_factory() as s:
            return list(s.scalars(select(PaperPosition).where(
                PaperPosition.account_id == account_id,
                PaperPosition.status == "OPEN",
            ).order_by(PaperPosition.id)))

    def all_positions(self, account_id: int) -> list[PaperPosition]:
        with self.session_factory() as s:
            return list(s.scalars(select(PaperPosition).where(
                PaperPosition.account_id == account_id
            ).order_by(PaperPosition.id.desc())))

    def position_for_candidate(self, candidate_id: str):
        with self.session_factory() as s:
            return s.scalar(select(PaperPosition).where(PaperPosition.candidate_id == candidate_id))

    def create_position(self, **kwargs) -> PaperPosition:
        with self.session_factory.begin() as s:
            p = PaperPosition(**kwargs)
            s.add(p)
            s.flush()
            s.refresh(p)
            return p

    def get_position(self, position_id: int):
        with self.session_factory() as s:
            return s.get(PaperPosition, position_id)

    def update_position(self, position_id: int, **values):
        with self.session_factory.begin() as s:
            p = s.get(PaperPosition, position_id)
            for k, v in values.items():
                setattr(p, k, v)
            s.flush()
            return p

    def add_event(self, position_id: int, idempotency_key: str, event_type: str, occurred_at, price=None, quantity=None, pnl=None, details: dict | None = None) -> bool:
        try:
            with self.session_factory.begin() as s:
                s.add(TradeEvent(
                    position_id=position_id,
                    idempotency_key=idempotency_key,
                    event_type=event_type,
                    occurred_at=occurred_at,
                    price=price,
                    quantity=quantity,
                    pnl=pnl,
                    details_json=json.dumps(details or {}, ensure_ascii=False, default=str),
                ))
            return True
        except IntegrityError:
            return False

    def events(self, position_id: int | None = None):
        with self.session_factory() as s:
            q = select(TradeEvent).order_by(TradeEvent.id.desc())
            if position_id is not None:
                q = q.where(TradeEvent.position_id == position_id)
            return list(s.scalars(q))

    def recent_candidates(self, limit: int = 100):
        with self.session_factory() as s:
            return list(s.scalars(select(SignalCandidateModel).order_by(SignalCandidateModel.created_at.desc()).limit(limit)))
# ===== END repositories/trading_repository.py =====


# ===== BEGIN engines/analysis_engine.py =====

import numpy as np
import pandas as pd


def wilder_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    result = 100 - (100 / (1 + rs))
    return result.fillna(50.0)


def wilder_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def enrich(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    x["ema20"] = x["close"].ewm(span=20, adjust=False).mean()
    x["ema50"] = x["close"].ewm(span=50, adjust=False).mean()
    x["ema200"] = x["close"].ewm(span=200, adjust=False).mean()
    x["rsi14"] = wilder_rsi(x["close"], 14)
    x["atr14"] = wilder_atr(x, 14)
    x["roc10"] = x["close"].pct_change(10)
    return x


def timeframe_snapshot(df: pd.DataFrame) -> dict[str, float]:
    if len(df) < 220:
        raise ValueError(f"Need >=220 candles for indicator snapshot; received {len(df)}")
    x = enrich(df)
    row = x.iloc[-1]
    required = ["close", "ema20", "ema50", "ema200", "rsi14", "atr14", "roc10"]
    if any(pd.isna(row[k]) for k in required):
        raise ValueError("Indicator warm-up incomplete")
    return {k: float(row[k]) for k in required}


def trend_evidence(s: dict[str, float]) -> float:
    score = 0.0
    score += 0.35 if s["ema20"] > s["ema50"] else -0.35
    score += 0.35 if s["ema50"] > s["ema200"] else -0.35
    score += 0.30 if s["close"] > s["ema20"] else -0.30
    return float(np.clip(score, -1, 1))


def rsi_momentum_evidence(s: dict[str, float]) -> float:
    rsi_ev = float(np.clip((s["rsi14"] - 50.0) / 20.0, -1, 1))
    roc_ev = float(np.clip(s["roc10"] / 0.004, -1, 1))
    return float(np.clip(0.55 * rsi_ev + 0.45 * roc_ev, -1, 1))
# ===== END engines/analysis_engine.py =====


# ===== BEGIN engines/pattern_engine.py =====

from datetime import timedelta
from decimal import Decimal
import numpy as np
import pandas as pd



def _pivots(df: pd.DataFrame, left: int = 3, right: int = 3):
    highs, lows = [], []
    if len(df) < left + right + 5:
        return highs, lows
    hv = df["high"].to_numpy()
    lv = df["low"].to_numpy()
    idx = df.index
    for i in range(left, len(df) - right):
        if hv[i] >= np.max(hv[i-left:i+right+1]):
            highs.append({"i": i, "price": float(hv[i]), "pivot_at": idx[i], "confirmed_at": idx[i+right]})
        if lv[i] <= np.min(lv[i-left:i+right+1]):
            lows.append({"i": i, "price": float(lv[i]), "pivot_at": idx[i], "confirmed_at": idx[i+right]})
    return highs, lows


def _cluster(points, tolerance: float, min_separation: int = 3):
    clusters = []
    for p in points:
        found = None
        for c in clusters:
            if abs(p["price"] - c["level"]) <= tolerance:
                if p["i"] - c["last_i"] >= min_separation:
                    found = c
                    break
        if found:
            found["prices"].append(p["price"])
            found["indices"].append(p["i"])
            found["confirmations"].append(p["confirmed_at"])
            found["level"] = float(np.mean(found["prices"]))
            found["last_i"] = p["i"]
        else:
            clusters.append({
                "level": p["price"], "prices": [p["price"]], "indices": [p["i"]],
                "confirmations": [p["confirmed_at"]], "last_i": p["i"],
            })
    return clusters


def _line(points):
    if len(points) < 3:
        return None
    xs = np.array([p["i"] for p in points[-4:]], dtype=float)
    ys = np.array([p["price"] for p in points[-4:]], dtype=float)
    if len(np.unique(xs)) < 2:
        return None
    slope, intercept = np.polyfit(xs, ys, 1)
    pred = slope * xs + intercept
    ss_res = np.sum((ys - pred) ** 2)
    ss_tot = np.sum((ys - ys.mean()) ** 2) or 1.0
    r2 = max(0.0, 1 - ss_res / ss_tot)
    return float(slope), float(intercept), float(r2)


def detect_patterns(df: pd.DataFrame, timeframe: str) -> list[PatternDetection]:
    if len(df) < 60:
        return []
    now = df.index[-1].to_pydatetime()
    atr = float((df["high"] - df["low"]).rolling(14).mean().iloc[-1])
    if not np.isfinite(atr) or atr <= 0:
        atr = float(df["close"].iloc[-1]) * 0.001
    tol = max(atr * 0.35, 0.01)
    highs, lows = _pivots(df, 3, 3)
    out: list[PatternDetection] = []

    # Support / resistance clusters with independently separated visits.
    for kind, pts, direction in [("RESISTANCE", highs[-30:], "BEARISH"), ("SUPPORT", lows[-30:], "BULLISH")]:
        clusters = _cluster(pts, tol)
        strong = [c for c in clusters if len(c["prices"]) >= 2]
        if strong:
            c = sorted(strong, key=lambda z: (len(z["prices"]), z["confirmations"][-1]), reverse=True)[0]
            q = min(100, 35 + 15 * len(c["prices"]))
            out.append(PatternDetection(
                pattern_type=kind, timeframe=timeframe, direction=direction, quality_score=q,
                level=Decimal(str(round(c["level"], 6))), zone_low=None, zone_high=None,
                detected_at=now, confirmed_at=c["confirmations"][-1].to_pydatetime(),
                explanation=f"{kind.title()} cluster with {len(c['prices'])} separated touches.",
                metadata={"touches": len(c["prices"]), "tolerance": tol},
            ))

    # Trendline evidence.
    hi_line = _line(highs)
    lo_line = _line(lows)
    if lo_line and lo_line[0] > 0 and lo_line[2] >= 0.55:
        out.append(PatternDetection(
            "RISING_TRENDLINE", timeframe, "BULLISH", int(min(100, lo_line[2] * 100)), None, None, None,
            now, lows[-1]["confirmed_at"].to_pydatetime() if lows else now,
            "Confirmed rising trendline through recent swing lows.", metadata={"slope": lo_line[0], "r2": lo_line[2]},
        ))
    if hi_line and hi_line[0] < 0 and hi_line[2] >= 0.55:
        out.append(PatternDetection(
            "FALLING_TRENDLINE", timeframe, "BEARISH", int(min(100, hi_line[2] * 100)), None, None, None,
            now, lows[-1]["confirmed_at"].to_pydatetime() if lows else now,
            "Confirmed falling trendline through recent swing highs.", metadata={"slope": hi_line[0], "r2": hi_line[2]},
        ))

    # Triangles from converging confirmed trendlines.
    if hi_line and lo_line and hi_line[2] >= 0.45 and lo_line[2] >= 0.45:
        flat_tol = atr * 0.015
        typ = direction = None
        if hi_line[0] < -flat_tol and lo_line[0] > flat_tol:
            typ, direction = "SYMMETRICAL_TRIANGLE", "NEUTRAL"
        elif abs(hi_line[0]) <= flat_tol and lo_line[0] > flat_tol:
            typ, direction = "ASCENDING_TRIANGLE", "BULLISH"
        elif hi_line[0] < -flat_tol and abs(lo_line[0]) <= flat_tol:
            typ, direction = "DESCENDING_TRIANGLE", "BEARISH"
        if typ:
            q = int(min(100, ((hi_line[2] + lo_line[2]) / 2) * 100))
            conf = max(highs[-1]["confirmed_at"], lows[-1]["confirmed_at"]).to_pydatetime()
            out.append(PatternDetection(
                typ, timeframe, direction, q, None, None, None, now, conf,
                "Converging confirmed swing trendlines; no breakout is implied until a closed candle confirms it.",
                metadata={"upper_slope": hi_line[0], "lower_slope": lo_line[0]},
            ))

    # Double top / bottom from last two confirmed swings.
    if len(highs) >= 2:
        a, b = highs[-2], highs[-1]
        if b["i"] - a["i"] >= 5 and abs(a["price"] - b["price"]) <= tol:
            q = int(max(50, 100 - 50 * abs(a["price"] - b["price"]) / tol))
            out.append(PatternDetection(
                "DOUBLE_TOP", timeframe, "BEARISH", min(100, q), Decimal(str((a["price"]+b["price"])/2)), None, None,
                now, b["confirmed_at"].to_pydatetime(), "Two separated confirmed swing highs within ATR tolerance.",
            ))
    if len(lows) >= 2:
        a, b = lows[-2], lows[-1]
        if b["i"] - a["i"] >= 5 and abs(a["price"] - b["price"]) <= tol:
            q = int(max(50, 100 - 50 * abs(a["price"] - b["price"]) / tol))
            out.append(PatternDetection(
                "DOUBLE_BOTTOM", timeframe, "BULLISH", min(100, q), Decimal(str((a["price"]+b["price"])/2)), None, None,
                now, b["confirmed_at"].to_pydatetime(), "Two separated confirmed swing lows within ATR tolerance.",
            ))

    # Structure regime + BOS/CHOCH. Break is close-confirmed, never wick-only.
    close = float(df["close"].iloc[-1])
    if len(highs) >= 2 and len(lows) >= 2:
        bullish_regime = highs[-1]["price"] > highs[-2]["price"] and lows[-1]["price"] > lows[-2]["price"]
        bearish_regime = highs[-1]["price"] < highs[-2]["price"] and lows[-1]["price"] < lows[-2]["price"]
        prior_high = highs[-1]["price"]
        prior_low = lows[-1]["price"]
        if close > prior_high:
            typ = "CHOCH" if bearish_regime else "BOS"
            out.append(PatternDetection(
                typ, timeframe, "BULLISH", 78 if typ == "BOS" else 84, Decimal(str(prior_high)), None, None,
                now, now, f"Closed candle confirmed above prior swing high {prior_high:.2f}.",
            ))
        elif close < prior_low:
            typ = "CHOCH" if bullish_regime else "BOS"
            out.append(PatternDetection(
                typ, timeframe, "BEARISH", 78 if typ == "BOS" else 84, Decimal(str(prior_low)), None, None,
                now, now, f"Closed candle confirmed below prior swing low {prior_low:.2f}.",
            ))

    # Closed-candle breakout and later retest of the latest strong clustered level.
    support_levels = [p for p in out if p.pattern_type == "SUPPORT" and p.level is not None]
    resistance_levels = [p for p in out if p.pattern_type == "RESISTANCE" and p.level is not None]
    prev_close = float(df["close"].iloc[-2])
    last_close = float(df["close"].iloc[-1])
    for rp in resistance_levels[:1]:
        lvl = float(rp.level)
        if prev_close <= lvl and last_close > lvl:
            out.append(PatternDetection(
                "BREAKOUT", timeframe, "BULLISH", 76, rp.level, None, None,
                now, now, "Closed candle confirmed above clustered resistance; wick-only penetration is insufficient.",
            ))
        # Search for an earlier confirmed breakout followed by a later retest.
        for j in range(max(1, len(df)-10), len(df)-1):
            if float(df["close"].iloc[j-1]) <= lvl and float(df["close"].iloc[j]) > lvl:
                for k in range(j+1, len(df)):
                    if float(df["low"].iloc[k]) <= lvl + tol and float(df["close"].iloc[k]) > lvl:
                        out.append(PatternDetection(
                            "BREAKOUT_RETEST", timeframe, "BULLISH", 84, rp.level, None, None,
                            now, df.index[k].to_pydatetime(), "Resistance breakout was followed by a later candle retesting the level and closing above it.",
                        ))
                        break
                break
    for sp in support_levels[:1]:
        lvl = float(sp.level)
        if prev_close >= lvl and last_close < lvl:
            out.append(PatternDetection(
                "BREAKOUT", timeframe, "BEARISH", 76, sp.level, None, None,
                now, now, "Closed candle confirmed below clustered support; wick-only penetration is insufficient.",
            ))
        for j in range(max(1, len(df)-10), len(df)-1):
            if float(df["close"].iloc[j-1]) >= lvl and float(df["close"].iloc[j]) < lvl:
                for k in range(j+1, len(df)):
                    if float(df["high"].iloc[k]) >= lvl - tol and float(df["close"].iloc[k]) < lvl:
                        out.append(PatternDetection(
                            "BREAKOUT_RETEST", timeframe, "BEARISH", 84, sp.level, None, None,
                            now, df.index[k].to_pydatetime(), "Support breakout was followed by a later candle retesting the level and closing below it.",
                        ))
                        break
                break

    # Wick sweep / false breakout against the latest confirmed levels.
    last = df.iloc[-1]
    if highs:
        lvl = highs[-1]["price"]
        if float(last["high"]) > lvl and float(last["close"]) < lvl:
            out.append(PatternDetection(
                "LIQUIDITY_SWEEP", timeframe, "BEARISH", 72, Decimal(str(lvl)), None, None,
                now, now, "Wick traded above prior confirmed swing high but closed back below it.",
            ))
            out.append(PatternDetection(
                "FALSE_BREAKOUT", timeframe, "BEARISH", 70, Decimal(str(lvl)), None, None,
                now, now, "Price penetrated resistance intrabar but failed to close above it.",
            ))
    if lows:
        lvl = lows[-1]["price"]
        if float(last["low"]) < lvl and float(last["close"]) > lvl:
            out.append(PatternDetection(
                "LIQUIDITY_SWEEP", timeframe, "BULLISH", 72, Decimal(str(lvl)), None, None,
                now, now, "Wick traded below prior confirmed swing low but closed back above it.",
            ))
            out.append(PatternDetection(
                "FALSE_BREAKOUT", timeframe, "BULLISH", 70, Decimal(str(lvl)), None, None,
                now, now, "Price penetrated support intrabar but failed to close below it.",
            ))

    # Reproducible base -> impulse supply/demand zones.
    body = (df["close"] - df["open"]).abs()
    rng = (df["high"] - df["low"]).replace(0, np.nan)
    for i in range(max(1, len(df)-25), len(df)-2):
        local_atr = float((df["high"]-df["low"]).rolling(14).mean().iloc[i])
        if not np.isfinite(local_atr) or local_atr <= 0:
            continue
        if float(body.iloc[i]) <= 0.5 * local_atr:
            next_move = float(df["close"].iloc[i+2] - df["close"].iloc[i])
            if next_move >= 1.5 * local_atr:
                out.append(PatternDetection(
                    "DEMAND_ZONE", timeframe, "BULLISH", 68, None,
                    Decimal(str(float(df["low"].iloc[i]))), Decimal(str(float(df["high"].iloc[i]))),
                    now, df.index[i+2].to_pydatetime(), "Small base candle followed by >=1.5 ATR upward impulse.",
                ))
            elif next_move <= -1.5 * local_atr:
                out.append(PatternDetection(
                    "SUPPLY_ZONE", timeframe, "BEARISH", 68, None,
                    Decimal(str(float(df["low"].iloc[i]))), Decimal(str(float(df["high"].iloc[i]))),
                    now, df.index[i+2].to_pydatetime(), "Small base candle followed by >=1.5 ATR downward impulse.",
                ))
    # Keep latest of repeated zone types and cap output.
    dedup = {}
    for p in out:
        dedup[(p.pattern_type, p.direction)] = p
    return list(dedup.values())[-14:]


def pattern_group_evidence(patterns: list[PatternDetection]) -> tuple[float, list[str], list[str]]:
    if not patterns:
        return 0.0, [], []
    pos = neg = 0.0
    reasons_for, reasons_against = [], []
    for p in patterns:
        strength = min(1.0, max(0.0, p.quality_score / 100.0))
        # Correlation cap is applied by retaining only the strongest evidence per family/direction.
        if p.direction == "BULLISH":
            pos = max(pos, strength)
            reasons_for.append(f"{p.timeframe} {p.pattern_type}: {p.explanation}")
        elif p.direction == "BEARISH":
            neg = max(neg, strength)
            reasons_against.append(f"{p.timeframe} {p.pattern_type}: {p.explanation}")
    return float(np.clip(pos - neg, -1, 1)), reasons_for[:6], reasons_against[:6]
# ===== END engines/pattern_engine.py =====



# ===== BEGIN engines/strategy_research_engine_v6.py =====
import math
import io
from itertools import product

try:
    from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    SKLEARN_OK = True
except Exception:
    SKLEARN_OK = False

@dataclass(frozen=True)
class CostModel:
    spread_usd_per_oz: float = 0.3
    slippage_each_side_usd_per_oz: float = 0.05

    @property
    def half_spread(self) -> float:
        return self.spread_usd_per_oz / 2.0

def ensure_utc_datetime_index(df: pd.DataFrame) -> pd.DataFrame:
    """Return a sorted copy with a UTC DatetimeIndex named 'datetime'."""
    out = df.copy()
    if not isinstance(out.index, pd.DatetimeIndex):
        raise ValueError('DataFrame index must be a DatetimeIndex.')
    if out.index.tz is None:
        out.index = out.index.tz_localize('UTC')
    else:
        out.index = out.index.tz_convert('UTC')
    out.index.name = 'datetime'
    return out.sort_index()

def ema(s, n):
    return s.ewm(span=n, adjust=False).mean()

def rsi(s, n=14):
    d = s.diff()
    up = d.clip(lower=0)
    dn = -d.clip(upper=0)
    au = up.ewm(alpha=1 / n, adjust=False).mean()
    ad = dn.ewm(alpha=1 / n, adjust=False).mean()
    rs = au / ad.replace(0, np.nan)
    result = 100 - 100 / (1 + rs)
    result = result.mask((ad == 0) & (au > 0), 100.)
    return result.mask((ad == 0) & (au == 0), 50.)

def atr(df, n=14):
    pc = df['close'].shift(1)
    tr = pd.concat([df['high'] - df['low'], (df['high'] - pc).abs(), (df['low'] - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()

def adx(df, n=14):
    up = df['high'].diff()
    dn = -df['low'].diff()
    plus_dm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=df.index)
    a = atr(df, n)
    plus_di = 100 * plus_dm.ewm(alpha=1 / n, adjust=False).mean() / a.replace(0, np.nan)
    minus_di = 100 * minus_dm.ewm(alpha=1 / n, adjust=False).mean() / a.replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return (dx.ewm(alpha=1 / n, adjust=False).mean(), plus_di, minus_di)

def stochastic(df, n=14):
    lo = df['low'].rolling(n).min()
    hi = df['high'].rolling(n).max()
    return 100 * (df['close'] - lo) / (hi - lo).replace(0, np.nan)

def add_features(df: pd.DataFrame) -> pd.DataFrame:
    x = ensure_utc_datetime_index(df)
    c = x['close']
    for n in [9, 20, 50, 100, 200]:
        x[f'ema{n}'] = ema(c, n)
    x['rsi14'] = rsi(c, 14)
    x['atr14'] = atr(x, 14)
    x['atr_pct'] = 100 * x['atr14'] / c
    x['roc10'] = 100 * (c / c.shift(10) - 1)
    x['macd'] = ema(c, 12) - ema(c, 26)
    x['macd_signal'] = ema(x['macd'], 9)
    x['macd_hist'] = x['macd'] - x['macd_signal']
    mid = c.rolling(20).mean()
    sd = c.rolling(20).std()
    x['bb_mid'] = mid
    x['bb_up'] = mid + 2 * sd
    x['bb_dn'] = mid - 2 * sd
    x['bb_width'] = (x['bb_up'] - x['bb_dn']) / mid
    x['don20_hi'] = x['high'].shift(1).rolling(20).max()
    x['don20_lo'] = x['low'].shift(1).rolling(20).min()
    x['don40_hi'] = x['high'].shift(1).rolling(40).max()
    x['don40_lo'] = x['low'].shift(1).rolling(40).min()
    x['adx14'], x['plus_di'], x['minus_di'] = adx(x, 14)
    x['stoch14'] = stochastic(x, 14)
    body = (x['close'] - x['open']).abs()
    rng = (x['high'] - x['low']).replace(0, np.nan)
    x['body_pct'] = body / rng
    x['upper_wick'] = (x['high'] - x[['open', 'close']].max(axis=1)) / rng
    x['lower_wick'] = (x[['open', 'close']].min(axis=1) - x['low']) / rng
    po = x['open'].shift(1)
    pc = x['close'].shift(1)
    x['bull_engulf'] = (x['close'] > x['open']) & (pc < po) & (x['open'] <= pc) & (x['close'] >= po)
    x['bear_engulf'] = (x['close'] < x['open']) & (pc > po) & (x['open'] >= pc) & (x['close'] <= po)
    x['bull_pin'] = (x['lower_wick'] > 0.55) & (x['body_pct'] < 0.35)
    x['bear_pin'] = (x['upper_wick'] > 0.55) & (x['body_pct'] < 0.35)
    for n in [5, 10, 20]:
        prev_hi = x['high'].shift(1).rolling(n).max()
        prev_lo = x['low'].shift(1).rolling(n).min()
        x[f'bos_up_{n}'] = x['close'] > prev_hi
        x[f'bos_dn_{n}'] = x['close'] < prev_lo
        x[f'sweep_low_{n}'] = (x['low'] < prev_lo) & (x['close'] > prev_lo)
        x[f'sweep_high_{n}'] = (x['high'] > prev_hi) & (x['close'] < prev_hi)
    ma50 = c.rolling(50).mean()
    sd50 = c.rolling(50).std()
    x['z50'] = (c - ma50) / sd50.replace(0, np.nan)
    x['vol20'] = c.pct_change().rolling(20).std() * np.sqrt(20)
    x['trend_strength'] = (x['ema20'] - x['ema100']).abs() / x['atr14'].replace(0, np.nan)
    x['hour_utc'] = x.index.hour
    x['london'] = x['hour_utc'].between(7, 15)
    x['new_york'] = x['hour_utc'].between(12, 20)
    x['overlap'] = x['hour_utc'].between(12, 15)
    for n in [1, 2, 4, 8, 16, 32]:
        x[f'ret_{n}'] = c.pct_change(n)
    return x

def add_h1_context(primary: pd.DataFrame, h1: pd.DataFrame) -> pd.DataFrame:
    """
    Merge ONLY fully closed H1 candles into the primary timeframe.

    Twelve Data timestamps intraday bars at BAR OPEN time.
    Therefore a 17:00 H1 candle's final OHLC/indicators are not available
    until 18:00. We shift H1 availability by +1 hour before merge_asof
    to prevent look-ahead leakage into 15m bars inside the same hour.
    """
    p0 = ensure_utc_datetime_index(primary)
    h0 = ensure_utc_datetime_index(h1)
    h = add_features(h0)
    cols = ['close', 'ema20', 'ema50', 'ema100', 'ema200', 'rsi14', 'adx14', 'atr_pct', 'roc10']
    h = h[cols].copy()
    h.columns = [f'h1_{c}' for c in cols]

    hh = h.reset_index()
    hh["available_at"] = hh["datetime"] + pd.Timedelta(hours=1)
    hh = hh.drop(columns=["datetime"]).rename(columns={"available_at": "datetime"})

    p = p0.reset_index()
    out = pd.merge_asof(
        p.sort_values('datetime'),
        hh.sort_values('datetime'),
        on='datetime',
        direction='backward'
    ).set_index('datetime')
    out.index.name = 'datetime'
    return out

def _sig(index, long_cond, short_cond):
    s = pd.Series(0, index=index, dtype=int)
    s[long_cond.fillna(False)] = 1
    s[short_cond.fillna(False)] = -1
    both = long_cond.fillna(False) & short_cond.fillna(False)
    s[both] = 0
    return s


def resample_ohlc_strict(df: pd.DataFrame, rule: str, expected_count: int) -> pd.DataFrame:
    """
    Aggregate already-closed lower-timeframe bars and keep only complete groups.
    Timestamps remain BAR OPEN times.
    """
    z = ensure_utc_datetime_index(df)[["open","high","low","close"]].copy()
    agg = z.resample(rule, label="left", closed="left").agg(
        {"open":"first","high":"max","low":"min","close":"last"}
    )
    counts = z["close"].resample(rule, label="left", closed="left").count()
    agg = agg[counts >= int(expected_count)].dropna()
    return agg


def add_context_features(primary: pd.DataFrame, context: pd.DataFrame, context_minutes: int) -> pd.DataFrame:
    """
    Attach only fully CLOSED higher-timeframe context.
    Context output columns keep the historical h1_* names for strategy compatibility,
    even when the 1h primary uses a 4h context.
    """
    p0 = ensure_utc_datetime_index(primary)
    c0 = ensure_utc_datetime_index(context)
    h = add_features(c0)
    cols = ["close","ema20","ema50","ema100","ema200","rsi14","adx14","atr_pct","roc10"]
    h = h[cols].copy()
    h.columns = [f"h1_{c}" for c in cols]

    hh = h.reset_index()
    hh["available_at"] = hh["datetime"] + pd.Timedelta(minutes=int(context_minutes))
    hh = hh.drop(columns=["datetime"]).rename(columns={"available_at":"datetime"})
    p = p0.reset_index()
    out = pd.merge_asof(
        p.sort_values("datetime"),
        hh.sort_values("datetime"),
        on="datetime",
        direction="backward",
    ).set_index("datetime")
    out.index.name = "datetime"
    return out

def strat_ema_pullback(x, p):
    trend_l = (x[f"ema{p['fast']}"] > x[f"ema{p['slow']}"]) & (x['adx14'] >= p['adx'])
    trend_s = (x[f"ema{p['fast']}"] < x[f"ema{p['slow']}"]) & (x['adx14'] >= p['adx'])
    long_c = trend_l & (x['low'] <= x[f"ema{p['fast']}"]) & (x['close'] > x[f"ema{p['fast']}"]) & (x['rsi14'] >= p['rsi_l'])
    short_c = trend_s & (x['high'] >= x[f"ema{p['fast']}"]) & (x['close'] < x[f"ema{p['fast']}"]) & (x['rsi14'] <= p['rsi_s'])
    return _sig(x.index, long_c, short_c)

def strat_donchian(x, p):
    hi = x['high'].shift(1).rolling(p['n']).max()
    lo = x['low'].shift(1).rolling(p['n']).min()
    long_c = (x['close'] > hi) & (x['adx14'] >= p['adx'])
    short_c = (x['close'] < lo) & (x['adx14'] >= p['adx'])
    return _sig(x.index, long_c, short_c)

def strat_bb_reversion(x, p):
    mid = x['close'].rolling(p['n']).mean()
    sd = x['close'].rolling(p['n']).std()
    up = mid + p['std'] * sd
    dn = mid - p['std'] * sd
    long_c = (x['close'] < dn) & (x['rsi14'] <= p['rsi_lo']) & (x['adx14'] <= p['adx_max'])
    short_c = (x['close'] > up) & (x['rsi14'] >= p['rsi_hi']) & (x['adx14'] <= p['adx_max'])
    return _sig(x.index, long_c, short_c)

def strat_macd_trend(x, p):
    long_c = (x['macd_hist'] > 0) & (x['macd_hist'].shift(1) <= 0) & (x['close'] > x[f"ema{p['ema']}"]) & (x['adx14'] >= p['adx'])
    short_c = (x['macd_hist'] < 0) & (x['macd_hist'].shift(1) >= 0) & (x['close'] < x[f"ema{p['ema']}"]) & (x['adx14'] >= p['adx'])
    return _sig(x.index, long_c, short_c)

def strat_liquidity_sweep(x, p):
    long_c = x[f"sweep_low_{p['n']}"] & (x['lower_wick'] >= p['wick']) & (x['rsi14'] < p['rsi_lo'])
    short_c = x[f"sweep_high_{p['n']}"] & (x['upper_wick'] >= p['wick']) & (x['rsi14'] > p['rsi_hi'])
    return _sig(x.index, long_c, short_c)

def strat_bos(x, p):
    long_c = x[f"bos_up_{p['n']}"] & (x['close'] > x['ema100']) & (x['adx14'] >= p['adx'])
    short_c = x[f"bos_dn_{p['n']}"] & (x['close'] < x['ema100']) & (x['adx14'] >= p['adx'])
    return _sig(x.index, long_c, short_c)

def strat_candle_trend(x, p):
    long_pat = x['bull_engulf'] | x['bull_pin']
    short_pat = x['bear_engulf'] | x['bear_pin']
    long_c = long_pat & (x['ema20'] > x['ema100']) & (x['rsi14'] >= p['rsi_l'])
    short_c = short_pat & (x['ema20'] < x['ema100']) & (x['rsi14'] <= p['rsi_s'])
    return _sig(x.index, long_c, short_c)

def strat_mtf(x, p):
    long_c = (x['ema20'] > x['ema100']) & (x['h1_ema20'] > x['h1_ema100']) & (x['close'] > x['don20_hi']) & (x['h1_rsi14'] >= p['h1_rsi'])
    short_c = (x['ema20'] < x['ema100']) & (x['h1_ema20'] < x['h1_ema100']) & (x['close'] < x['don20_lo']) & (x['h1_rsi14'] <= 100 - p['h1_rsi'])
    return _sig(x.index, long_c, short_c)

def strat_session_breakout(x, p):
    hi = x['high'].shift(1).rolling(p['n']).max()
    lo = x['low'].shift(1).rolling(p['n']).min()
    session = x[p['session']].fillna(False)
    long_c = session & (x['close'] > hi) & (x['close'] > x['ema100'])
    short_c = session & (x['close'] < lo) & (x['close'] < x['ema100'])
    return _sig(x.index, long_c, short_c)

def strat_regime_ensemble(x, p):
    trend = x['adx14'] >= p['adx_trend']
    range_ = ~trend
    trend_long = (x['ema20'] > x['ema100']) & (x['macd_hist'] > 0) & (x['close'] > x['don20_hi'])
    trend_short = (x['ema20'] < x['ema100']) & (x['macd_hist'] < 0) & (x['close'] < x['don20_lo'])
    range_long = (x['z50'] <= -p['z']) & (x['rsi14'] <= p['rsi_lo'])
    range_short = (x['z50'] >= p['z']) & (x['rsi14'] >= p['rsi_hi'])
    return _sig(x.index, trend & trend_long | range_ & range_long, trend & trend_short | range_ & range_short)

def param_grid(intensity: str):
    if intensity == 'Quick':
        return {'EMA Pullback': [dict(fast=20, slow=100, adx=20, rsi_l=45, rsi_s=55, sl=1.5, rr=2.0), dict(fast=20, slow=50, adx=25, rsi_l=50, rsi_s=50, sl=2.0, rr=2.0)], 'Donchian Breakout': [dict(n=20, adx=20, sl=1.5, rr=2.0), dict(n=40, adx=25, sl=2.0, rr=2.5)], 'Bollinger Mean Reversion': [dict(n=20, std=2.0, rsi_lo=30, rsi_hi=70, adx_max=25, sl=1.5, rr=1.5), dict(n=20, std=2.5, rsi_lo=25, rsi_hi=75, adx_max=22, sl=2.0, rr=1.5)], 'MACD Trend': [dict(ema=100, adx=20, sl=1.5, rr=2.0), dict(ema=200, adx=25, sl=2.0, rr=2.5)], 'Liquidity Sweep': [dict(n=10, wick=0.5, rsi_lo=45, rsi_hi=55, sl=1.2, rr=1.8), dict(n=20, wick=0.55, rsi_lo=40, rsi_hi=60, sl=1.5, rr=2.0)], 'BOS / Structure Break': [dict(n=10, adx=20, sl=1.5, rr=2.0), dict(n=20, adx=25, sl=2.0, rr=2.5)], 'Candlestick + Trend': [dict(rsi_l=45, rsi_s=55, sl=1.5, rr=2.0), dict(rsi_l=50, rsi_s=50, sl=2.0, rr=2.0)], 'Multi-Timeframe Breakout': [dict(h1_rsi=52, sl=1.5, rr=2.0), dict(h1_rsi=55, sl=2.0, rr=2.5)], 'Session Breakout': [dict(n=12, session='london', sl=1.5, rr=2.0), dict(n=16, session='new_york', sl=2.0, rr=2.0)], 'Regime Ensemble': [dict(adx_trend=23, z=1.6, rsi_lo=30, rsi_hi=70, sl=1.5, rr=2.0), dict(adx_trend=27, z=2.0, rsi_lo=25, rsi_hi=75, sl=2.0, rr=2.0)]}
    grids = {}
    grids['EMA Pullback'] = [dict(fast=f, slow=s, adx=a, rsi_l=rl, rsi_s=100 - rl, sl=sl, rr=rr) for f, s, a, rl, sl, rr in product([20, 50], [100, 200], [18, 25], [45, 50], [1.5, 2.0], [1.5, 2.0, 2.5]) if f < s]
    grids['Donchian Breakout'] = [dict(n=n, adx=a, sl=sl, rr=rr) for n, a, sl, rr in product([20, 40, 60], [18, 25], [1.5, 2.0], [1.5, 2.0, 2.5])]
    grids['Bollinger Mean Reversion'] = [dict(n=n, std=sd, rsi_lo=lo, rsi_hi=100 - lo, adx_max=ax, sl=sl, rr=rr) for n, sd, lo, ax, sl, rr in product([20, 30], [2.0, 2.5], [25, 30], [22, 28], [1.5, 2.0], [1.0, 1.5, 2.0])]
    grids['MACD Trend'] = [dict(ema=e, adx=a, sl=sl, rr=rr) for e, a, sl, rr in product([100, 200], [18, 25], [1.5, 2.0], [1.5, 2.0, 2.5])]
    grids['Liquidity Sweep'] = [dict(n=n, wick=w, rsi_lo=lo, rsi_hi=100 - lo, sl=sl, rr=rr) for n, w, lo, sl, rr in product([10, 20], [0.5, 0.6], [35, 45], [1.2, 1.6], [1.5, 2.0, 2.5])]
    grids['BOS / Structure Break'] = [dict(n=n, adx=a, sl=sl, rr=rr) for n, a, sl, rr in product([5, 10, 20], [18, 25], [1.5, 2.0], [1.5, 2.0, 2.5])]
    grids['Candlestick + Trend'] = [dict(rsi_l=rl, rsi_s=100 - rl, sl=sl, rr=rr) for rl, sl, rr in product([45, 50], [1.2, 1.6, 2.0], [1.5, 2.0, 2.5])]
    grids['Multi-Timeframe Breakout'] = [dict(h1_rsi=r, sl=sl, rr=rr) for r, sl, rr in product([50, 55, 60], [1.5, 2.0], [1.5, 2.0, 2.5])]
    grids['Session Breakout'] = [dict(n=n, session=s, sl=sl, rr=rr) for n, s, sl, rr in product([8, 12, 20], ['london', 'new_york', 'overlap'], [1.5, 2.0], [1.5, 2.0, 2.5])]
    grids['Regime Ensemble'] = [dict(adx_trend=a, z=z, rsi_lo=lo, rsi_hi=100 - lo, sl=sl, rr=rr) for a, z, lo, sl, rr in product([20, 25, 30], [1.5, 2.0], [25, 30], [1.5, 2.0], [1.5, 2.0, 2.5])]
    return grids

def prepare_ml(train, test, horizon_bars=8, threshold=0.0015):
    cols = [c for c in ML_FEATURES if c in train.columns]
    cols = [c for c in cols if train[c].notna().sum() > max(50, len(train) * 0.2)]
    tr = train.copy()
    te = test.copy()
    future = tr['close'].shift(-horizon_bars) / tr['close'] - 1
    y = pd.Series(np.where(future > threshold, 1, np.where(future < -threshold, 0, np.nan)), index=tr.index)
    mask = tr[cols].notna().all(axis=1) & y.notna()
    Xtr = tr.loc[mask, cols]
    ytr = y.loc[mask].astype(int)
    Xte = te[cols].replace([np.inf, -np.inf], np.nan).ffill()
    return (Xtr, ytr, Xte, cols)


def strat_deep_consensus(x, p):
    members = p.get("members", [])
    vote = int(p.get("vote", 2))
    if not members:
        return pd.Series(0, index=x.index, dtype=int)
    total = pd.Series(0, index=x.index, dtype=int)
    for item in members:
        family = item.get("family")
        params = item.get("params", {})
        fn = STRATEGIES.get(family)
        if fn is None or family == "Deep Consensus":
            continue
        total = total.add(fn(x, params).reindex(x.index).fillna(0).astype(int), fill_value=0).astype(int)
    out = pd.Series(0, index=x.index, dtype=int)
    out[total >= vote] = 1
    out[total <= -vote] = -1
    return out

STRATEGIES = {
    "EMA Pullback": strat_ema_pullback,
    "Donchian Breakout": strat_donchian,
    "Bollinger Mean Reversion": strat_bb_reversion,
    "MACD Trend": strat_macd_trend,
    "Liquidity Sweep": strat_liquidity_sweep,
    "BOS / Structure Break": strat_bos,
    "Candlestick + Trend": strat_candle_trend,
    "Multi-Timeframe Breakout": strat_mtf,
    "Session Breakout": strat_session_breakout,
    "Regime Ensemble": strat_regime_ensemble,
    "Deep Consensus": strat_deep_consensus,
}

ML_FEATURES = [
    "rsi14", "atr_pct", "roc10", "macd_hist", "bb_width", "adx14",
    "plus_di", "minus_di", "stoch14", "z50", "vol20", "trend_strength",
    "body_pct", "upper_wick", "lower_wick",
    "ret_1", "ret_2", "ret_4", "ret_8", "ret_16", "ret_32",
    "h1_rsi14", "h1_adx14", "h1_atr_pct", "h1_roc10",
    "us10y_chg5", "real10y_chg5", "usd_broad_chg5",
]


def _fred_series(series_id: str, start_date: str, end_date: str) -> pd.Series:
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv"
    r = requests.get(url, params={"id": series_id, "cosd": start_date, "coed": end_date}, timeout=20)
    r.raise_for_status()
    d = pd.read_csv(io.StringIO(r.text))
    if d.empty or "DATE" not in d.columns or series_id not in d.columns:
        raise RuntimeError(f"FRED {series_id} unavailable")
    d["DATE"] = pd.to_datetime(d["DATE"], utc=True)
    s = pd.to_numeric(d[series_id].replace(".", np.nan), errors="coerce")
    s.index = d["DATE"]
    s.index.name = "datetime"
    return s.sort_index()


def attach_macro_features_v6(df: pd.DataFrame):
    out = ensure_utc_datetime_index(df)
    notes = []
    start = (out.index.min() - pd.Timedelta(days=10)).strftime("%Y-%m-%d")
    end = out.index.max().strftime("%Y-%m-%d")
    mapping = {"DGS10": "us10y", "DFII10": "real10y", "DTWEXBGS": "usd_broad"}
    for sid, col in mapping.items():
        try:
            s = _fred_series(sid, start, end)
            daily = s.to_frame(col).reset_index()
            # Conservative release availability: do not expose a daily final observation
            # to intraday bars until the next UTC day.
            daily["datetime"] = daily["datetime"] + pd.Timedelta(days=1)
            left = out.reset_index().sort_values("datetime")
            right = daily.sort_values("datetime")
            merged = pd.merge_asof(left, right, on="datetime", direction="backward").set_index("datetime")
            out[col] = merged[col]
            out[f"{col}_chg5"] = out[col].diff(5)
            notes.append(f"{col}: loaded")
        except Exception as exc:
            out[col] = np.nan
            out[f"{col}_chg5"] = np.nan
            notes.append(f"{col}: unavailable ({type(exc).__name__})")
    return out, notes


def research_target_multipliers(rr: float):
    base = float(rr)
    return (0.40*base, 0.70*base, 1.00*base, 1.30*base, 1.70*base)


def _adverse_exit_fill(raw_price: float, side: int, cost: CostModel) -> float:
    # side=1 means closing a long by selling; side=-1 means closing a short by buying.
    if side == 1:
        return raw_price - cost.half_spread - cost.slippage_each_side_usd_per_oz
    return raw_price + cost.half_spread + cost.slippage_each_side_usd_per_oz


def backtest_v5_lifecycle(
    x: pd.DataFrame,
    signal: pd.Series,
    sl_atr: float,
    rr: float,
    cost: CostModel,
    max_hold_bars: int = 96,
):
    """
    1x-notional research backtest using the V6 / project position-management rules:
      TP1 -> SL to TP1 next bar
      TP2 -> hold
      TP3 -> close 50% of original
      TP4 -> SL on remainder to TP3 next bar
      TP5 -> close remainder
    Entry is next-bar open. Stop is checked before targets inside each bar.
    Research sizing is 1x notional, so reported return does not use leverage.
    """
    x = ensure_utc_datetime_index(x)
    sig = signal.reindex(x.index).fillna(0).astype(int)
    equity = 1.0
    curve = pd.Series(np.nan, index=x.index, dtype=float)
    curve.iloc[0] = equity
    trades = []
    i = 0
    n = len(x)
    total_bars_in_market = 0
    while i < n - 2:
        curve.iloc[i] = equity
        side = int(sig.iloc[i])
        atrv = float(x["atr14"].iloc[i]) if np.isfinite(x["atr14"].iloc[i]) else np.nan
        if side == 0 or not np.isfinite(atrv) or atrv <= 0:
            i += 1
            continue

        stop_multiple = float(sl_atr.iloc[i]) if isinstance(sl_atr, pd.Series) else float(sl_atr)
        reward_multiple = float(rr.iloc[i]) if isinstance(rr, pd.Series) else float(rr)
        mults = research_target_multipliers(reward_multiple)
        entry_i = i + 1
        raw_open = float(x["open"].iloc[entry_i])
        if side == 1:
            entry = raw_open + cost.half_spread + cost.slippage_each_side_usd_per_oz
            stop = entry - stop_multiple * atrv
        else:
            entry = raw_open - cost.half_spread - cost.slippage_each_side_usd_per_oz
            stop = entry + stop_multiple * atrv

        R = abs(entry - stop)
        if R <= 0:
            i += 1
            continue
        targets = [entry + side * R * m for m in mults]

        equity_before = equity
        original_units = equity_before / entry  # exactly 1x notional
        remaining = original_units
        realized = 0.0
        tp_hit = [False]*5
        pending_sl = None
        pending_effective_i = None
        exit_i = None
        exit_reason = None
        last_j = min(n - 1, entry_i + max_hold_bars)
        total_bars_in_market += max(1, last_j-entry_i+1)

        for j in range(entry_i, last_j+1):
            o = float(x["open"].iloc[j])
            h = float(x["high"].iloc[j])
            l = float(x["low"].iloc[j])
            c = float(x["close"].iloc[j])

            if pending_sl is not None and pending_effective_i is not None and j >= pending_effective_i:
                if (side == 1 and pending_sl > stop) or (side == -1 and pending_sl < stop):
                    stop = pending_sl
                pending_sl = None
                pending_effective_i = None

            stop_touched = l <= stop if side == 1 else h >= stop
            if stop_touched:
                worse_gap = (side == 1 and o < stop) or (side == -1 and o > stop)
                raw_exit = o if worse_gap else stop
                fill = _adverse_exit_fill(raw_exit, side, cost)
                realized += (fill - entry) * side * remaining
                remaining = 0.0
                equity = equity_before + realized
                curve.iloc[j] = equity
                exit_i = j
                exit_reason = "STOP"
                break

            for k, target in enumerate(targets):
                if tp_hit[k]:
                    continue
                touched = h >= target if side == 1 else l <= target
                if not touched:
                    continue
                tp_hit[k] = True

                if k == 0:
                    pending_sl = targets[0]
                    pending_effective_i = j + 1
                elif k == 1:
                    pass
                elif k == 2:
                    qty = min(original_units * 0.5, remaining)
                    fill = _adverse_exit_fill(targets[2], side, cost)
                    realized += (fill - entry) * side * qty
                    remaining -= qty
                elif k == 3:
                    pending_sl = targets[2]
                    pending_effective_i = j + 1
                elif k == 4:
                    qty = remaining
                    fill = _adverse_exit_fill(targets[4], side, cost)
                    realized += (fill - entry) * side * qty
                    remaining = 0.0
                    equity = equity_before + realized
                    curve.iloc[j] = equity
                    exit_i = j
                    exit_reason = "TP5"
                    break

            if exit_i is not None:
                break

            mark = _adverse_exit_fill(c, side, cost)
            mtm = equity_before + realized + (mark - entry) * side * remaining
            curve.iloc[j] = mtm

        if exit_i is None:
            exit_i = last_j
            raw_exit = float(x["close"].iloc[exit_i])
            fill = _adverse_exit_fill(raw_exit, side, cost)
            realized += (fill - entry) * side * remaining
            remaining = 0.0
            equity = equity_before + realized
            curve.iloc[exit_i] = equity
            exit_reason = "TIME"

        trade_ret = (equity - equity_before) / equity_before
        trades.append({
            "side": side,
            "entry_time": x.index[entry_i],
            "exit_time": x.index[exit_i],
            "entry": entry,
            "initial_stop": entry - side*R,
            "tp1": targets[0], "tp2": targets[1], "tp3": targets[2], "tp4": targets[3], "tp5": targets[4],
            "reason": exit_reason,
            "ret": trade_ret,
            "bars": int(exit_i-entry_i+1),
            "equity_after": equity,
        })

        i = exit_i + 1

    curve = curve.ffill().fillna(1.0)
    tdf = pd.DataFrame(trades)
    dd = curve / curve.cummax() - 1.0

    if tdf.empty:
        metrics = {
            "return_pct": 0.0, "max_dd_pct": float(dd.min()*100) if len(dd) else 0.0,
            "sharpe": 0.0, "profit_factor": 0.0, "win_rate": 0.0, "trades": 0,
            "long_return_pct": 0.0, "short_return_pct": 0.0,
            "long_trades": 0, "short_trades": 0,
            "avg_trade_pct": 0.0, "exposure_pct": 0.0,
        }
        return tdf, metrics, curve

    rets = tdf["ret"].astype(float)
    wins = rets[rets > 0].sum()
    losses = -rets[rets < 0].sum()
    pf = float(wins/losses) if losses > 0 else (99.0 if wins > 0 else 0.0)

    def side_compound(side_value):
        r = tdf.loc[tdf["side"] == side_value, "ret"].astype(float)
        return (float(np.prod(1+r))-1)*100 if len(r) else 0.0

    sharpe = 0.0
    if len(rets) > 1 and rets.std(ddof=1) > 0:
        sharpe = float(rets.mean()/rets.std(ddof=1)*math.sqrt(len(rets)))

    metrics = {
        "return_pct": (equity-1.0)*100,
        "max_dd_pct": float(dd.min()*100),
        "sharpe": sharpe,
        "profit_factor": pf,
        "win_rate": float((rets > 0).mean()*100),
        "trades": int(len(tdf)),
        "long_return_pct": side_compound(1),
        "short_return_pct": side_compound(-1),
        "long_trades": int((tdf["side"] == 1).sum()),
        "short_trades": int((tdf["side"] == -1).sum()),
        "avg_trade_pct": float(rets.mean()*100),
        "exposure_pct": min(100.0, 100.0*total_bars_in_market/max(1, len(x))),
    }
    return tdf, metrics, curve


def research_train_score(m):
    balance_penalty = (8.0 if m["long_return_pct"] <= 0 else 0.0) + (8.0 if m["short_return_pct"] <= 0 else 0.0)
    trade_penalty = max(0, 12-int(m["trades"])) * 0.5
    return (
        float(m["return_pct"])
        + 3.0*min(float(m["profit_factor"]), 3.0)
        + 1.5*float(m["sharpe"])
        + 0.5*float(m["max_dd_pct"])
        - balance_penalty - trade_penalty
    )


def run_rule_research_v6(train, test, cost, intensity="Quick"):
    grids = param_grid(intensity)
    rows = []
    details = {}

    # Inner time-ordered validation inside the pre-OOS training window.
    split = max(300, int(len(train) * 0.67))
    split = min(split, max(300, len(train) - 300))
    fit = train.iloc[:split].copy()
    val = train.iloc[split:].copy()

    for name, configs in grids.items():
        scored = []
        for p in configs:
            fit_sig = STRATEGIES[name](fit, p)
            _, fit_m, _ = backtest_v5_lifecycle(fit, fit_sig, p["sl"], p["rr"], cost)

            val_sig = STRATEGIES[name](val, p)
            _, val_m, _ = backtest_v5_lifecycle(val, val_sig, p["sl"], p["rr"], cost)

            stability_penalty = 0.10 * abs(float(fit_m["return_pct"]) - float(val_m["return_pct"]))
            selection_score = research_train_score(val_m) + 0.25 * research_train_score(fit_m) - stability_penalty
            scored.append((selection_score, p, fit_m, val_m))

        scored.sort(key=lambda z: z[0], reverse=True)
        score, best_p, fit_m, val_m = scored[0]

        full_sig = STRATEGIES[name](train, best_p)
        _, full_train_m, _ = backtest_v5_lifecycle(train, full_sig, best_p["sl"], best_p["rr"], cost)

        test_sig = STRATEGIES[name](test, best_p)
        test_trades, test_m, test_curve = backtest_v5_lifecycle(
            test, test_sig, best_p["sl"], best_p["rr"], cost
        )

        rows.append({
            "family": name,
            "model": "RULE",
            "train_score": score,
            "selection_validation_return_pct": float(val_m["return_pct"]),
            "selection_validation_pf": float(val_m["profit_factor"]),
            "selection_validation_dd_pct": float(val_m["max_dd_pct"]),
            **{f"train_{k}": v for k,v in full_train_m.items()},
            **{f"oos_{k}": v for k,v in test_m.items()},
            "params": json.dumps(best_p, sort_keys=True),
        })
        details[name] = {
            "params": best_p,
            "trades": test_trades,
            "curve": test_curve,
            "metrics": test_m,
            "validation_metrics": val_m,
        }
    return pd.DataFrame(rows), details
def _predict_proba_no_lookahead(model, frame: pd.DataFrame, cols: list[str]) -> np.ndarray:
    """
    Predict only rows whose features are genuinely available on that row.
    Missing values produce neutral probability 0.5.
    No bfill is allowed because bfill would import future observations.
    """
    z = frame[cols].replace([np.inf, -np.inf], np.nan)
    valid = z.notna().all(axis=1)
    probs = np.full(len(z), 0.5, dtype=float)
    if valid.any():
        probs[valid.to_numpy()] = model.predict_proba(z.loc[valid])[:, 1]
    return probs


def run_ml_research_v6(train, test, cost):
    if not SKLEARN_OK:
        return pd.DataFrame(), {}

    def make_models():
        return {
            "Logistic Regression": Pipeline([
                ("scale", StandardScaler()),
                ("model", LogisticRegression(max_iter=1000, class_weight="balanced", random_state=7)),
            ]),
            "Random Forest": RandomForestClassifier(
                n_estimators=250, max_depth=6, min_samples_leaf=12,
                class_weight="balanced_subsample", random_state=7, n_jobs=-1,
            ),
            "Hist Gradient Boosting": HistGradientBoostingClassifier(
                max_iter=160, max_depth=4, learning_rate=0.05,
                min_samples_leaf=20, random_state=7,
            ),
        }

    split = max(300, int(len(train) * 0.67))
    split = min(split, max(300, len(train) - 300))
    fit = train.iloc[:split].copy()
    val = train.iloc[split:].copy()

    Xfit, yfit, Xval, cols_inner = prepare_ml(fit, val)
    if len(Xfit) < 300 or yfit.nunique() < 2 or len(Xval) < 100:
        return pd.DataFrame(), {}

    selected = {}
    for name, model in make_models().items():
        try:
            model.fit(Xfit, yfit)
            p_fit = _predict_proba_no_lookahead(model, fit, cols_inner)
            p_val = _predict_proba_no_lookahead(model, val, cols_inner)

            best = None
            for hi, sl, rr in product([0.56,0.60,0.64],[1.5,2.0],[1.5,2.0,2.5]):
                lo = 1-hi

                sig_fit = pd.Series(0, index=fit.index, dtype=int)
                sig_fit[np.asarray(p_fit) >= hi] = 1
                sig_fit[np.asarray(p_fit) <= lo] = -1
                _, fit_m, _ = backtest_v5_lifecycle(fit, sig_fit, sl, rr, cost, max_hold_bars=48)

                sig_val = pd.Series(0, index=val.index, dtype=int)
                sig_val[np.asarray(p_val) >= hi] = 1
                sig_val[np.asarray(p_val) <= lo] = -1
                _, val_m, _ = backtest_v5_lifecycle(val, sig_val, sl, rr, cost, max_hold_bars=48)

                stability_penalty = 0.10 * abs(float(fit_m["return_pct"]) - float(val_m["return_pct"]))
                sc = research_train_score(val_m) + 0.20*research_train_score(fit_m) - stability_penalty
                if best is None or sc > best[0]:
                    best = (sc, hi, sl, rr, fit_m, val_m)

            if best is not None:
                selected[name] = best
        except Exception:
            continue

    if not selected:
        return pd.DataFrame(), {}

    # Refit selected model family on the entire pre-OOS training window only,
    # then touch OOS exactly once.
    Xfull, yfull, Xtest, cols_full = prepare_ml(train, test)
    if len(Xfull) < 300 or yfull.nunique() < 2:
        return pd.DataFrame(), {}

    rows = []
    details = {}
    for name, (sc, hi, sl, rr, inner_fit_m, val_m) in selected.items():
        try:
            model = make_models()[name]
            model.fit(Xfull, yfull)

            p_train = _predict_proba_no_lookahead(model, train, cols_full)
            p_test = _predict_proba_no_lookahead(model, test, cols_full)
            lo = 1-hi

            sig_train = pd.Series(0, index=train.index, dtype=int)
            sig_train[np.asarray(p_train) >= hi] = 1
            sig_train[np.asarray(p_train) <= lo] = -1
            _, train_m, _ = backtest_v5_lifecycle(train, sig_train, sl, rr, cost, max_hold_bars=48)

            sig_test = pd.Series(0, index=test.index, dtype=int)
            sig_test[np.asarray(p_test) >= hi] = 1
            sig_test[np.asarray(p_test) <= lo] = -1
            trades, oos_m, curve = backtest_v5_lifecycle(test, sig_test, sl, rr, cost, max_hold_bars=48)

            params = {
                "prob_hi":hi, "prob_lo":lo, "sl":sl, "rr":rr,
                "features":len(cols_full),
            }
            rows.append({
                "family":name,
                "model":"ML",
                "train_score":sc,
                "selection_validation_return_pct":float(val_m["return_pct"]),
                "selection_validation_pf":float(val_m["profit_factor"]),
                "selection_validation_dd_pct":float(val_m["max_dd_pct"]),
                **{f"train_{k}":v for k,v in train_m.items()},
                **{f"oos_{k}":v for k,v in oos_m.items()},
                "params":json.dumps(params,sort_keys=True),
            })
            details[name] = {
                "params":params,
                "trades":trades,
                "curve":curve,
                "metrics":oos_m,
                "validation_metrics":val_m,
            }
        except Exception:
            continue

    return pd.DataFrame(rows), details
def research_target_gate(row, target=15.0, min_trades=12, max_dd=15.0):
    reasons = []
    if float(row["oos_return_pct"]) < float(target):
        reasons.append(f"OOS return < {target:.1f}%")
    if float(row["oos_long_return_pct"]) <= 0:
        reasons.append("BUY side not positive")
    if float(row["oos_short_return_pct"]) <= 0:
        reasons.append("SELL side not positive")
    if int(row.get("oos_long_trades", 0)) < 3:
        reasons.append("fewer than 3 BUY trades")
    if int(row.get("oos_short_trades", 0)) < 3:
        reasons.append("fewer than 3 SELL trades")
    if float(row["oos_max_dd_pct"]) < -abs(float(max_dd)):
        reasons.append(f"drawdown worse than -{max_dd:.1f}%")
    if int(row["oos_trades"]) < int(min_trades):
        reasons.append(f"fewer than {min_trades} OOS trades")
    if float(row["oos_profit_factor"]) < 1.20:
        reasons.append("profit factor < 1.20")
    return (len(reasons)==0, "; ".join(reasons) if reasons else "PASS")


def rank_research_results(results, target=15.0, min_trades=12, max_dd=15.0):
    if results is None or results.empty:
        return results
    out = results.copy()
    gates = out.apply(lambda r: research_target_gate(r,target,min_trades,max_dd),axis=1)
    out["target_pass"] = [g[0] for g in gates]
    out["gate_reason"] = [g[1] for g in gates]
    out["oos_rank_score"] = (
        out["oos_return_pct"]
        + 2.0*out["oos_sharpe"]
        + 2.0*out["oos_profit_factor"].clip(upper=3)
        + 0.6*out["oos_max_dd_pct"]
        - np.where(out["oos_long_return_pct"] <= 0, 6, 0)
        - np.where(out["oos_short_return_pct"] <= 0, 6, 0)
    )
    return out.sort_values(["target_pass","oos_rank_score"],ascending=[False,False]).reset_index(drop=True)



DEEP_PRIMARY_TFS = ("5m", "15m", "30m", "1h")
DEEP_INTERVALS = {"5m":"5min", "15m":"15min", "30m":"30min", "1h":"1h"}
DEEP_MINUTES = {"5m":5, "15m":15, "30m":30, "1h":60}


def build_deep_features(primary: pd.DataFrame, context: pd.DataFrame, context_minutes: int,
                        include_macro: bool = False):
    x = add_features(primary[["open","high","low","close"]].copy())
    x = add_context_features(x, context[["open","high","low","close"]].copy(), context_minutes)
    notes = []
    if include_macro:
        x, notes = attach_macro_features_v6(x)
    else:
        for col in ["us10y_chg5","real10y_chg5","usd_broad_chg5"]:
            x[col] = np.nan
    return x, notes


def _signal_only_params(configs):
    seen = set()
    out = []
    for p in configs:
        q = {k:v for k,v in p.items() if k not in ("sl","rr")}
        key = json.dumps(q, sort_keys=True)
        if key not in seen:
            seen.add(key)
            out.append(q)
    return out


def _risk_pairs(configs):
    vals = sorted({(float(p["sl"]), float(p["rr"])) for p in configs})
    return vals


def _fast_training_screen(x: pd.DataFrame, sig: pd.Series, cost: CostModel, hold_bars: int = 8):
    """
    Cheap TRAIN-only NumPy screen used only to reduce expensive lifecycle tests.
    It never touches final OOS.
    """
    s = sig.reindex(x.index).fillna(0).astype(np.int8).to_numpy()
    entry = x["open"].shift(-1).to_numpy(dtype=float)
    exit_ = x["close"].shift(-int(hold_bars)).to_numpy(dtype=float)
    valid = (s != 0) & np.isfinite(entry) & np.isfinite(exit_) & (entry > 0)
    if int(valid.sum()) < 10:
        return -1e9
    sv = s[valid].astype(float)
    ev = entry[valid]
    xv = exit_[valid]
    net = sv * (xv / ev - 1.0)
    net -= (float(cost.spread_usd_per_oz) + 2.0*float(cost.slippage_each_side_usd_per_oz)) / ev
    finite = np.isfinite(net)
    net = net[finite]
    sv = sv[finite]
    if len(net) < 10:
        return -1e9
    long_n = int(np.sum(sv > 0))
    short_n = int(np.sum(sv < 0))
    side_penalty = (5.0 if long_n < 3 else 0.0) + (5.0 if short_n < 3 else 0.0)
    win_rate = float(np.mean(net > 0))
    return float(np.mean(net))*10000.0*math.sqrt(len(net)) + 2.0*(win_rate-0.5) - side_penalty


def _wf_slices(n: int, folds: int = 4, min_bars: int = 250):
    folds = max(3, int(folds))
    edges = np.linspace(0, n, folds+1, dtype=int)
    out = []
    for i in range(folds):
        a, b = int(edges[i]), int(edges[i+1])
        if b-a >= min_bars:
            out.append((a,b))
    return out


def _walkforward_candidate_metrics(x: pd.DataFrame, sig: pd.Series, sl: float, rr: float,
                                   cost: CostModel, folds: int = 4):
    fold_metrics = []
    for a,b in _wf_slices(len(x), folds=folds):
        xf = x.iloc[a:b]
        sf = sig.iloc[a:b]
        _, m, _ = backtest_v5_lifecycle(
            xf, sf, sl, rr, cost, max_hold_bars=max(1, len(xf))
        )
        fold_metrics.append(m)
    if not fold_metrics:
        return None

    returns = np.array([float(m["return_pct"]) for m in fold_metrics], dtype=float)
    pfs = np.array([float(m["profit_factor"]) for m in fold_metrics], dtype=float)
    dds = np.array([float(m["max_dd_pct"]) for m in fold_metrics], dtype=float)
    scores = np.array([research_train_score(m) for m in fold_metrics], dtype=float)
    positive = int((returns > 0).sum())
    both_side_positive = int(sum(
        1 for m in fold_metrics
        if float(m["long_return_pct"]) > 0 and float(m["short_return_pct"]) > 0
    ))
    selection_score = (
        float(np.mean(scores))
        - 0.45*float(np.std(returns))
        + 0.20*float(np.median(returns))
        + 0.15*float(np.min(returns))
        + 0.75*positive
        + 0.50*both_side_positive
    )
    return {
        "selection_score": selection_score,
        "wf_folds": len(fold_metrics),
        "wf_positive_folds": positive,
        "wf_both_side_positive_folds": both_side_positive,
        "wf_mean_return_pct": float(np.mean(returns)),
        "wf_median_return_pct": float(np.median(returns)),
        "wf_worst_return_pct": float(np.min(returns)),
        "wf_std_return_pct": float(np.std(returns)),
        "wf_mean_pf": float(np.mean(pfs)),
        "wf_worst_dd_pct": float(np.min(dds)),
    }


def run_deep_rule_selection(train: pd.DataFrame, cost: CostModel, timeframe: str,
                            finalists_per_family: int = 2, folds: int = 4):
    """
    TRAIN ONLY.
    Stage 1: vectorized screen of unique signal configurations.
    Stage 2: full V5 lifecycle walk-forward on finalists × risk geometry.
    Returns one winner per family plus one training-selected consensus.
    """
    grids = param_grid("Balanced")
    family_rows = []
    family_details = {}

    for family, configs in grids.items():
        signal_configs = _signal_only_params(configs)
        risk_pairs = _risk_pairs(configs)
        screened = []
        for sp in signal_configs:
            sig = STRATEGIES[family](train, sp)
            screened.append((_fast_training_screen(train, sig, cost), sp))
        screened.sort(key=lambda z:z[0], reverse=True)
        finalists = screened[:max(1, int(finalists_per_family))]

        best = None
        for _, sp in finalists:
            sig = STRATEGIES[family](train, sp)
            for sl, rr in risk_pairs:
                p = dict(sp)
                p.update({"sl":float(sl), "rr":float(rr)})
                wf = _walkforward_candidate_metrics(train, sig, sl, rr, cost, folds=folds)
                if wf is None:
                    continue
                if best is None or wf["selection_score"] > best[0]:
                    best = (wf["selection_score"], p, wf)

        if best is None:
            continue
        score, p, wf = best
        full_sig = STRATEGIES[family](train, p)
        _, train_m, _ = backtest_v5_lifecycle(
            train, full_sig, p["sl"], p["rr"], cost, max_hold_bars=max(1, len(train))
        )
        p = dict(p)
        p["_timeframe"] = timeframe
        p["_context_minutes"] = 240 if timeframe == "1h" else 60

        row = {
            "timeframe": timeframe,
            "family": family,
            "model": "RULE_DEEP",
            **wf,
            **{f"train_{k}":v for k,v in train_m.items()},
            "params": json.dumps(p, sort_keys=True),
        }
        family_rows.append(row)
        family_details[family] = {"params":p, "wf":wf, "train_metrics":train_m}

    # TRAIN-only consensus candidate from the top 3 families by walk-forward score.
    if len(family_rows) >= 3:
        fam_df = pd.DataFrame(family_rows).sort_values("selection_score", ascending=False)
        top = fam_df.head(3)
        members = []
        for _, r in top.iterrows():
            pp = json.loads(r["params"])
            pp.pop("_timeframe", None)
            pp.pop("_context_minutes", None)
            members.append({"family":str(r["family"]), "params":pp})

        best_cons = None
        for vote in (2,):
            for sl, rr in ((1.2,1.5),(1.5,1.5),(1.5,2.0),(2.0,2.0),(2.0,2.5)):
                p = {"members":members, "vote":vote, "sl":sl, "rr":rr}
                sig = STRATEGIES["Deep Consensus"](train, p)
                wf = _walkforward_candidate_metrics(train, sig, sl, rr, cost, folds=folds)
                if wf is not None and (best_cons is None or wf["selection_score"] > best_cons[0]):
                    best_cons = (wf["selection_score"], p, wf)
        if best_cons is not None:
            _, p, wf = best_cons
            sig = STRATEGIES["Deep Consensus"](train, p)
            _, train_m, _ = backtest_v5_lifecycle(
                train, sig, p["sl"], p["rr"], cost, max_hold_bars=max(1,len(train))
            )
            p = dict(p)
            p["_timeframe"] = timeframe
            p["_context_minutes"] = 240 if timeframe == "1h" else 60
            row = {
                "timeframe":timeframe,
                "family":"Deep Consensus",
                "model":"RULE_ENSEMBLE",
                **wf,
                **{f"train_{k}":v for k,v in train_m.items()},
                "params":json.dumps(p, sort_keys=True),
            }
            family_rows.append(row)
            family_details["Deep Consensus"] = {"params":p, "wf":wf, "train_metrics":train_m}

    return pd.DataFrame(family_rows), family_details


def deep_selection_rank(rows: pd.DataFrame):
    if rows is None or rows.empty:
        return rows
    out = rows.copy()
    # No OOS values are used here.
    out["selection_robust"] = (
        (out["wf_positive_folds"] >= np.maximum(2, out["wf_folds"]-1))
        & (out["wf_mean_pf"] >= 1.0)
        & (out["train_trades"] >= 12)
    )
    out["global_selection_score"] = (
        out["selection_score"]
        + 0.35*out["wf_median_return_pct"]
        + 0.15*out["wf_worst_return_pct"]
        - 0.25*out["wf_std_return_pct"]
        + np.where(out["selection_robust"], 3.0, -3.0)
    )
    return out.sort_values(
        ["selection_robust","global_selection_score"],
        ascending=[False,False]
    ).reset_index(drop=True)



def label_market_regimes(x: pd.DataFrame) -> pd.Series:
    """
    Point-in-time regime labels for a prospective NEXT-BAR entry.

    The label exposed at timestamp t uses only information available through t-1:
    the raw regime is shifted one bar before it is assigned to an entry timestamp.
    """
    z = ensure_utc_datetime_index(x)
    adxv = z["adx14"].astype(float)
    atrp = z["atr_pct"].astype(float)
    # Rolling percentile based only on prior observations.
    vol_cut = atrp.shift(1).rolling(252, min_periods=50).quantile(0.70)
    high_vol = atrp > vol_cut
    trend_up = (adxv >= 23.0) & (z["ema20"] > z["ema100"])
    trend_dn = (adxv >= 23.0) & (z["ema20"] < z["ema100"])

    raw = pd.Series("RANGE", index=z.index, dtype="object")
    raw.loc[(~trend_up) & (~trend_dn) & high_vol] = "VOLATILE"
    raw.loc[trend_up] = "TREND_UP"
    raw.loc[trend_dn] = "TREND_DOWN"

    # A trade enters on the next bar, so expose the prior closed-bar regime.
    return raw.shift(1).fillna("UNKNOWN")


def _trade_subset_metrics(tdf: pd.DataFrame) -> dict:
    if tdf is None or tdf.empty:
        return {
            "return_pct": 0.0,
            "profit_factor": 0.0,
            "trades": 0,
            "long_return_pct": 0.0,
            "short_return_pct": 0.0,
        }
    r = tdf["ret"].astype(float)
    wins = float(r[r > 0].sum())
    losses = float(-r[r < 0].sum())
    pf = wins / losses if losses > 0 else (99.0 if wins > 0 else 0.0)

    def _side(side):
        s = tdf.loc[tdf["side"] == side, "ret"].astype(float)
        return (float(np.prod(1.0 + s)) - 1.0) * 100.0 if len(s) else 0.0

    return {
        "return_pct": (float(np.prod(1.0 + r)) - 1.0) * 100.0,
        "profit_factor": float(pf),
        "trades": int(len(tdf)),
        "long_return_pct": _side(1),
        "short_return_pct": _side(-1),
    }


def _regime_trade_metrics(trades: pd.DataFrame, x: pd.DataFrame) -> dict:
    if trades is None or trades.empty:
        return {
            "regime_count": 0,
            "positive_regimes": 0,
            "worst_regime_return_pct": 0.0,
            "regime_summary": {},
        }

    regimes = label_market_regimes(x)
    t = trades.copy()
    t["entry_time"] = pd.to_datetime(t["entry_time"], utc=True)
    t["regime"] = [
        regimes.get(ts, "UNKNOWN") if ts in regimes.index else "UNKNOWN"
        for ts in t["entry_time"]
    ]

    summary = {}
    qualified_returns = []
    positive = 0
    for regime, g in t.groupby("regime"):
        if regime == "UNKNOWN":
            continue
        m = _trade_subset_metrics(g)
        summary[str(regime)] = m
        # Require at least 3 trades before using a regime in robustness scoring.
        if int(m["trades"]) >= 3:
            qualified_returns.append(float(m["return_pct"]))
            if float(m["return_pct"]) > 0:
                positive += 1

    return {
        "regime_count": int(len(qualified_returns)),
        "positive_regimes": int(positive),
        "worst_regime_return_pct": (
            float(min(qualified_returns)) if qualified_returns else 0.0
        ),
        "regime_summary": summary,
    }


def _nested_outer_splits(n: int, folds: int = 4, min_train: int = 600, min_val: int = 180):
    """
    Expanding-window outer CV:
      [FIT ........][VAL]
      [FIT ..............][VAL]
      ...

    All folds live entirely inside the pre-holdout research window.
    """
    folds = max(3, int(folds))
    if n < min_train + folds * min_val:
        min_val = max(80, int((n - min_train) / max(1, folds)))
    if min_val <= 0:
        return []

    available_for_val = max(0, n - min_train)
    val_size = max(min_val, int(available_for_val / max(1, folds)))
    if min_train + folds * val_size > n:
        val_size = max(1, int((n - min_train) / folds))

    out = []
    fit_end = n - folds * val_size
    fit_end = max(min_train, fit_end)

    for i in range(folds):
        val_start = fit_end + i * val_size
        val_end = min(n, val_start + val_size)
        if val_end - val_start < max(40, min_val // 2):
            continue
        out.append((0, val_start, val_start, val_end))
    return out


def _select_family_params_on_fit(
    fit: pd.DataFrame,
    family: str,
    cost: CostModel,
    finalists_per_family: int = 1,
    inner_folds: int = 3,
):
    """
    Parameter selection happens ONLY inside the outer-fit slice.
    The outer validation slice is never used here.
    """
    configs = param_grid("Balanced")[family]
    signal_configs = _signal_only_params(configs)
    risk_pairs = _risk_pairs(configs)

    screened = []
    for sp in signal_configs:
        sig = STRATEGIES[family](fit, sp)
        screened.append((_fast_training_screen(fit, sig, cost), sp))
    screened.sort(key=lambda z: z[0], reverse=True)
    finalists = screened[:max(1, int(finalists_per_family))]

    best = None
    for _, sp in finalists:
        sig = STRATEGIES[family](fit, sp)
        for sl, rr in risk_pairs:
            wf = _walkforward_candidate_metrics(
                fit, sig, float(sl), float(rr), cost, folds=max(3, int(inner_folds))
            )
            if wf is None:
                continue
            p = dict(sp)
            p.update({"sl": float(sl), "rr": float(rr)})
            if best is None or float(wf["selection_score"]) > float(best[0]):
                best = (float(wf["selection_score"]), p, wf)
    return best


def run_nested_family_selection(
    train: pd.DataFrame,
    cost: CostModel,
    timeframe: str,
    *,
    outer_folds: int = 4,
    inner_folds: int = 3,
    finalists_per_family: int = 1,
):
    """
    Robust family comparison on PRE-HOLDOUT data only.

    For every family and every OUTER fold:
    - select parameters only on the expanding FIT slice
    - evaluate those selected parameters on the unseen OUTER validation slice

    After unbiased outer validation is collected, final deployment parameters are
    re-selected using the entire pre-holdout train window.
    """
    rows = []
    details = {}
    outer_splits = _nested_outer_splits(len(train), folds=outer_folds)
    if len(outer_splits) < 3:
        return pd.DataFrame(), {}

    for family in [k for k in STRATEGIES.keys() if k != "Deep Consensus"]:
        fold_metrics = []
        fold_trades = []
        fold_params = []

        for fit_a, fit_b, val_a, val_b in outer_splits:
            fit = train.iloc[fit_a:fit_b].copy()
            val = train.iloc[val_a:val_b].copy()
            if len(fit) < 300 or len(val) < 80:
                continue

            selected = _select_family_params_on_fit(
                fit,
                family,
                cost,
                finalists_per_family=finalists_per_family,
                inner_folds=inner_folds,
            )
            if selected is None:
                continue

            _, p, _ = selected
            sig_val = STRATEGIES[family](val, p)
            trades, m, _ = backtest_v5_lifecycle(
                val,
                sig_val,
                float(p["sl"]),
                float(p["rr"]),
                cost,
                max_hold_bars=max(1, len(val)),
            )
            fold_metrics.append(m)
            if trades is not None and len(trades):
                fold_trades.append((trades, val))
            fold_params.append(p)

        if len(fold_metrics) < 3:
            continue

        # Outer-validation statistics.
        rets = np.array([float(m["return_pct"]) for m in fold_metrics], dtype=float)
        pfs = np.array([float(m["profit_factor"]) for m in fold_metrics], dtype=float)
        dds = np.array([float(m["max_dd_pct"]) for m in fold_metrics], dtype=float)

        positive_folds = int((rets > 0).sum())
        both_side_folds = int(sum(
            1 for m in fold_metrics
            if float(m["long_return_pct"]) > 0 and float(m["short_return_pct"]) > 0
        ))

        # Aggregate independent validation trades.
        combined_trades = []
        regime_summaries = []
        for trades, val in fold_trades:
            combined_trades.append(trades)
            regime_summaries.append(_regime_trade_metrics(trades, val))

        all_trades = (
            pd.concat(combined_trades, ignore_index=True)
            if combined_trades else pd.DataFrame()
        )
        agg = _trade_subset_metrics(all_trades)

        # Aggregate regime returns from all validation trades by reconstructing
        # a pooled entry-regime table.
        pooled_regime_rows = []
        for trades, val in fold_trades:
            reg = label_market_regimes(val)
            z = trades.copy()
            z["entry_time"] = pd.to_datetime(z["entry_time"], utc=True)
            z["regime"] = [
                reg.get(ts, "UNKNOWN") if ts in reg.index else "UNKNOWN"
                for ts in z["entry_time"]
            ]
            pooled_regime_rows.append(z)
        pooled = (
            pd.concat(pooled_regime_rows, ignore_index=True)
            if pooled_regime_rows else pd.DataFrame()
        )
        regime_metrics = _regime_trade_metrics(
            pooled if not pooled.empty else pd.DataFrame(),
            train,
        ) if False else None

        # Calculate pooled regime metrics directly (avoid mismatched index).
        regime_summary = {}
        qualified_regime_returns = []
        positive_regimes = 0
        if not pooled.empty:
            for regime, g in pooled.groupby("regime"):
                if regime == "UNKNOWN":
                    continue
                m = _trade_subset_metrics(g)
                regime_summary[str(regime)] = m
                if int(m["trades"]) >= 3:
                    qualified_regime_returns.append(float(m["return_pct"]))
                    if float(m["return_pct"]) > 0:
                        positive_regimes += 1

        regime_count = len(qualified_regime_returns)
        worst_regime = min(qualified_regime_returns) if qualified_regime_returns else 0.0

        # Refit final parameters on ALL pre-holdout data after nested estimation.
        final_sel = _select_family_params_on_fit(
            train,
            family,
            cost,
            finalists_per_family=finalists_per_family,
            inner_folds=max(3, inner_folds),
        )
        if final_sel is None:
            continue
        _, final_params, final_inner = final_sel

        full_sig = STRATEGIES[family](train, final_params)
        _, train_m, _ = backtest_v5_lifecycle(
            train,
            full_sig,
            float(final_params["sl"]),
            float(final_params["rr"]),
            cost,
            max_hold_bars=max(1, len(train)),
        )

        nested_robust = (
            positive_folds >= max(2, len(fold_metrics) - 1)
            and float(np.mean(pfs)) >= 1.05
            and float(agg["long_return_pct"]) > 0
            and float(agg["short_return_pct"]) > 0
            and int(agg["trades"]) >= 12
            and regime_count >= 3
            and positive_regimes >= 2
            and float(worst_regime) > -5.0
        )

        nested_score = (
            float(np.median(rets))
            + 0.35 * float(np.mean(rets))
            + 0.20 * float(np.min(rets))
            - 0.40 * float(np.std(rets))
            + 1.50 * float(np.mean(np.clip(pfs, 0, 3)))
            + 1.00 * positive_folds
            + 0.75 * both_side_folds
            + 0.50 * positive_regimes
            + 0.25 * float(worst_regime)
            + (4.0 if nested_robust else -4.0)
        )

        p = dict(final_params)
        p["_timeframe"] = timeframe
        p["_context_minutes"] = 240 if timeframe == "1h" else 60

        row = {
            "timeframe": timeframe,
            "family": family,
            "model": "RULE_NESTED",
            "nested_robust": bool(nested_robust),
            "nested_score": float(nested_score),
            "outer_folds": int(len(fold_metrics)),
            "outer_positive_folds": int(positive_folds),
            "outer_both_side_positive_folds": int(both_side_folds),
            "outer_mean_return_pct": float(np.mean(rets)),
            "outer_median_return_pct": float(np.median(rets)),
            "outer_worst_return_pct": float(np.min(rets)),
            "outer_std_return_pct": float(np.std(rets)),
            "outer_mean_pf": float(np.mean(pfs)),
            "outer_worst_dd_pct": float(np.min(dds)),
            "cv_return_pct": float(agg["return_pct"]),
            "cv_profit_factor": float(agg["profit_factor"]),
            "cv_trades": int(agg["trades"]),
            "cv_long_return_pct": float(agg["long_return_pct"]),
            "cv_short_return_pct": float(agg["short_return_pct"]),
            "regime_count": int(regime_count),
            "positive_regimes": int(positive_regimes),
            "worst_regime_return_pct": float(worst_regime),
            "train_return_pct": float(train_m["return_pct"]),
            "train_profit_factor": float(train_m["profit_factor"]),
            "train_max_dd_pct": float(train_m["max_dd_pct"]),
            "train_trades": int(train_m["trades"]),
            "params": json.dumps(p, sort_keys=True),
            "regime_summary_json": json.dumps(regime_summary, sort_keys=True),
        }
        rows.append(row)
        details[family] = {
            "params": p,
            "fold_metrics": fold_metrics,
            "regime_summary": regime_summary,
            "final_inner": final_inner,
            "train_metrics": train_m,
        }

    return pd.DataFrame(rows), details


def robust_selection_rank(rows: pd.DataFrame) -> pd.DataFrame:
    if rows is None or rows.empty:
        return rows
    out = rows.copy()
    return out.sort_values(
        ["nested_robust", "nested_score", "outer_median_return_pct"],
        ascending=[False, False, False],
    ).reset_index(drop=True)


def evaluate_robust_final_oos(
    selected_row,
    test: pd.DataFrame,
    cost: CostModel,
    target: float,
    min_trades: int,
    max_dd: float,
):
    family = str(selected_row["family"])
    params = json.loads(selected_row["params"])
    sig = STRATEGIES[family](test, params)
    trades, metrics, curve = backtest_v5_lifecycle(
        test,
        sig,
        float(params["sl"]),
        float(params["rr"]),
        cost,
        max_hold_bars=max(1, len(test)),
    )

    gate_row = {
        "oos_return_pct": metrics["return_pct"],
        "oos_long_return_pct": metrics["long_return_pct"],
        "oos_short_return_pct": metrics["short_return_pct"],
        "oos_long_trades": metrics["long_trades"],
        "oos_short_trades": metrics["short_trades"],
        "oos_max_dd_pct": metrics["max_dd_pct"],
        "oos_trades": metrics["trades"],
        "oos_profit_factor": metrics["profit_factor"],
    }
    passed, reason = research_target_gate(
        pd.Series(gate_row),
        target=target,
        min_trades=min_trades,
        max_dd=max_dd,
    )

    if not bool(selected_row.get("nested_robust", False)):
        passed = False
        reason = (
            (reason + "; " if reason != "PASS" else "")
            + "nested pre-holdout robustness gate failed"
        )

    final_regimes = _regime_trade_metrics(trades, test)
    if int(final_regimes["regime_count"]) < 2:
        passed = False
        reason = (
            (reason + "; " if reason != "PASS" else "")
            + "final OOS regime coverage too narrow"
        )

    return {
        "family": family,
        "timeframe": str(selected_row["timeframe"]),
        "model": str(selected_row["model"]),
        "params": params,
        "metrics": metrics,
        "trades": trades,
        "curve": curve,
        "target_pass": bool(passed),
        "gate_reason": reason,
        "final_regimes": final_regimes,
    }


def evaluate_deep_final_oos(selected_row, test: pd.DataFrame, cost: CostModel,
                            target: float, min_trades: int, max_dd: float):
    family = str(selected_row["family"])
    params = json.loads(selected_row["params"])
    sig = STRATEGIES[family](test, params)
    trades, metrics, curve = backtest_v5_lifecycle(
        test, sig, float(params["sl"]), float(params["rr"]), cost,
        max_hold_bars=max(1, len(test))
    )
    gate_row = {
        "oos_return_pct":metrics["return_pct"],
        "oos_long_return_pct":metrics["long_return_pct"],
        "oos_short_return_pct":metrics["short_return_pct"],
        "oos_long_trades":metrics["long_trades"],
        "oos_short_trades":metrics["short_trades"],
        "oos_max_dd_pct":metrics["max_dd_pct"],
        "oos_trades":metrics["trades"],
        "oos_profit_factor":metrics["profit_factor"],
    }
    passed, reason = research_target_gate(
        pd.Series(gate_row), target=target, min_trades=min_trades, max_dd=max_dd
    )
    # Add training-only walk-forward stability requirement.
    if int(selected_row["wf_positive_folds"]) < max(2, int(selected_row["wf_folds"])-1):
        passed = False
        reason = (reason + "; " if reason != "PASS" else "") + "walk-forward stability gate failed"
    return {
        "family":family,
        "timeframe":str(selected_row["timeframe"]),
        "model":str(selected_row["model"]),
        "params":params,
        "metrics":metrics,
        "trades":trades,
        "curve":curve,
        "target_pass":bool(passed),
        "gate_reason":reason,
    }


def internal_ml_benchmark(train: pd.DataFrame, cost: CostModel):
    """
    ML benchmark uses ONLY the training window. It never sees final OOS in V6.2.
    """
    if len(train) < 1200:
        return pd.DataFrame()
    cut = int(len(train)*0.72)
    fit = train.iloc[:cut].copy()
    val = train.iloc[cut:].copy()
    rows, _ = run_ml_research_v6(fit, val, cost)
    if rows is None or rows.empty:
        return pd.DataFrame()
    rows = rows.copy()
    rows["scope"] = "TRAIN_INTERNAL_ONLY"
    return rows

def build_research_features(primary_15m, h1, include_macro=True):
    x = add_features(primary_15m[["open","high","low","close"]].copy())
    x = add_h1_context(x, h1[["open","high","low","close"]].copy())
    notes = []
    if include_macro:
        x, notes = attach_macro_features_v6(x)
    else:
        for col in ["us10y_chg5","real10y_chg5","usd_broad_chg5"]:
            x[col] = np.nan
    return x, notes


def current_rule_signal(family: str, params: dict, primary, context, context_minutes: int = 60):
    if family not in STRATEGIES:
        return 0, None
    x, _ = build_deep_features(primary, context, context_minutes, include_macro=False)
    sig = STRATEGIES[family](x, params)
    if sig.empty:
        return 0, x
    return int(sig.iloc[-1]), x


def build_research_trade_plan(
    candidate_id: str,
    side: Side,
    entry_reference: Decimal,
    atr_value: Decimal,
    params: dict,
    equity: Decimal,
    quote_policy: QuotePolicy,
    fixed_lot: Decimal,
    contract_size: Decimal,
    gate_pass: bool,
):
    sl_atr = Decimal(str(params.get("sl", 1.5)))
    rr = Decimal(str(params.get("rr", 2.0)))
    if atr_value <= 0 or equity <= 0 or sl_atr <= 0 or rr <= 0:
        return None
    if side == Side.BUY:
        sl = entry_reference - sl_atr*atr_value
    else:
        sl = entry_reference + sl_atr*atr_value
    R = abs(entry_reference-sl)
    if R <= 0:
        return None

    mults_float = research_target_multipliers(float(rr))
    mults = tuple(Decimal(str(round(x,8))) for x in mults_float)
    targets = tuple(
        entry_reference + R*m if side == Side.BUY else entry_reference - R*m
        for m in mults
    )
    gross = R*contract_size*fixed_lot
    risk_pct = Decimal("100")*gross/equity
    payload = {
        "candidate_id":candidate_id,"side":side.value,"entry":str(entry_reference),
        "sl":str(sl),"targets":[str(x) for x in targets],
        "mults":[str(x) for x in mults],"source":"RESEARCH_STRATEGY",
        "policy":quote_policy.value,
    }
    plan_hash = hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
    return TradePlan(
        candidate_id=candidate_id,
        side=side,
        entry_reference=entry_reference,
        initial_sl=sl,
        provisional_targets=targets,
        original_lot=fixed_lot,
        gross_risk_usd=gross,
        risk_pct=risk_pct,
        grade=Grade.A_PLUS if gate_pass else Grade.B,
        buy_index=100 if side == Side.BUY else 0,
        sell_index=100 if side == Side.SELL else 0,
        evidence_completeness=100,
        setup_quality=80 if gate_pass else 60,
        quote_policy=quote_policy,
        reasons_for=(f"Activated research strategy: {side.value}",),
        reasons_against=(() if gate_pass else ("Research target gate was not fully passed; PAPER experiment only.",)),
        plan_hash=plan_hash,
        created_at=datetime.now(timezone.utc),
        source="RESEARCH_STRATEGY",
        research_authorized=bool(gate_pass),
        target_multipliers=mults,
    )
# ===== END engines/strategy_research_engine_v6.py =====


# ===== BEGIN engines/signal_engine.py =====

from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import numpy as np



TF_WEIGHTS = {"5m": 0.20, "15m": 0.30, "1h": 0.50}
GROUP_WEIGHTS = {
    "trend": 0.30,
    "rsi_momentum": 0.15,
    "structure": 0.20,
    "levels": 0.15,
    "patterns": 0.20,
}


def _weighted_tf(by_tf, func):
    return float(sum(TF_WEIGHTS[tf] * func(by_tf[tf]) for tf in TF_WEIGHTS))


def _structure_evidence(patterns):
    vals = []
    for p in patterns:
        if p.pattern_type in {"BOS", "CHOCH"}:
            sign = 1 if p.direction == "BULLISH" else -1 if p.direction == "BEARISH" else 0
            vals.append(sign * p.quality_score / 100.0)
    return float(np.clip(max(vals, key=abs) if vals else 0.0, -1, 1))


def _levels_evidence(patterns, current_price: float, atr15: float):
    ev = []
    for p in patterns:
        if p.pattern_type not in {"SUPPORT", "RESISTANCE", "RISING_TRENDLINE", "FALLING_TRENDLINE", "DEMAND_ZONE", "SUPPLY_ZONE"}:
            continue
        sign = 1 if p.direction == "BULLISH" else -1 if p.direction == "BEARISH" else 0
        relevance = p.quality_score / 100.0
        if p.level is not None and atr15 > 0:
            distance = abs(float(p.level) - current_price)
            relevance *= max(0.25, min(1.0, 1.5 - distance / (3 * atr15)))
        ev.append(sign * relevance)
    return float(np.clip(max(ev, key=abs) if ev else 0.0, -1, 1))


def evaluate(bundle: AnalysisBundle) -> SignalEvaluation:
    now = datetime.now(timezone.utc)
    mandatory = ["5m", "15m", "1h"]
    complete_tfs = [tf for tf in mandatory if tf in bundle.by_timeframe]
    completeness = int(round(100 * len(complete_tfs) / len(mandatory)))
    if not bundle.complete or completeness < 100:
        return SignalEvaluation(
            side=Side.BUY, buy_index=50, sell_index=50, evidence_completeness=completeness,
            setup_quality=0, grade=Grade.C, status=CandidateStatus.INSUFFICIENT_DATA,
            evidence=(), reasons_for=(), reasons_against=("Mandatory analysis data is incomplete.",), evaluated_at=now,
        )

    trend = _weighted_tf(bundle.by_timeframe, trend_evidence)
    rsi_mom = _weighted_tf(bundle.by_timeframe, rsi_momentum_evidence)
    structure = _structure_evidence(bundle.patterns)
    p_ev, p_for, p_against = pattern_group_evidence(list(bundle.patterns))
    current = bundle.by_timeframe["15m"]["close"]
    atr15 = bundle.by_timeframe["15m"]["atr14"]
    levels = _levels_evidence(bundle.patterns, current, atr15)

    vals = {"trend": trend, "rsi_momentum": rsi_mom, "structure": structure, "levels": levels, "patterns": p_ev}
    evidence = []
    D = 0.0
    for name, weight in GROUP_WEIGHTS.items():
        value = float(np.clip(vals[name], -1, 1))
        contribution = value * weight
        D += contribution
        evidence.append(EvidenceGroup(name, value, weight, contribution, f"{name} evidence={value:+.3f}"))
    D = float(np.clip(D, -1, 1))
    buy = int(round(50 + 50 * D))
    sell = 100 - buy
    side = Side.BUY if buy >= sell else Side.SELL
    selected = max(buy, sell)

    # Setup quality intentionally distinct from direction. Reward confirmed usable structure, not direction itself.
    pattern_quality = max([p.quality_score for p in bundle.patterns], default=45)
    quality = int(np.clip(45 + 0.30 * pattern_quality + 10 * abs(structure) + 8 * abs(levels), 0, 100))

    reasons_for = []
    reasons_against = []
    direction_sign = 1 if side == Side.BUY else -1
    for e in evidence:
        if e.value * direction_sign > 0.10:
            reasons_for.append(f"{e.name}: {e.value:+.2f}")
        elif e.value * direction_sign < -0.10:
            reasons_against.append(f"{e.name}: {e.value:+.2f}")
    reasons_for.extend(p_for if side == Side.BUY else p_against)
    reasons_against.extend(p_against if side == Side.BUY else p_for)

    if selected >= 80 and quality >= 75 and completeness >= 90:
        grade, status = Grade.A_PLUS, CandidateStatus.APPROVED
    elif selected >= 70 and quality >= 65 and completeness >= 85:
        grade, status = Grade.A, CandidateStatus.APPROVED
    elif selected >= 60:
        grade, status = Grade.B, CandidateStatus.WATCH_ONLY
    else:
        grade, status = Grade.C, CandidateStatus.WATCH_ONLY

    return SignalEvaluation(
        side=side, buy_index=buy, sell_index=sell, evidence_completeness=completeness,
        setup_quality=quality, grade=grade, status=status, evidence=tuple(evidence),
        reasons_for=tuple(reasons_for[:10]), reasons_against=tuple(reasons_against[:10]), evaluated_at=now,
    )


def _best_level(patterns, side: Side, entry: Decimal):
    candidates = []
    for p in patterns:
        if p.level is None:
            continue
        level = p.level
        if side == Side.BUY and p.pattern_type == "SUPPORT" and level < entry:
            candidates.append((abs(entry-level), level))
        if side == Side.SELL and p.pattern_type == "RESISTANCE" and level > entry:
            candidates.append((abs(entry-level), level))
    return min(candidates)[1] if candidates else None


def build_trade_plan(candidate_id: str, evaluation: SignalEvaluation, bundle: AnalysisBundle, entry_reference: Decimal, equity: Decimal, quote_policy: QuotePolicy, fixed_lot: Decimal = Decimal("0.03"), contract_size: Decimal = Decimal("100")) -> TradePlan | None:
    if evaluation.status != CandidateStatus.APPROVED:
        return None
    atr15 = Decimal(str(bundle.by_timeframe["15m"]["atr14"]))
    structure = _best_level(bundle.patterns, evaluation.side, entry_reference)
    buffer = max(Decimal("0.80"), atr15 * Decimal("0.20"))
    fallback = max(Decimal("3.00"), atr15 * Decimal("1.10"))
    if evaluation.side == Side.BUY:
        sl = (structure - buffer) if structure is not None else (entry_reference - fallback)
        if sl >= entry_reference:
            return None
        R = entry_reference - sl
        targets = tuple(entry_reference + R*m for m in map(Decimal, ["0.40","0.70","1.00","1.30","1.70"]))
    else:
        sl = (structure + buffer) if structure is not None else (entry_reference + fallback)
        if sl <= entry_reference:
            return None
        R = sl - entry_reference
        targets = tuple(entry_reference - R*m for m in map(Decimal, ["0.40","0.70","1.00","1.30","1.70"]))
    gross = abs(entry_reference - sl) * contract_size * fixed_lot
    risk_pct = Decimal("100") * gross / equity if equity > 0 else Decimal("999")
    payload = {
        "candidate_id": candidate_id, "side": evaluation.side.value, "entry": str(entry_reference), "sl": str(sl),
        "targets": [str(x) for x in targets], "lot": str(fixed_lot), "grade": evaluation.grade.value,
        "policy": quote_policy.value,
    }
    plan_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return TradePlan(
        candidate_id=candidate_id, side=evaluation.side, entry_reference=entry_reference, initial_sl=sl,
        provisional_targets=targets, original_lot=fixed_lot, gross_risk_usd=gross, risk_pct=risk_pct,
        grade=evaluation.grade, buy_index=evaluation.buy_index, sell_index=evaluation.sell_index,
        evidence_completeness=evaluation.evidence_completeness, setup_quality=evaluation.setup_quality,
        quote_policy=quote_policy, reasons_for=evaluation.reasons_for, reasons_against=evaluation.reasons_against,
        plan_hash=plan_hash, created_at=datetime.now(timezone.utc),
    )
# ===== END engines/signal_engine.py =====


# ===== BEGIN engines/risk_engine.py =====

from datetime import datetime, timedelta, timezone
from decimal import Decimal



class RiskEngine:
    def __init__(self, settings, repository):
        self.settings = settings
        self.repository = repository

    def assess(self, account, plan: TradePlan, quote: Quote, latest_closed_1m_at=None) -> RiskDecision:
        now = datetime.now(timezone.utc)
        reasons = []
        explanations = []
        if account.kill_switch:
            reasons.append("KILL_SWITCH")
            explanations.append("Account kill switch blocks new entries.")
        if not account.auto_paper_enabled:
            reasons.append("AUTO_PAPER_DISABLED")
            explanations.append("Auto paper execution is not enabled.")
        if plan.grade != Grade.A_PLUS and not plan.research_authorized:
            reasons.append("GRADE_NOT_ELIGIBLE")
            explanations.append("Automatic paper execution requires A+, unless the user explicitly activated a research strategy for PAPER forward testing.")
        if account.equity is None or Decimal(account.equity) <= 0:
            reasons.append("INVALID_EQUITY")
            explanations.append("Account equity must be positive.")
        if plan.risk_pct > self.settings.max_risk_per_trade_pct:
            reasons.append("RISK_PER_TRADE_EXCEEDED")
            explanations.append(f"Plan risk {plan.risk_pct:.2f}% exceeds {self.settings.max_risk_per_trade_pct}%.")

        open_positions = self.repository.open_positions(account.id)
        if len(open_positions) >= self.settings.max_open_positions:
            reasons.append("MAX_OPEN_POSITIONS")
            explanations.append("Global open-position limit reached.")
        own_open = [p for p in open_positions if p.source in ("OWN_SYSTEM", "RESEARCH_STRATEGY", "PAPER_EXPERIMENT")]
        if len(own_open) >= self.settings.max_own_positions:
            reasons.append("MAX_OWN_POSITIONS")
            explanations.append("Own-system / research-strategy open-position limit reached.")
        if any(p.side == plan.side.value for p in open_positions):
            reasons.append("SAME_DIRECTION_OPEN")
            explanations.append("A position in the same direction is already open.")
        if self.repository.position_for_candidate(plan.candidate_id) is not None:
            reasons.append("DUPLICATE_SETUP")
            explanations.append("This candidate already has a position.")

        if plan.quote_policy == QuotePolicy.STRICT_EXECUTABLE:
            if quote.bid is None or quote.ask is None:
                reasons.append("BID_ASK_UNAVAILABLE")
                explanations.append("Strict mode requires genuine bid and ask; Twelve Data reference /price is not treated as executable bid/ask.")
            elif quote.source_timestamp is None:
                reasons.append("QUOTE_FRESHNESS_UNKNOWN")
                explanations.append("Strict mode requires a verified source timestamp.")
            else:
                age = (now - _utc(quote.source_timestamp)).total_seconds()
                if age > self.settings.quote_freshness_seconds:
                    reasons.append("QUOTE_STALE")
                    explanations.append(f"Quote source age {age:.0f}s exceeds limit.")
                if quote.spread is not None and quote.spread > self.settings.max_spread_usd:
                    reasons.append("SPREAD_TOO_WIDE")
                    explanations.append(f"Spread {quote.spread} exceeds {self.settings.max_spread_usd}.")
        else:
            if quote.reference_price <= 0:
                reasons.append("REFERENCE_PRICE_INVALID")
                explanations.append("Reference simulation requires a positive genuine provider reference price.")
            received_age = (now - quote.received_timestamp).total_seconds()
            if received_age > 30:
                reasons.append("REFERENCE_RESPONSE_STALE")
                explanations.append(f"Reference response was received {received_age:.0f}s ago.")
            if latest_closed_1m_at is None:
                reasons.append("ONE_MINUTE_FRESHNESS_UNKNOWN")
                explanations.append("Reference simulation requires a recent completed 1m candle for sanity checking.")
            else:
                candle_age = (now - latest_closed_1m_at).total_seconds()
                if candle_age > 180:
                    reasons.append("ONE_MINUTE_DATA_STALE")
                    explanations.append(f"Latest completed 1m candle is {candle_age:.0f}s old.")

        approved = not reasons
        return RiskDecision(
            approved=approved,
            reason_codes=tuple(reasons),
            explanation=tuple(explanations),
            approved_at=now,
            expires_at=now + timedelta(seconds=30),
            plan_hash=plan.plan_hash,
        )
# ===== END engines/risk_engine.py =====


# ===== BEGIN engines/execution_engine.py =====

from datetime import datetime, timezone
from decimal import Decimal





def _utc(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

class PaperExecutionEngine:
    def __init__(self, settings, repository):
        self.settings = settings
        self.repository = repository

    def _fill_price(self, side: Side, quote, policy: QuotePolicy) -> Decimal:
        slip = self.settings.reference_slippage_usd
        if policy == QuotePolicy.STRICT_EXECUTABLE:
            if quote.bid is None or quote.ask is None:
                raise RuntimeError("BID_ASK_UNAVAILABLE")
            return quote.ask + slip if side == Side.BUY else quote.bid - slip
        half = self.settings.reference_assumed_spread_usd / Decimal("2")
        return quote.reference_price + half + slip if side == Side.BUY else quote.reference_price - half - slip

    def execute(self, account, plan, risk_decision, quote):
        now = datetime.now(timezone.utc)
        if not risk_decision.approved:
            raise RuntimeError("RISK_NOT_APPROVED")
        if risk_decision.plan_hash != plan.plan_hash or now > risk_decision.expires_at:
            raise RuntimeError("RISK_APPROVAL_EXPIRED_OR_MISMATCHED")
        # Revalidate account state, duplicate/capacity immediately before creation.
        current_account = self.repository.get_account(account.id)
        if current_account.kill_switch:
            raise RuntimeError("KILL_SWITCH")
        if not current_account.auto_paper_enabled:
            raise RuntimeError("AUTO_PAPER_DISABLED")
        opens = self.repository.open_positions(account.id)
        if len(opens) >= self.settings.max_open_positions:
            raise RuntimeError("MAX_OPEN_POSITIONS")
        if len([p for p in opens if p.source in ("OWN_SYSTEM", "RESEARCH_STRATEGY", "PAPER_EXPERIMENT")]) >= self.settings.max_own_positions:
            raise RuntimeError("MAX_OWN_POSITIONS")
        if any(p.side == plan.side.value for p in opens):
            raise RuntimeError("SAME_DIRECTION_OPEN")
        if self.repository.position_for_candidate(plan.candidate_id) is not None:
            raise RuntimeError("DUPLICATE_SETUP")

        fill = self._fill_price(plan.side, quote, plan.quote_policy)
        sl = plan.initial_sl
        R = abs(fill - sl)
        if R <= 0:
            raise RuntimeError("INVALID_STOP")
        if plan.side == Side.BUY and sl >= fill:
            raise RuntimeError("INVALID_STOP")
        if plan.side == Side.SELL and sl <= fill:
            raise RuntimeError("INVALID_STOP")
        mults = [Decimal(m) for m in plan.target_multipliers]
        targets = [fill + R*m if plan.side == Side.BUY else fill - R*m for m in mults]
        frozen_risk = R * self.settings.contract_oz_per_lot * self.settings.fixed_lot

        p = self.repository.create_position(
            account_id=account.id,
            candidate_id=plan.candidate_id,
            source=plan.source,
            side=plan.side.value,
            quote_policy=plan.quote_policy.value,
            entry=fill,
            sl_initial=sl,
            sl_current=sl,
            pending_sl=None,
            pending_sl_effective_at=None,
            tp1=targets[0], tp2=targets[1], tp3=targets[2], tp4=targets[3], tp5=targets[4],
            original_lot=self.settings.fixed_lot,
            remaining_lot=self.settings.fixed_lot,
            frozen_initial_risk_usd=frozen_risk,
            realized_pnl=Decimal("0"),
            status="OPEN",
            tp1_hit=False, tp2_hit=False, tp3_hit=False, tp4_hit=False, tp5_hit=False,
            opened_at=now, closed_at=None, last_processed_market_timestamp=None,
        )
        self.repository.add_event(
            p.id, f"position:{p.id}:OPEN", "OPEN", now, price=fill, quantity=self.settings.fixed_lot,
            details={
                "quote_policy": plan.quote_policy.value,
                "reference_price": str(quote.reference_price),
                "source": plan.source,
                "target_multipliers": [str(x) for x in plan.target_multipliers],
            }
        )
        return p

    def _pnl(self, side: str, entry: Decimal, exit_price: Decimal, qty: Decimal) -> Decimal:
        direction = Decimal("1") if side == "BUY" else Decimal("-1")
        return (exit_price - entry) * direction * self.settings.contract_oz_per_lot * qty

    def process_closed_bar(self, position_id: int, bar_open_time, bar_close_time, o, h, l, c):
        p = self.repository.get_position(position_id)
        if p is None or p.status != "OPEN":
            return
        if p.last_processed_market_timestamp is not None and _utc(bar_close_time) <= _utc(p.last_processed_market_timestamp):
            return
        o, h, l, c = map(lambda x: Decimal(str(x)), [o,h,l,c])
        sl = Decimal(p.sl_current)
        pending_sl = Decimal(p.pending_sl) if p.pending_sl is not None else None
        if pending_sl is not None and p.pending_sl_effective_at is not None and _utc(bar_open_time) >= _utc(p.pending_sl_effective_at):
            # Stops never loosen.
            if (p.side == "BUY" and pending_sl > sl) or (p.side == "SELL" and pending_sl < sl):
                sl = pending_sl
                self.repository.add_event(p.id, f"{p.id}:{bar_open_time}:SL_EFFECTIVE", "SL_EFFECTIVE", bar_open_time, price=sl)
            self.repository.update_position(p.id, sl_current=sl, pending_sl=None, pending_sl_effective_at=None)
            p = self.repository.get_position(p.id)

        # Conservative stop-first convention when both stop and target are inside one bar.
        stop_touched = l <= sl if p.side == "BUY" else h >= sl
        if stop_touched:
            gap_worse = (p.side == "BUY" and o < sl) or (p.side == "SELL" and o > sl)
            exit_price = o if gap_worse else sl
            exit_price += (-1 if p.side == "BUY" else 1) * (self.settings.reference_assumed_spread_usd / 2 + self.settings.reference_slippage_usd)
            qty = Decimal(p.remaining_lot)
            pnl = self._pnl(p.side, Decimal(p.entry), exit_price, qty)
            total = Decimal(p.realized_pnl) + pnl
            self.repository.add_event(p.id, f"{p.id}:{bar_close_time}:STOP", "STOP", bar_close_time, price=exit_price, quantity=qty, pnl=pnl, details={"stop_first_convention": True, "gap_fill": gap_worse})
            self.repository.update_position(p.id, status="CLOSED", remaining_lot=Decimal("0"), realized_pnl=total, closed_at=bar_close_time, last_processed_market_timestamp=bar_close_time)
            return

        def touched(tp):
            tp = Decimal(tp)
            return h >= tp if p.side == "BUY" else l <= tp

        updates = {"last_processed_market_timestamp": bar_close_time}
        realized = Decimal(p.realized_pnl)
        remaining = Decimal(p.remaining_lot)
        flags = {i: getattr(p, f"tp{i}_hit") for i in range(1,6)}
        targets = {i: Decimal(getattr(p, f"tp{i}")) for i in range(1,6)}

        for i in range(1,6):
            if flags[i] or not touched(targets[i]):
                continue
            flags[i] = True
            updates[f"tp{i}_hit"] = True
            if i == 1:
                # Amendment becomes effective at next candle boundary.
                updates["pending_sl"] = targets[1]
                updates["pending_sl_effective_at"] = bar_close_time
                self.repository.add_event(p.id, f"{p.id}:{bar_close_time}:TP1", "TP1", bar_close_time, price=targets[1], details={"pending_sl": str(targets[1]), "effective_at": str(bar_close_time)})
            elif i == 2:
                self.repository.add_event(p.id, f"{p.id}:{bar_close_time}:TP2", "TP2", bar_close_time, price=targets[2])
            elif i == 3:
                qty = Decimal("0.015")
                qty = min(qty, remaining)
                pnl = self._pnl(p.side, Decimal(p.entry), targets[3] + (-1 if p.side == "BUY" else 1)*(self.settings.reference_assumed_spread_usd/2+self.settings.reference_slippage_usd), qty)
                realized += pnl
                remaining -= qty
                self.repository.add_event(p.id, f"{p.id}:{bar_close_time}:TP3", "TP3_PARTIAL", bar_close_time, price=targets[3], quantity=qty, pnl=pnl)
            elif i == 4:
                updates["pending_sl"] = targets[3]
                updates["pending_sl_effective_at"] = bar_close_time
                self.repository.add_event(p.id, f"{p.id}:{bar_close_time}:TP4", "TP4", bar_close_time, price=targets[4], details={"pending_sl": str(targets[3]), "effective_at": str(bar_close_time)})
            elif i == 5:
                qty = remaining
                pnl = self._pnl(p.side, Decimal(p.entry), targets[5] + (-1 if p.side == "BUY" else 1)*(self.settings.reference_assumed_spread_usd/2+self.settings.reference_slippage_usd), qty)
                realized += pnl
                remaining = Decimal("0")
                updates.update(status="CLOSED", closed_at=bar_close_time)
                self.repository.add_event(p.id, f"{p.id}:{bar_close_time}:TP5", "TP5_CLOSE", bar_close_time, price=targets[5], quantity=qty, pnl=pnl)

        updates["remaining_lot"] = remaining
        updates["realized_pnl"] = realized
        self.repository.update_position(p.id, **updates)

    def replay_bars(self, position_id: int, one_min_df):
        p = self.repository.get_position(position_id)
        if p is None or p.status != "OPEN":
            return
        for ts, row in one_min_df.iterrows():
            close_time = ts.to_pydatetime()
            # Twelve Data datetime is treated as bar open time after timezone=UTC; use +1m as close.
            from datetime import timedelta
            bar_open = close_time
            bar_close = close_time + timedelta(minutes=1)
            if _utc(bar_open) < _utc(p.opened_at):
                continue
            self.process_closed_bar(p.id, bar_open, bar_close, row.open, row.high, row.low, row.close)
            p = self.repository.get_position(p.id)
            if p.status != "OPEN":
                break
# ===== END engines/execution_engine.py =====


# ===== BEGIN engines/performance_engine.py =====
from decimal import Decimal


def summarize(positions):
    closed = [p for p in positions if p.status == "CLOSED"]
    wins = [p for p in closed if Decimal(p.realized_pnl) > 0]
    losses = [p for p in closed if Decimal(p.realized_pnl) < 0]
    net = sum((Decimal(p.realized_pnl) for p in closed), Decimal("0"))
    gross_profit = sum((Decimal(p.realized_pnl) for p in wins), Decimal("0"))
    gross_loss = -sum((Decimal(p.realized_pnl) for p in losses), Decimal("0"))
    if not closed:
        win_rate = None
    else:
        win_rate = 100 * len(wins) / len(closed)
    if gross_loss == 0:
        profit_factor = None if gross_profit == 0 else float("inf")
    else:
        profit_factor = float(gross_profit / gross_loss)
    rs = []
    for p in closed:
        risk = Decimal(p.frozen_initial_risk_usd)
        if risk > 0:
            rs.append(float(Decimal(p.realized_pnl) / risk))
    return {
        "positions": len(positions),
        "closed": len(closed),
        "open": len([p for p in positions if p.status == "OPEN"]),
        "win_rate": win_rate,
        "net_pnl": float(net),
        "average_realized_r": (sum(rs) / len(rs)) if rs else None,
        "profit_factor": profit_factor,
    }
# ===== END engines/performance_engine.py =====


# ===== BEGIN connectors/twelve_data.py =====

from datetime import datetime, timezone
from decimal import Decimal
import time

import pandas as pd
import requests
from pathlib import Path
import os



class TwelveDataError(RuntimeError):
    pass


class TwelveDataClient:
    BASE_URL = "https://api.twelvedata.com"

    def __init__(self, api_key: str, symbol: str = "XAU/USD", timeout: int = 15):
        self.api_key = api_key
        self.symbol = symbol
        self.timeout = timeout
        self.session = requests.Session()

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def _get(self, endpoint: str, params: dict, retries: int = 5) -> dict:
        if not self.api_key:
            raise TwelveDataError("TWELVEDATA_API_KEY is not configured")

        payload = dict(params)
        payload["apikey"] = self.api_key
        last_message = "Unknown Twelve Data error"

        for attempt in range(retries + 1):
            try:
                r = self.session.get(
                    f"{self.BASE_URL}/{endpoint}",
                    params=payload,
                    timeout=self.timeout,
                )

                api_message = ""
                parsed = None
                try:
                    parsed = r.json()
                    if isinstance(parsed, dict):
                        api_message = str(parsed.get("message") or parsed.get("code") or "")
                except Exception:
                    parsed = None

                if r.status_code == 429 or (isinstance(parsed, dict) and str(parsed.get("code")) == "429"):
                    retry_after = r.headers.get("Retry-After")
                    try:
                        wait_s = float(retry_after) if retry_after else 0.0
                    except Exception:
                        try:
                            from email.utils import parsedate_to_datetime
                            wait_s = max(0., (parsedate_to_datetime(retry_after) - datetime.now(timezone.utc)).total_seconds())
                        except Exception:
                            wait_s = 0.0
                    if wait_s > 60:
                        raise TwelveDataError(f"Rate limited: Retry-After is {wait_s:.0f}s; retry research later. Successful chunks remain cached.")
                    wait_s = max(wait_s, min(60.0, 10.0 + attempt * 8.0))
                    last_message = (
                        "Twelve Data rate limit reached (HTTP 429). "
                        f"Retrying after {wait_s:.0f}s."
                    )
                    if attempt >= retries:
                        break
                    time.sleep(wait_s)
                    continue

                if r.status_code in (401, 403):
                    raise TwelveDataError(
                        f"Twelve Data authorization failed (HTTP {r.status_code}). "
                        "Check TWELVEDATA_API_KEY in Streamlit Secrets."
                    )

                if r.status_code >= 500:
                    last_message = f"Twelve Data temporary server error (HTTP {r.status_code})."
                    if attempt >= retries:
                        break
                    time.sleep(min(20.0, 2.0 * (attempt + 1)))
                    continue

                if r.status_code >= 400:
                    safe_msg = ""
                    raise TwelveDataError(
                        f"Twelve Data request failed (HTTP {r.status_code}){safe_msg}"
                    )

                data = parsed if isinstance(parsed, dict) else r.json()
                if isinstance(data, dict) and data.get("status") == "error":
                    raise TwelveDataError(
                        "Twelve Data returned an API error; check plan, symbol and credits."
                    )
                return data

            except TwelveDataError:
                raise
            except requests.RequestException as exc:
                last_message = f"Twelve Data network error: {type(exc).__name__}"
                if attempt >= retries:
                    break
                time.sleep(min(15.0, 1.5 * (attempt + 1)))
            except ValueError:
                last_message = "Twelve Data returned malformed JSON."
                if attempt >= retries:
                    break
                time.sleep(1.0)

        raise TwelveDataError(last_message)

    def fetch_candles(self, interval: str, outputsize: int = 420) -> pd.DataFrame:
        data = self._get("time_series", {
            "symbol": self.symbol,
            "interval": interval,
            "outputsize": int(outputsize),
            "timezone": "UTC",
            "order": "ASC",
            "format": "JSON",
        })
        rows = data.get("values") or []
        if not rows:
            raise TwelveDataError(f"No candle data returned for {self.symbol} {interval}")
        df = pd.DataFrame(rows)
        required = ["datetime", "open", "high", "low", "close"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise TwelveDataError(f"Malformed candle response; missing {missing}")
        df["datetime"] = pd.to_datetime(df["datetime"], utc=True, errors="coerce")
        for c in ["open", "high", "low", "close"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df = df.dropna(subset=required).drop_duplicates("datetime").sort_values("datetime")
        invalid = (df[["open", "high", "low", "close"]] <= 0).any(axis=1) | (df["high"] < df["low"])
        if invalid.any():
            raise TwelveDataError(f"Rejected {int(invalid.sum())} invalid OHLC rows")
        if "volume" in df:
            df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
        return df.set_index("datetime")

    def fetch_candles_range(
        self,
        interval: str,
        start_at,
        end_at,
        *,
        rate_limit_safe: bool = False,
    ) -> pd.DataFrame:
        start = pd.Timestamp(start_at)
        end = pd.Timestamp(end_at)
        if start.tzinfo is None:
            start = start.tz_localize("UTC")
        else:
            start = start.tz_convert("UTC")
        if end.tzinfo is None:
            end = end.tz_localize("UTC")
        else:
            end = end.tz_convert("UTC")
        if end <= start:
            raise TwelveDataError("Invalid research date range.")

        chunk_days = {
            "5min": 14,
            "15min": 45,
            "30min": 85,
            "1h": 180,
        }.get(interval, 30)

        cache_dir = Path("/tmp/gold_v64_td_history_cache")
        if rate_limit_safe:
            cache_dir.mkdir(parents=True, exist_ok=True)

        frames = []
        cur = start

        while cur < end:
            nxt = min(cur + pd.Timedelta(days=chunk_days), end)
            part = None
            cache_file = None

            if rate_limit_safe:
                import hashlib as _hashlib
                raw_key = f"{self.symbol}|{interval}|{cur.isoformat()}|{nxt.isoformat()}"
                digest = _hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:24]
                cache_file = cache_dir / f"{interval}_{digest}.csv"

            if cache_file is not None and cache_file.exists():
                try:
                    cached = pd.read_csv(cache_file)
                    cached["datetime"] = pd.to_datetime(
                        cached["datetime"], utc=True, errors="coerce"
                    )
                    for c in ["open", "high", "low", "close"]:
                        cached[c] = pd.to_numeric(cached[c], errors="coerce")
                    cached = cached.dropna(
                        subset=["datetime", "open", "high", "low", "close"]
                    )
                    if not cached.empty:
                        part = cached[["datetime", "open", "high", "low", "close"]]
                except Exception:
                    part = None

            if part is None:
                data = self._get(
                    "time_series",
                    {
                        "symbol": self.symbol,
                        "interval": interval,
                        "outputsize": 5000,
                        "start_date": cur.strftime("%Y-%m-%d %H:%M:%S"),
                        "end_date": nxt.strftime("%Y-%m-%d %H:%M:%S"),
                        "timezone": "UTC",
                        "order": "ASC",
                        "format": "JSON",
                    },
                    retries=6 if rate_limit_safe else 3,
                )
                rows = data.get("values") or []
                if rows:
                    part = pd.DataFrame(rows)
                    required = ["datetime", "open", "high", "low", "close"]
                    missing = [c for c in required if c not in part.columns]
                    if missing:
                        raise TwelveDataError(
                            f"Malformed historical candle response; missing {missing}"
                        )
                    part["datetime"] = pd.to_datetime(
                        part["datetime"], utc=True, errors="coerce"
                    )
                    for c in ["open", "high", "low", "close"]:
                        part[c] = pd.to_numeric(part[c], errors="coerce")
                    part = part.dropna(subset=required)[required]

                    if cache_file is not None and not part.empty:
                        try:
                            part.to_csv(cache_file, index=False)
                        except Exception:
                            pass

                if rate_limit_safe and nxt < end:
                    time.sleep(8.5)

            if part is not None and not part.empty:
                frames.append(part)

            cur = nxt

        if not frames:
            raise TwelveDataError(
                f"No historical candle data returned for {self.symbol} {interval}"
            )

        df = pd.concat(frames, ignore_index=True)
        df = df.drop_duplicates("datetime").sort_values("datetime")
        invalid = (
            (df[["open", "high", "low", "close"]] <= 0).any(axis=1)
            | (df["high"] < df["low"])
        )
        if invalid.any():
            df = df.loc[~invalid].copy()
        if df.empty:
            raise TwelveDataError(
                f"All historical rows were invalid for {self.symbol} {interval}"
            )
        return df.set_index("datetime")

    def fetch_reference_quote(self) -> Quote:
        received = datetime.now(timezone.utc)
        data = self._get("price", {"symbol": self.symbol})
        if "price" not in data:
            raise TwelveDataError("Price endpoint returned no price")
        price = Decimal(str(data["price"]))
        if price <= 0:
            raise TwelveDataError("Nonpositive reference price")
        # /price does not provide a verified executable bid/ask pair here.
        return Quote(
            symbol=self.symbol,
            reference_price=price,
            bid=None,
            ask=None,
            source_timestamp=None,
            received_timestamp=received,
            source="TWELVE_DATA",
            price_type="REFERENCE",
            quality_flags=("BID_ASK_UNAVAILABLE", "SOURCE_TIMESTAMP_UNAVAILABLE"),
        )
# ===== END connectors/twelve_data.py =====


# ===== BEGIN connectors/tradingview.py =====
def advanced_chart_html(symbol: str = "FXPRO:XAUUSD", interval: str = "1") -> str:
    # Fixed-height TradingView embed for tablets.
    # Do not rely on autosize here: in Streamlit component iframes it can collapse
    # to a short chart while leaving blank space below.
    return f"""
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        html, body {{
          margin: 0 !important;
          padding: 0 !important;
          width: 100% !important;
          height: 100% !important;
          min-height: 850px !important;
          overflow: hidden !important;
          background: #0e1117;
        }}
        #tv-wrapper {{
          width: 100% !important;
          height: 850px !important;
          min-height: 850px !important;
          display: block !important;
        }}
        .tradingview-widget-container {{
          width: 100% !important;
          height: 850px !important;
          min-height: 850px !important;
        }}
        .tradingview-widget-container__widget {{
          width: 100% !important;
          height: 850px !important;
          min-height: 850px !important;
        }}
        .tradingview-widget-container iframe {{
          width: 100% !important;
          height: 850px !important;
          min-height: 850px !important;
        }}
      </style>
    </head>
    <body>
      <div id="tv-wrapper">
        <div class="tradingview-widget-container">
          <div class="tradingview-widget-container__widget"></div>
          <script
            type="text/javascript"
            src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js"
            async>
          {{
            "width": "100%",
            "height": 850,
            "autosize": false,
            "symbol": "{symbol}",
            "interval": "{interval}",
            "timezone": "Etc/UTC",
            "theme": "dark",
            "style": "1",
            "locale": "en",
            "allow_symbol_change": false,
            "calendar": true,
            "hide_side_toolbar": false,
            "hide_top_toolbar": false,
            "hide_legend": false,
            "hide_volume": false,
            "withdateranges": true,
            "save_image": false,
            "support_host": "https://www.tradingview.com"
          }}
          </script>
        </div>
      </div>
    </body>
    </html>
    """
# ===== END connectors/tradingview.py =====


# ===== BEGIN ui/charts.py =====

import plotly.graph_objects as go


def backend_candlestick(df, plan=None, patterns=()):
    view = df.tail(140)
    fig = go.Figure(data=[go.Candlestick(
        x=view.index,
        open=view["open"], high=view["high"], low=view["low"], close=view["close"],
        name="XAU/USD backend"
    )])
    # Important levels only; keep plot readable.
    seen = set()
    for p in patterns:
        if p.level is None or p.pattern_type not in {"SUPPORT", "RESISTANCE", "BOS", "CHOCH"}:
            continue
        key = (p.pattern_type, round(float(p.level), 2))
        if key in seen:
            continue
        seen.add(key)
        fig.add_hline(y=float(p.level), line_dash="dot", annotation_text=f"{p.pattern_type} {float(p.level):.2f}")
    if plan:
        fig.add_hline(y=float(plan.entry_reference), annotation_text="Entry ref")
        fig.add_hline(y=float(plan.initial_sl), line_dash="dash", annotation_text="SL")
        for i, tp in enumerate(plan.provisional_targets, 1):
            fig.add_hline(y=float(tp), line_dash="dot", annotation_text=f"TP{i}")
    fig.update_layout(height=900, xaxis_rangeslider_visible=False, margin=dict(l=10,r=10,t=25,b=10), legend_orientation="h")
    return fig
# ===== END ui/charts.py =====



def live_strategy_frames(frames: dict, timeframe: str):
    tf = str(timeframe or "15m")
    if tf == "5m":
        return frames["5m"], frames["1h"], 60
    if tf == "15m":
        return frames["15m"], frames["1h"], 60
    if tf == "30m":
        primary = resample_ohlc_strict(frames["15m"], "30min", 2)
        return primary, frames["1h"], 60
    if tf == "1h":
        context = resample_ohlc_strict(frames["1h"], "4h", 4)
        return frames["1h"], context, 240
    raise ValueError(f"Unsupported active strategy timeframe: {tf}")

# ===== BEGIN services/core_service.py =====

from datetime import datetime, timezone, timedelta
from decimal import Decimal
import hashlib



def _closed_only(df, minutes: int):
    now = datetime.now(timezone.utc)
    close_times = df.index + timedelta(minutes=minutes)
    return df.loc[close_times <= now].copy()


class CoreService:
    def __init__(self, settings):
        self.settings = settings
        self.engine = create_db_engine(settings.database_url)
        init_database(self.engine)
        self.sessions = make_session_factory(self.engine)
        self.repo = TradingRepository(self.sessions)
        self.account = self.repo.ensure_account(equity=Decimal("2500"))
        self.market = TwelveDataClient(settings.twelve_data_api_key, settings.symbol)
        self.risk = RiskEngine(settings, self.repo)
        self.execution = PaperExecutionEngine(settings, self.repo)

    def set_account_controls(self, equity: Decimal, auto_paper: bool, kill_switch: bool):
        self.account = self.repo.update_account(self.account.id, equity=equity, auto_paper_enabled=auto_paper, kill_switch=kill_switch)

    def fetch_market(self):
        quote = self.market.fetch_reference_quote()
        frames = {
            "1m": _closed_only(self.market.fetch_candles("1min", 500), 1),
            "5m": _closed_only(self.market.fetch_candles("5min", 420), 5),
            "15m": _closed_only(self.market.fetch_candles("15min", 420), 15),
            "1h": _closed_only(self.market.fetch_candles("1h", 420), 60),
        }
        self.repo.save_market_snapshot(quote)
        return quote, frames

    def analyze(self, frames):
        missing = []
        by_tf = {}
        all_patterns = []
        for key in ["5m", "15m", "1h"]:
            df = frames.get(key)
            if df is None or len(df) < 200:
                missing.append(f"{key}: need >=200 valid candles")
                continue
            by_tf[key] = timeframe_snapshot(df)
            all_patterns.extend(detect_patterns(df, key))
        latest_1m = None
        if "1m" in frames and not frames["1m"].empty:
            latest_1m = frames["1m"].index[-1].to_pydatetime() + timedelta(minutes=1)
        return AnalysisBundle(by_timeframe=by_tf, patterns=tuple(all_patterns), latest_closed_1m_at=latest_1m, complete=(len(missing)==0), missing=tuple(missing))

    def fetch_research_history(self, train_days: int = 90, oos_days: int = 90):
        end = pd.Timestamp.now(tz="UTC").floor("min")
        oos_start = end - pd.Timedelta(days=int(oos_days))
        train_start = oos_start - pd.Timedelta(days=int(train_days))
        fetch_start = train_start - pd.Timedelta(days=10)  # warm-up for EMA/ADX features

        primary = self.market.fetch_candles_range("15min", fetch_start, end)
        h1 = self.market.fetch_candles_range("1h", fetch_start, end)
        primary = _closed_only(primary, 15)
        h1 = _closed_only(h1, 60)
        return primary, h1, train_start, oos_start, end

    def run_strategy_research(
        self,
        *,
        train_days: int = 90,
        oos_days: int = 90,
        target_return: float = 15.0,
        max_dd: float = 15.0,
        min_trades: int = 12,
        intensity: str = "Quick",
        include_macro: bool = True,
    ):
        primary, h1, train_start, oos_start, end = self.fetch_research_history(train_days, oos_days)
        x, macro_notes = build_research_features(primary, h1, include_macro=include_macro)
        train = x[(x.index >= train_start) & (x.index < oos_start)].copy()
        test = x[(x.index >= oos_start) & (x.index <= end)].copy()
        if len(train) < 1000 or len(test) < 1000:
            raise RuntimeError(f"Not enough research bars. Train={len(train)}, OOS={len(test)}")

        cost = CostModel(
            spread_usd_per_oz=float(self.settings.reference_assumed_spread_usd),
            slippage_each_side_usd_per_oz=float(self.settings.reference_slippage_usd),
        )
        rule_results, rule_details = run_rule_research_v6(train, test, cost, intensity)
        ml_results, ml_details = run_ml_research_v6(train, test, cost)
        results = pd.concat([rule_results, ml_results], ignore_index=True)
        ranked = rank_research_results(results, target_return, min_trades, max_dd)
        return {
            "results": ranked,
            "details": {**rule_details, **ml_details},
            "train_start": train.index.min(),
            "train_end": train.index.max(),
            "oos_start": test.index.min(),
            "oos_end": test.index.max(),
            "macro_notes": macro_notes,
            "train_bars": len(train),
            "oos_bars": len(test),
        }


    def _derive_deep_timeframes(self, base_tf: str, base_df: pd.DataFrame, requested):
        base_minutes = DEEP_MINUTES[base_tf]
        out = {base_tf: base_df}

        for tf in requested:
            if tf == base_tf:
                continue
            target_minutes = DEEP_MINUTES[tf]
            if target_minutes < base_minutes or target_minutes % base_minutes != 0:
                continue
            expected = target_minutes // base_minutes
            rule = {"15m": "15min", "30m": "30min", "1h": "1h"}[tf]
            out[tf] = resample_ohlc_strict(base_df, rule, expected)

        if "1h" not in out and base_minutes < 60 and 60 % base_minutes == 0:
            out["1h"] = resample_ohlc_strict(base_df, "1h", 60 // base_minutes)
        return out

    def fetch_deep_research_history(
        self,
        train_days: int = 120,
        oos_days: int = 90,
        timeframes=("5m","15m","30m","1h"),
    ):
        end = pd.Timestamp.now(tz="UTC").floor("min")
        oos_start = end - pd.Timedelta(days=int(oos_days))
        train_start = oos_start - pd.Timedelta(days=int(train_days))
        fetch_start = train_start - pd.Timedelta(days=35)

        requested = [tf for tf in timeframes if tf in DEEP_PRIMARY_TFS]
        if not requested:
            raise RuntimeError("No valid deep-research timeframe selected.")

        requested = sorted(requested, key=lambda x: DEEP_MINUTES[x])
        base_tf = requested[0]
        errors = {}

        try:
            base_df = self.market.fetch_candles_range(
                DEEP_INTERVALS[base_tf],
                fetch_start,
                end,
                rate_limit_safe=True,
            )
            base_df = _closed_only(base_df, DEEP_MINUTES[base_tf])
            datasets = self._derive_deep_timeframes(base_tf, base_df, requested)
        except Exception as exc:
            raise RuntimeError(
                f"Deep-history download failed for base timeframe {base_tf}: "
                f"{type(exc).__name__}: {exc}"
            )

        datasets = {
            tf: df for tf, df in datasets.items()
            if df is not None and not df.empty
        }

        available = [tf for tf in requested if tf in datasets]
        for tf in requested:
            if tf not in datasets:
                errors[tf] = f"Could not derive {tf} from base timeframe {base_tf}."

        if not available:
            raise RuntimeError("No requested deep-research timeframe could be produced.")

        return datasets, available, errors, train_start, oos_start, end

    def run_deep_strategy_research(
        self,
        *,
        train_days: int = 120,
        oos_days: int = 90,
        target_return: float = 15.0,
        max_dd: float = 15.0,
        min_trades: int = 12,
        timeframes=("5m","15m","30m","1h"),
        finalists_per_family: int = 2,
        folds: int = 4,
        include_ml_benchmark: bool = True,
        include_macro_ml: bool = False,
    ):
        datasets, available, errors, train_start, oos_start, end = self.fetch_deep_research_history(
            train_days, oos_days, timeframes
        )
        cost = CostModel(
            spread_usd_per_oz=float(self.settings.reference_assumed_spread_usd),
            slippage_each_side_usd_per_oz=float(self.settings.reference_slippage_usd),
        )

        selection_rows = []
        selection_details = {}
        frames_by_tf = {}
        notes_by_tf = {}

        for tf in available:
            primary = datasets[tf]
            if tf == "1h":
                context = resample_ohlc_strict(datasets["1h"], "4h", 4)
                context_minutes = 240
            else:
                context = datasets["1h"]
                context_minutes = 60

            x, notes = build_deep_features(
                primary, context, context_minutes,
                include_macro=bool(include_macro_ml and tf == "15m")
            )
            train = x[(x.index >= train_start) & (x.index < oos_start)].copy()
            test = x[(x.index >= oos_start) & (x.index <= end)].copy()

            if len(train) < 800 or len(test) < 300:
                errors[tf] = f"Insufficient usable bars after features: train={len(train)}, oos={len(test)}"
                continue

            rows, details = run_deep_rule_selection(
                train, cost, tf,
                finalists_per_family=finalists_per_family,
                folds=folds,
            )
            if rows is not None and not rows.empty:
                selection_rows.append(rows)
                selection_details[tf] = details
                frames_by_tf[tf] = {"train":train, "test":test}
                notes_by_tf[tf] = notes

        if not selection_rows:
            raise RuntimeError("Deep research produced no deterministic strategy candidates. " + str(errors))

        selection = deep_selection_rank(pd.concat(selection_rows, ignore_index=True))
        selected = selection.iloc[0]
        selected_tf = str(selected["timeframe"])
        final = evaluate_deep_final_oos(
            selected,
            frames_by_tf[selected_tf]["test"],
            cost,
            target_return,
            min_trades,
            max_dd,
        )

        ml_benchmark = pd.DataFrame()
        if include_ml_benchmark and "15m" in frames_by_tf:
            try:
                ml_benchmark = internal_ml_benchmark(frames_by_tf["15m"]["train"], cost)
            except Exception:
                ml_benchmark = pd.DataFrame()

        return {
            "selection_results": selection,
            "selected_final": final,
            "ml_benchmark": ml_benchmark,
            "available_timeframes": available,
            "timeframe_errors": errors,
            "train_start": train_start,
            "train_end": oos_start,
            "oos_start": oos_start,
            "oos_end": end,
            "notes_by_tf": notes_by_tf,
            "selection_candidate_count": int(len(selection)),
        }

    def run_robust_strategy_research(
        self,
        *,
        research_days: int = 275,
        oos_days: int = 90,
        target_return: float = 15.0,
        max_dd: float = 15.0,
        min_trades: int = 12,
        timeframes=("15m", "30m", "1h"),
        finalists_per_family: int = 1,
        outer_folds: int = 4,
        inner_folds: int = 3,
        include_ml_benchmark: bool = True,
        include_macro_ml: bool = False,
    ):
        datasets, available, errors, train_start, oos_start, end = self.fetch_deep_research_history(
            research_days, oos_days, timeframes
        )
        cost = CostModel(
            spread_usd_per_oz=float(self.settings.reference_assumed_spread_usd),
            slippage_each_side_usd_per_oz=float(self.settings.reference_slippage_usd),
        )

        selection_rows = []
        frames_by_tf = {}
        notes_by_tf = {}

        for tf in available:
            primary = datasets[tf]
            if tf == "1h":
                context = resample_ohlc_strict(datasets["1h"], "4h", 4)
                context_minutes = 240
            else:
                context = datasets["1h"]
                context_minutes = 60

            x, notes = build_deep_features(
                primary,
                context,
                context_minutes,
                include_macro=bool(include_macro_ml and tf == "15m"),
            )
            train = x[(x.index >= train_start) & (x.index < oos_start)].copy()
            test = x[(x.index >= oos_start) & (x.index <= end)].copy()

            if len(train) < 1200 or len(test) < 300:
                errors[tf] = (
                    f"Insufficient usable bars after features: "
                    f"train={len(train)}, oos={len(test)}"
                )
                continue

            rows, _ = run_nested_family_selection(
                train,
                cost,
                tf,
                outer_folds=outer_folds,
                inner_folds=inner_folds,
                finalists_per_family=finalists_per_family,
            )
            if rows is not None and not rows.empty:
                selection_rows.append(rows)
                frames_by_tf[tf] = {"train": train, "test": test}
                notes_by_tf[tf] = notes

        if not selection_rows:
            raise RuntimeError(
                "Robust research produced no deterministic candidates. "
                + str(errors)
            )

        selection = robust_selection_rank(
            pd.concat(selection_rows, ignore_index=True)
        )
        selected = selection.iloc[0]
        selected_tf = str(selected["timeframe"])

        final = evaluate_robust_final_oos(
            selected,
            frames_by_tf[selected_tf]["test"],
            cost,
            target_return,
            min_trades,
            max_dd,
        )

        ml_benchmark = pd.DataFrame()
        if include_ml_benchmark and "15m" in frames_by_tf:
            try:
                ml_benchmark = internal_ml_benchmark(
                    frames_by_tf["15m"]["train"], cost
                )
            except Exception:
                ml_benchmark = pd.DataFrame()

        return {
            "selection_results": selection,
            "selected_final": final,
            "ml_benchmark": ml_benchmark,
            "available_timeframes": available,
            "timeframe_errors": errors,
            "train_start": train_start,
            "train_end": oos_start,
            "oos_start": oos_start,
            "oos_end": end,
            "notes_by_tf": notes_by_tf,
            "selection_candidate_count": int(len(selection)),
            "method": "V6.3_NESTED_WALKFORWARD_REGIME_SINGLE_HOLDOUT",
            "total_days": int(research_days + oos_days),
        }

    def _active_strategy_payload(self):
        obj = self.repo.get_active_strategy()
        if obj is None:
            return None
        try:
            params = json.loads(obj.params_json or "{}")
        except Exception:
            params = {}
        try:
            metrics = json.loads(obj.metrics_json or "{}")
        except Exception:
            metrics = {}
        return {
            "family": obj.family,
            "params": params,
            "metrics": metrics,
            "gate_pass": bool(obj.gate_pass),
            "activated_at": obj.activated_at,
            "updated_at": obj.updated_at,
        }

    def _research_candidate_id(self, primary_frame, timeframe: str, family: str, side: Side, active):
        mins = DEEP_MINUTES.get(str(timeframe), 15)
        anchor = (
            (primary_frame.index[-1].to_pydatetime() + timedelta(minutes=mins)).isoformat()
            if primary_frame is not None and not primary_frame.empty
            else datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")
        )
        activation = str(active.get("updated_at"))
        raw = f"RESEARCH_STRATEGY|{timeframe}|{family}|{side.value}|{anchor}|{activation}|v6.3-robust"
        return hashlib.sha256(raw.encode()).hexdigest()

    def run_once(self, *, allow_execution: bool):
        quote, frames = self.fetch_market()

        # Protective management always continues for existing paper positions.
        for p in self.repo.open_positions(self.account.id):
            self.execution.replay_bars(p.id, frames["1m"])

        bundle = self.analyze(frames)
        core_evaluation = evaluate(bundle)

        active = self._active_strategy_payload()
        strategy_signal = 0
        strategy_eval = None
        cid = None
        plan = None
        risk_decision = None
        position = None

        if active and active["family"] in STRATEGIES:
            active_tf = str(active["params"].get("_timeframe", "15m"))
            primary_live, context_live, context_minutes = live_strategy_frames(frames, active_tf)
            strategy_signal, research_frame = current_rule_signal(
                active["family"], active["params"], primary_live, context_live, context_minutes
            )
            if strategy_signal != 0 and research_frame is not None and len(research_frame):
                side = Side.BUY if strategy_signal > 0 else Side.SELL
                cid = self._research_candidate_id(primary_live, active_tf, active["family"], side, active)
                gate_pass = bool(active.get("gate_pass"))
                strategy_eval = SignalEvaluation(
                    side=side,
                    buy_index=100 if side == Side.BUY else 0,
                    sell_index=100 if side == Side.SELL else 0,
                    evidence_completeness=100,
                    setup_quality=85 if gate_pass else 60,
                    grade=Grade.A_PLUS if gate_pass else Grade.B,
                    status=CandidateStatus.APPROVED if gate_pass else CandidateStatus.WATCH_ONLY,
                    evidence=(),
                    reasons_for=(
                        f"Activated strategy {active['family']} ({active_tf}) generated {side.value}.",
                        f"Research gate: {'PASS' if gate_pass else 'EXPERIMENT'}",
                    ),
                    reasons_against=(
                        () if gate_pass
                        else ("The configured 15%/robustness research gate was not fully passed; this is PAPER forward testing only.",)
                    ),
                    evaluated_at=datetime.now(timezone.utc),
                )
                atr_value = Decimal(str(research_frame["atr14"].iloc[-1]))
                plan = build_research_trade_plan(
                    cid,
                    side,
                    quote.reference_price,
                    atr_value,
                    active["params"],
                    Decimal(self.account.equity),
                    self.settings.quote_policy,
                    self.settings.fixed_lot,
                    self.settings.contract_oz_per_lot,
                    gate_pass,
                )
                self.repo.save_candidate(cid, strategy_eval, plan, source="RESEARCH_STRATEGY")
                if plan is not None:
                    risk_decision = self.risk.assess(
                        self.account, plan, quote, bundle.latest_closed_1m_at
                    )
                    if allow_execution and risk_decision.approved:
                        position = self.execution.execute(
                            self.account, plan, risk_decision, quote
                        )

        return {
            "quote": quote,
            "frames": frames,
            "bundle": bundle,
            "evaluation": core_evaluation,
            "strategy_evaluation": strategy_eval,
            "active_strategy": active,
            "strategy_signal": strategy_signal,
            "candidate_id": cid,
            "plan": plan,
            "risk": risk_decision,
            "position": position,
        }
# ===== END services/core_service.py =====


# ===== BEGIN ui/dashboard.py =====

from decimal import Decimal
import json

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components



def _secrets_dict():
    try:
        return dict(st.secrets)
    except Exception:
        return {}


def _service(settings):
    return CoreService(settings)


def _money(v):
    if v is None:
        return "N/A"
    return f"${float(v):,.2f}"


def _render_snapshot(result, settings):
    q = result["quote"]
    core_ev = result["evaluation"]
    active = result.get("active_strategy")
    strategy_signal = int(result.get("strategy_signal") or 0)
    strategy_eval = result.get("strategy_evaluation")
    plan = result.get("plan")
    risk = result.get("risk")
    position = result.get("position")

    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Twelve Data reference", f"{float(q.reference_price):,.2f}")
    c2.metric("Bid", "N/A" if q.bid is None else f"{float(q.bid):,.2f}")
    c3.metric("Ask", "N/A" if q.ask is None else f"{float(q.ask):,.2f}")
    c4.metric("Core BUY index", core_ev.buy_index)
    c5.metric("Core SELL index", core_ev.sell_index)
    st.caption(
        f"Backend source: {q.source} | quote type: {q.price_type} | "
        f"flags: {', '.join(q.quality_flags) or 'none'}"
    )

    if active is None:
        st.warning(
            "No active research strategy. The app will analyze and manage existing paper positions, "
            "but it will not open a new strategy position."
        )
    else:
        sig_text = "BUY" if strategy_signal > 0 else "SELL" if strategy_signal < 0 else "NONE"
        gate_text = "RESEARCH GATE PASS" if active.get("gate_pass") else "UNVALIDATED PAPER EXPERIMENT"
        a,b,c,d = st.columns(4)
        a.metric("Active strategy", active.get("family","N/A"))
        b.metric("Strategy signal", sig_text)
        c.metric("Research status", gate_text)
        try:
            oos_ret = float(active.get("metrics",{}).get("oos_return_pct"))
            d.metric("Research OOS", f"{oos_ret:.2f}%")
        except Exception:
            d.metric("Research OOS", "N/A")

    if plan:
        st.markdown(f"### Strategy plan — {plan.side.value}")
        st.write(
            f"Entry reference **{float(plan.entry_reference):,.2f}** | "
            f"SL **{float(plan.initial_sl):,.2f}** | fixed PAPER size **0.03 lot**"
        )
        st.write(" | ".join([f"TP{i}: {float(x):,.2f}" for i,x in enumerate(plan.provisional_targets,1)]))
        st.write(
            f"Gross initial risk: **${float(plan.gross_risk_usd):,.2f}** "
            f"({float(plan.risk_pct):.2f}% equity)"
        )
        st.write("Quote policy:", plan.quote_policy.value)
        if strategy_eval is not None:
            st.caption(
                f"Operational source: RESEARCH_STRATEGY | "
                f"{'target gate PASS' if plan.research_authorized and strategy_eval.grade == Grade.A_PLUS else 'paper experiment'}"
            )
        if risk:
            if risk.approved:
                st.success("Risk/Data gates: APPROVED")
            else:
                st.warning("Execution blocked: " + ", ".join(risk.reason_codes))
                for line in risk.explanation:
                    st.caption("• " + line)
        if position is not None:
            st.success(f"PAPER position created: #{position.id}")
    elif active is not None:
        st.info("Active strategy has no BUY/SELL entry signal on its latest fully closed primary-timeframe bar.")

    with st.expander("Core directional context", expanded=False):
        x1,x2,x3 = st.columns(3)
        x1.metric("Evidence completeness", f"{core_ev.evidence_completeness}%")
        x2.metric("Setup quality", f"{core_ev.setup_quality}/100")
        x3.metric("Core grade", core_ev.grade.value)
        if core_ev.reasons_for:
            st.write("Reasons for:")
            for x in core_ev.reasons_for:
                st.write("+", x)
        if core_ev.reasons_against:
            st.write("Reasons against:")
            for x in core_ev.reasons_against:
                st.write("−", x)
# ===== END ui/dashboard.py =====


# ===== V6.4 regime-adaptive research and PAPER orchestration =====
REGIMES64 = ('TREND_UP', 'TREND_DOWN', 'RANGE', 'VOLATILE')
FAMILY64 = 'Regime-Adaptive Composite'


def regime_evidence64(x):
    """Closed-bar state; no future filling. Thresholds are fixed, not audit-fit."""
    z = x.copy()
    z['ema_slope'] = (z.ema20 - z.ema20.shift(5)) / z.atr14.replace(0, np.nan)
    z['ema_separation'] = (z.ema20 - z.ema100) / z.atr14.replace(0, np.nan)
    z['atr_cut'] = z.atr_pct.shift(1).rolling(252, min_periods=100).quantile(.85)
    required = ['adx14', 'ema_slope', 'ema_separation', 'atr_cut', 'bb_width', 'vol20', 'roc10']
    ready = z[required].notna().all(axis=1)
    raw = pd.Series('UNKNOWN', index=z.index)
    raw.loc[ready] = 'RANGE'
    up = ready & (z.adx14 >= 23) & (z.ema_slope > .1) & (z.ema_separation > .3)
    down = ready & (z.adx14 >= 23) & (z.ema_slope < -.1) & (z.ema_separation < -.3)
    raw.loc[up] = 'TREND_UP'
    raw.loc[down] = 'TREND_DOWN'
    raw.loc[ready & (z.atr_pct > z.atr_cut)] = 'VOLATILE'
    z['regime_closed'] = raw
    z['completeness_pct'] = z[required].notna().mean(axis=1) * 100
    # Fixed UTC session windows are descriptive proxies, not DST-adjusted exchanges.
    h = z.index.hour
    z['asia'] = (h >= 0) & (h < 7)
    z['session64'] = np.select([z.overlap, z.new_york, z.london, z.asia],
                              ['OVERLAP', 'NEW_YORK', 'LONDON', 'ASIA'], default='OTHER')
    return z


def label_market_regimes(x):
    return regime_evidence64(x).regime_closed.shift(1).fillna('UNKNOWN')


class RegimeRouter:
    """One independently validated family/config per regime and side; no voting."""
    def __init__(self, routes, allow_experiment=False):
        self.routes = routes
        self.allow_experiment = allow_experiment

    def signals(self, x):
        ev = regime_evidence64(x)
        signal = pd.Series(0, index=x.index, dtype=int)
        sl = pd.Series(1.5, index=x.index)
        rr = pd.Series(2., index=x.index)
        family = pd.Series('NONE', index=x.index)
        conflict = pd.Series(False, index=x.index)
        for key, config in self.routes.items():
            if not config.get('validated', False) and not (self.allow_experiment and config.get('paper_only', False)):
                continue
            regime, side = key.split('|')
            if regime not in REGIMES64 or config['family'] not in STRATEGIES:
                continue
            value = 1 if side == 'BUY' else -1
            raw = STRATEGIES[config['family']](x, config['params'])
            mask = (ev.regime_closed == regime) & (raw == value)
            conflict |= mask & (signal != 0)
            signal.loc[mask] = value
            sl.loc[mask] = config['params']['sl']
            rr.loc[mask] = config['params']['rr']
            family.loc[mask] = config['family']
        signal.loc[conflict] = 0
        family.loc[conflict] = 'CONFLICT_BLOCKED'
        return signal, sl, rr, family, ev


def directional_signal64(x, family, params, regime, side):
    raw = STRATEGIES[family](x, params)
    state = x['regime_closed64'] if 'regime_closed64' in x else regime_evidence64(x).regime_closed
    return raw.where((state == regime) & (raw == side), 0)


def monthly64(trades):
    if trades.empty:
        return pd.DataFrame()
    t = trades.copy()
    t['month'] = pd.to_datetime(t.exit_time, utc=True).dt.strftime('%Y-%m')
    rows = []
    for month, g in t.groupby('month'):
        r = g.ret.astype(float)
        losses = -r[r < 0].sum()
        rows.append(dict(month=month, return_pct=(np.prod(1+r)-1)*100,
                         trades=len(g), win_rate=(r>0).mean()*100,
                         profit_factor=float(r[r>0].sum()/losses) if losses else (99 if (r>0).any() else 0),
                         BUY_contribution=float(g.loc[g.side==1, 'ret'].sum()*100),
                         SELL_contribution=float(g.loc[g.side==-1, 'ret'].sum()*100)))
    return pd.DataFrame(rows)


def tag_trades64(t, x, families=None):
    if t.empty:
        return t
    t = t.copy()
    ev = regime_evidence64(x)
    entry_regime = ev.regime_closed.shift(1)
    t['regime'] = entry_regime.reindex(pd.DatetimeIndex(t.entry_time)).to_numpy()
    t['exit_regime'] = ev.regime_closed.reindex(pd.DatetimeIndex(t.exit_time)).to_numpy()
    t['regime_changed'] = [ev.regime_closed.loc[a:b].nunique() > 1
                           for a,b in zip(t.entry_time, t.exit_time)]
    t['session'] = ev.session64.shift(1).reindex(pd.DatetimeIndex(t.entry_time)).to_numpy()
    if families is not None:
        t['family'] = families.shift(1).reindex(pd.DatetimeIndex(t.entry_time)).to_numpy()
    t['r_multiple'] = t.ret * t.entry / (t.entry - t.initial_stop).abs()
    return t


def run_router64(x, routes, cost):
    sig, sl, rr, families, ev = RegimeRouter(routes).signals(x)
    if len(x) < 3:
        return pd.DataFrame(), {}, pd.Series(dtype=float)
    t, m, curve = backtest_v5_lifecycle(x, sig, sl, rr, cost, max_hold_bars=96)
    return tag_trades64(t, x, families), m, curve


def neighbours64(p):
    """Single-axis +/-10% perturbations including signal and risk thresholds."""
    neighbours = []
    for k in ('sl', 'rr', 'adx', 'adx_max', 'rsi_l', 'rsi_s', 'rsi_lo', 'rsi_hi',
              'h1_rsi', 'std', 'wick', 'z', 'adx_trend', 'n'):
        if k not in p:
            continue
        # Fixed feature columns for BOS/sweep must remain in their valid discrete set.
        if k == 'n' and p[k] in (5,10):
            continue
        for scale in (.9, 1.1):
            q = dict(p)
            q[k] = max(2, int(round(p[k]*scale))) if k == 'n' else float(p[k]*scale)
            neighbours.append(q)
    return neighbours


def fit_routes64(fit, cost, inner_folds=3, families=None):
    """Select independently per direction/regime using inner time blocks ONLY.

    All inner blocks precede outer validation. Features initialized before slicing.
    A small declared grid and neighbourhood checks avoid a sharp single optimum.
    """
    fit = fit.copy()
    fit['regime_closed64'] = regime_evidence64(fit).regime_closed
    grids = param_grid('Quick')
    families = families or list(grids)
    routes, rows = {}, []
    splits = _wf_slices(len(fit), inner_folds, min_bars=80)
    if len(splits) < 3:
        return routes, pd.DataFrame()
    for regime in REGIMES64:
        for side in (1,-1):
            candidates = []
            for family in families:
                for p in grids[family]:
                    sig = directional_signal64(fit, family, p, regime, side)
                    metrics, trades = [], []
                    for a,b in splits:
                        t,m,_ = backtest_v5_lifecycle(fit.iloc[a:b], sig.iloc[a:b], p['sl'], p['rr'], cost)
                        metrics.append(m)
                        trades.append(t)
                    tt = pd.concat(trades, ignore_index=True)
                    if tt.empty:
                        continue
                    r = np.array([m['return_pct'] for m in metrics])
                    score = float(r.mean() - .5*r.std() + .2*r.min())
                    candidates.append((score, family, p, metrics, tt))
            candidates.sort(key=lambda c:c[0], reverse=True)
            # Evaluate nearby configs for top 2, prefer stable broad results.
            best = None
            for score, family, p, metrics, tt in candidates[:2]:
                nearby = []
                for q in neighbours64(p):
                    try:
                        sig = directional_signal64(fit, family, q, regime, side)
                        rs = []
                        for a,b in splits:
                            _, m, _ = backtest_v5_lifecycle(fit.iloc[a:b], sig.iloc[a:b], q['sl'], q['rr'], cost)
                            rs.append(m['return_pct'])
                        nearby.append(float(np.mean(rs)))
                    except KeyError:
                        continue
                base_return = np.mean([m['return_pct'] for m in metrics])
                stable = bool(nearby) and np.mean(np.array(nearby)>0) >= .7 and np.median(nearby) >= .5*max(base_return,0)
                positives = sum(m['return_pct']>0 for m in metrics)
                losses = -tt.loc[tt.ret<0,'ret'].sum()
                pf = float(tt.loc[tt.ret>0,'ret'].sum()/losses) if losses else 99.
                month = monthly64(tt)
                profits = month.return_pct.clip(lower=0)
                concentration = float(profits.max()/profits.sum()) if profits.sum()>0 else 1.
                valid = stable and positives >= len(metrics)-1 and len(tt)>=9 and pf>=1.15 and concentration<=.7
                robust_score = score - (0 if stable else 5.) - 2*concentration
                config = dict(family=family, params=dict(p), validated=bool(valid),
                              stability=float(np.mean(np.array(nearby)>0)) if nearby else 0.,
                              inner_positive=positives, inner_folds=len(metrics),
                              trades=len(tt), pf=pf, month_concentration=concentration,
                              score=robust_score)
                if best is None or (config['validated'], robust_score) > (best['validated'], best['score']):
                    best = config
            if best:
                key = f"{regime}|{'BUY' if side==1 else 'SELL'}"
                rows.append(dict(route=key, **best))
                if best['validated']:
                    routes[key] = best
    return routes, pd.DataFrame(rows)


def nested_router64(train, cost, outer_folds=4, inner_folds=3, families=None):
    splits = _nested_outer_splits(len(train), outer_folds, min_train=max(600,len(train)//3))
    oof, stress_trades, fold_rows, versions = [], [], [], []
    curves = []
    for i,(a,b,c,d) in enumerate(splits):
        assert b <= c and a < b < d
        routes, evidence = fit_routes64(train.iloc[a:b], cost, inner_folds, families)
        val = train.iloc[c:d]
        t,m,curve = run_router64(val, routes, cost)
        st,sm,_ = run_router64(val, routes, CostModel(.50,.10))
        _,spread_m,_ = run_router64(val, routes, CostModel(.50,.05))
        _,slip_m,_ = run_router64(val, routes, CostModel(.30,.10))
        oof.append(t); stress_trades.append(st); curves.append(curve)
        fold_rows.append(dict(fold=i+1, fit_start=train.index[a], fit_end=train.index[b-1],
                              validation_start=train.index[c], validation_end=train.index[d-1],
                              routes=len(routes), **m, stress_return=sm.get('return_pct',0),
                              spread_only_return=spread_m.get('return_pct',0),
                              slippage_only_return=slip_m.get('return_pct',0)))
        versions.append(routes)
    final_routes, route_evidence = fit_routes64(train, cost, inner_folds, families)
    t = pd.concat(oof,ignore_index=True) if oof else pd.DataFrame()
    st = pd.concat(stress_trades,ignore_index=True) if stress_trades else pd.DataFrame()
    folds = pd.DataFrame(fold_rows)
    # Concatenate independent validation equity paths continuously at 1x exposure.
    scaled, factor = [], 1.
    for curve in curves:
        scaled.append(curve*factor)
        if len(curve): factor *= float(curve.iloc[-1])
    curve = pd.concat(scaled) if scaled else pd.Series(dtype=float)
    return dict(routes=final_routes, route_evidence=route_evidence, folds=folds,
                trades=t, stress_trades=st, curve=curve, fold_routes=versions)


def robust_report64(result, target=15., min_trades=24):
    t, folds, curve = result['trades'], result['folds'], result['curve']
    components, reasons = {}, []
    if t.empty or folds.empty:
        return dict(pass_gate=False, target_status='FAIL', score=0., components={}, reasons=['No validated outer trades'])
    monthly = monthly64(t)
    ret = (np.prod(1+t.ret)-1)*100
    losses = -t.loc[t.ret<0,'ret'].sum()
    pf = float(t.loc[t.ret>0,'ret'].sum()/losses) if losses else 99.
    dd = float((curve/curve.cummax()-1).min()*100)
    consistency = float((folds.return_pct>0).mean())
    buy = float(t.loc[t.side==1,'ret'].sum()*100)
    sell = float(t.loc[t.side==-1,'ret'].sum()*100)
    regime_groups = t.groupby('regime').ret.agg(['sum','count'])
    covered = regime_groups[regime_groups['count']>=5]
    profits = monthly.return_pct.clip(lower=0)
    concentration = float(profits.max()/profits.sum()) if profits.sum()>0 else 1.
    stress = (np.prod(1+result['stress_trades'].ret)-1)*100 if not result['stress_trades'].empty else 0.
    spread_return = float((np.prod(1+folds.spread_only_return/100)-1)*100)
    slippage_return = float((np.prod(1+folds.slippage_only_return/100)-1)*100)
    stability = float(np.mean([v['stability'] for v in result['routes'].values()])) if result['routes'] else 0.
    # Stability of selected family across outer fit versions (not parameter probability).
    agreements = []
    for key,v in result['routes'].items():
        seq = [r.get(key,{}).get('family') for r in result['fold_routes']]
        agreements.append(sum(f==v['family'] for f in seq)/max(1,len(seq)))
    route_stability = float(np.mean(agreements)) if agreements else 0.
    windows90 = []
    for end in pd.date_range(curve.index.min()+pd.Timedelta(days=90), curve.index.max(), freq='30D'):
        q = curve.loc[end-pd.Timedelta(days=90):end]
        if len(q)>1: windows90.append((q.iloc[-1]/q.iloc[0]-1)*100)
    target_pass = bool(windows90) and float(np.median(windows90))>=target
    components = dict(walk_forward_consistency=consistency*100, profit_factor=min(pf/1.5,1)*100,
                      drawdown=max(0,1-abs(dd)/15)*100, BUY_SELL_balance=100. if buy>0 and sell>0 else 0.,
                      regime_coverage=len(covered)/4*100,
                      regime_consistency=float((covered['sum']>0).mean()*100) if len(covered) else 0.,
                      parameter_neighbours=stability*100, route_family_stability=route_stability*100,
                      cost_sensitivity=max(0,min(1,stress/max(ret,.001)))*100,
                      spread_sensitivity=max(0,min(1,spread_return/max(ret,.001)))*100,
                      slippage_sensitivity=max(0,min(1,slippage_return/max(ret,.001)))*100,
                      trade_count=min(len(t)/min_trades,1)*100,
                      monthly_stability=max(0,1-concentration)*100)
    checks = {'outer fold consistency':consistency>=.75, 'profit factor':pf>=1.2,
              'drawdown':dd>=-15, 'BUY and SELL contributions':buy>0 and sell>0,
              'minimum directional trades':min((t.side==1).sum(),(t.side==-1).sum())>=6,
              'trade count':len(t)>=min_trades, 'regime coverage':len(covered)>=2,
              'regime consistency':len(covered)>0 and (covered['sum']>0).mean()>=.5,
              'parameter stability':stability>=.7, 'route stability':route_stability>=.5,
              'month concentration':concentration<=.6, 'stress costs':stress>0 and stress>=.5*max(ret,0),
              'frequency cap':len(t)/max(1,(curve.index.max()-curve.index.min()).days)<=10,
              '15% target over 90 days':target_pass, 'validated routes':bool(result['routes'])}
    reasons = [k+' failed' for k,v in checks.items() if not v]
    return dict(pass_gate=all(checks.values()), target_status='PASS' if target_pass else 'FAIL',
                score=float(np.mean(list(components.values()))), components=components, reasons=reasons,
                return_pct=float(ret), max_dd_pct=dd, profit_factor=pf, trades=len(t),
                BUY_contribution=buy, SELL_contribution=sell, stress_return_pct=float(stress),
                spread_only_return_pct=spread_return, slippage_only_return_pct=slippage_return,
                median_90_day_return=float(np.median(windows90)) if windows90 else None,
                best_month=float(monthly.return_pct.max()), worst_month=float(monthly.return_pct.min()))


def research64(self, research_days=400, audit_days=90, timeframes=('15m','30m','1h'),
               audit_start='2026-07-01', outer_folds=4, inner_folds=3, include_ml=False):
    # Observed V6.3 dates were not supplied precisely; conservative fixed embargo.
    # Never slide this boundary with today's date or reuse audit for optimization.
    boundary = pd.Timestamp(audit_start, tz='UTC')
    start = boundary - pd.Timedelta(days=int(research_days))
    end = min(boundary+pd.Timedelta(days=int(audit_days)), pd.Timestamp.now(tz='UTC').floor('D'))
    requested = sorted(timeframes, key=lambda tf:DEEP_MINUTES[tf])
    if not requested: raise ValueError('Select at least one timeframe')
    base = requested[0]
    raw = self.market.fetch_candles_range(DEEP_INTERVALS[base], start-pd.Timedelta(days=35), end, rate_limit_safe=True)
    raw = _closed_only(raw, DEEP_MINUTES[base])
    datasets = self._derive_deep_timeframes(base,raw,requested)
    results, audits = {}, {}
    cost = CostModel(.30,.05)
    for tf in requested:
        primary = datasets[tf]
        context = resample_ohlc_strict(datasets['1h'],'4h',4) if tf=='1h' else datasets['1h']
        x,_ = build_deep_features(primary,context,240 if tf=='1h' else 60,include_macro=False)
        # Need full candle closure before the excluded audit boundary.
        train = x[(x.index>=start) & (x.index+pd.Timedelta(minutes=DEEP_MINUTES[tf])<=boundary)].copy()
        if len(train)<1500: raise ValueError('Insufficient development bars; lower days/TF or check API entitlement')
        result = nested_router64(train,cost,outer_folds,inner_folds)
        result['report'] = robust_report64(result)
        result['timeframe'] = tf
        result['development_start'] = str(start); result['development_end'] = str(boundary)
        result['ml'] = internal_ml_benchmark(train,cost) if include_ml else pd.DataFrame()
        results[tf] = result
    # Rank BEFORE reading audit outcomes. Audit never affects ranking/gating.
    selected_tf = max(results,key=lambda tf:(results[tf]['report']['pass_gate'],results[tf]['report']['score']))
    selected = results[selected_tf]
    primary = datasets[selected_tf]
    context = resample_ohlc_strict(datasets['1h'],'4h',4) if selected_tf=='1h' else datasets['1h']
    x,_ = build_deep_features(primary,context,240 if selected_tf=='1h' else 60,False)
    audit = x[(x.index>=boundary) & (x.index<end)].copy()
    at,am,ac = run_router64(audit,selected['routes'],cost)
    payload = dict(routes=selected['routes'], _timeframe=selected_tf, audit_start=str(boundary),
                   development_start=str(start), method='V6.4_NESTED_REGIME_DIRECTIONAL',
                   frozen_at=datetime.now(timezone.utc).isoformat())
    payload['parameter_version'] = hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()[:16]
    return dict(selected=selected, results=results, payload=payload,
                audit=dict(trades=at,metrics=am,curve=ac), audit_start=boundary,audit_end=end)


CoreService.run_regime_research = research64

# Harden existing risk and execution engines rather than bypassing them.
_assess63 = RiskEngine.assess
_execute63 = PaperExecutionEngine.execute
_activate63 = TradingRepository.set_active_strategy


def activate64(self, family, params, metrics, gate_pass):
    if family != FAMILY64 or not gate_pass or not metrics.get('pass_gate') or not params.get('routes'):
        raise ValueError('Failed/legacy/ML candidates cannot be activated')
    if any(not c.get('validated') for c in params['routes'].values()):
        raise ValueError('Every route must pass internal validation')
    return _activate63(self,family,params,metrics,True)


TradingRepository.set_active_strategy = activate64


def assess64(self, account, plan, quote, latest_closed_1m_at=None):
    decision = _assess63(self,account,plan,quote,latest_closed_1m_at)
    reasons = list(decision.reason_codes); explanations = list(decision.explanation)
    positions = self.repository.all_positions(account.id)
    now = datetime.now(timezone.utc)
    recent = [p for p in positions if (now-_utc(p.opened_at)).total_seconds()<300]
    if recent:
        reasons.append('ROLLING_FILL_PROTECTION'); explanations.append('At most one fill per rolling five minutes')
    opens = [p for p in positions if p.status=='OPEN']
    aggregate = sum(Decimal(p.frozen_initial_risk_usd) for p in opens)+plan.gross_risk_usd
    if aggregate>Decimal(account.equity)*self.settings.max_aggregate_risk_pct/100:
        reasons.append('AGGREGATE_RISK'); explanations.append('Aggregate frozen risk exceeds limit')
    day_events = [e for e in self.repository.events() if _utc(e.occurred_at).date()==now.date()]
    realized = sum(Decimal(e.pnl or 0) for e in day_events if any(p.id==e.position_id for p in positions))
    unrealized = Decimal('0')
    for p in opens:
        mark = quote.reference_price
        if quote.bid is not None and quote.ask is not None:
            mark = quote.bid if p.side=='BUY' else quote.ask
        else:
            mark += (-1 if p.side=='BUY' else 1)*(self.settings.reference_assumed_spread_usd/2+self.settings.reference_slippage_usd)
        unrealized += (mark-Decimal(p.entry))*(1 if p.side=='BUY' else -1)*Decimal(p.remaining_lot)*100
    if realized+unrealized <= -Decimal(account.equity)*Decimal('.03'):
        reasons.append('DAILY_DRAWDOWN'); explanations.append('UTC daily realized plus open losses exceed 3% of configured capital')
    if plan.quote_policy==QuotePolicy.REFERENCE_SIMULATION and self.settings.reference_assumed_spread_usd>self.settings.max_spread_usd:
        reasons.append('SPREAD_TOO_WIDE'); explanations.append('Simulation spread exceeds limit')
    if quote.source_timestamp and _utc(quote.source_timestamp)>now+timedelta(seconds=5):
        reasons.append('QUOTE_FROM_FUTURE'); explanations.append('Invalid source timestamp')
    if plan.source in ('RESEARCH_STRATEGY','PAPER_EXPERIMENT'):
        active=self.repository.get_active_strategy()
        if not paper_active64(active, plan.quote_policy) or (plan.source=='RESEARCH_STRATEGY' and not active.gate_pass):
            reasons.append('NO_VALIDATED_ACTIVE_STRATEGY'); explanations.append('No robust active composite')
    return RiskDecision(not reasons,tuple(reasons),tuple(explanations),now,now+timedelta(seconds=30),plan.plan_hash)


RiskEngine.assess = assess64


def execute64(self, account, plan, decision, quote):
    # Fill-risk reflects spread/slippage before approval; account controls rechecked.
    fresh = self.repository.get_account(account.id)
    closed_at = getattr(self,'latest_closed_1m_at',None)
    recheck = RiskEngine(self.settings,self.repository).assess(fresh,plan,quote,closed_at)
    if not recheck.approved: raise RuntimeError('EXECUTION_RECHECK_BLOCKED: '+','.join(recheck.reason_codes))
    fill = self._fill_price(plan.side,quote,plan.quote_policy)
    risk=abs(fill-plan.initial_sl)*100*Decimal('.03')
    if risk>Decimal(fresh.equity)*self.settings.max_risk_per_trade_pct/100: raise RuntimeError('FILL_RISK_EXCEEDED')
    p = _execute63(self,fresh,plan,decision,quote)
    context = getattr(self,'route_context',{})
    self.repository.add_event(p.id,f'{p.id}:REGIME_ENTRY','REGIME_ENTRY',utcnow(),
                              details=dict(context, parameter_version=context.get('parameter_version'),
                                           spread_assumption=str(self.settings.reference_assumed_spread_usd),
                                           slippage_assumption=str(self.settings.reference_slippage_usd),
                                           stop=str(p.sl_initial), targets=[str(getattr(p,f'tp{i}')) for i in range(1,6)],
                                           risk_usd=str(risk), risk_pct=str(risk/Decimal(fresh.equity)*100)))
    return p


PaperExecutionEngine.execute = execute64


def market64(self):
    quote=self.market.fetch_reference_quote()
    minute=_closed_only(self.market.fetch_candles('1min',500),1)
    base=_closed_only(self.market.fetch_candles('15min',1800),15)
    hour=resample_ohlc_strict(base,'1h',4)
    frames={'1m':minute,'15m':base,'30m':resample_ohlc_strict(base,'30min',2),'1h':hour}
    # 5m download only when the selected active PAPER model needs it.
    active=self._active_strategy_payload()
    if active and active['params'].get('_timeframe')=='5m':
        frames['5m']=_closed_only(self.market.fetch_candles('5min',500),5)
    self.repo.save_market_snapshot(quote)
    return quote,frames


CoreService.fetch_market = market64


def run_once64(self, *, allow_execution):
    self.account=self.repo.get_account(self.account.id)
    quote,frames=self.fetch_market()
    active=self._active_strategy_payload()
    tf=active['params'].get('_timeframe','15m') if active else '15m'
    primary,context,cm=live_strategy_frames(frames,tf)
    x,_=build_deep_features(primary,context,cm,False)
    ev=regime_evidence64(x)
    regime=str(ev.regime_closed.iloc[-1]) if len(ev) else 'UNKNOWN'
    # Preserve management independently of active/new-entry gates.
    for p in self.repo.open_positions(self.account.id):
        self.execution.replay_bars(p.id,frames['1m'])
        current=self.repo.get_position(p.id)
        entries=[e for e in self.repo.events() if e.position_id==p.id and e.event_type=='REGIME_ENTRY']
        details=json.loads(entries[-1].details_json) if entries else {}
        position_tf=details.get('timeframe',tf)
        pp,pc,pm=live_strategy_frames(frames,position_tf)
        px,_=build_deep_features(pp,pc,pm,False)
        pev=regime_evidence64(px)
        available=pev.regime_closed.copy()
        available.index=available.index+pd.Timedelta(minutes=DEEP_MINUTES[position_tf])
        observed_at=pd.Timestamp(_utc(current.closed_at)) if current.closed_at else pd.Timestamp.now(tz='UTC')
        known=available.loc[:observed_at]
        exit_regime=str(known.iloc[-1]) if len(known) else 'UNKNOWN'
        during=available.loc[pd.Timestamp(_utc(p.opened_at)):observed_at]
        changed=bool((during!=details.get('regime')).any()) if len(during) else False
        self.repo.add_event(p.id,f'{p.id}:REGIME:{frames["1m"].index[-1]}','REGIME_OBSERVATION',utcnow(),
                            details=dict(regime=exit_regime,regime_changed=changed,
                                         regime_at_exit=exit_regime if current.status=='CLOSED' else None,
                                         result=current.status,pnl=str(current.realized_pnl),
                                         r_multiple=str(Decimal(current.realized_pnl)/Decimal(current.frozen_initial_risk_usd)) if current.frozen_initial_risk_usd else None))
    bundle=self.analyze(frames)
    core_evaluation=evaluate(bundle)
    out=dict(quote=quote,frames=frames,bundle=bundle,evaluation=core_evaluation,
             strategy_evaluation=None,active_strategy=active,strategy_signal=0,candidate_id=None,
             plan=None,risk=None,position=None,regime=regime,regime_evidence=ev)
    experimental = bool(active and active['params'].get('paper_experiment'))
    if not active or active['family']!=FAMILY64 or (not active['gate_pass'] and not experimental):
        return out
    if experimental and self.settings.quote_policy!=QuotePolicy.REFERENCE_SIMULATION:
        return out
    sig,sl,rr,families,_=RegimeRouter(active['params']['routes'], allow_experiment=experimental).signals(x)
    side_value=int(sig.iloc[-1]) if len(sig) else 0
    if not side_value: return out
    primary_close=primary.index[-1]+pd.Timedelta(minutes=DEEP_MINUTES[tf])
    if (pd.Timestamp.now(tz='UTC')-primary_close).total_seconds()>DEEP_MINUTES[tf]*60+180:
        return out
    side=Side.BUY if side_value>0 else Side.SELL
    key=f'{regime}|{side.value}'
    config=active['params']['routes'].get(key)
    if not config: return out
    cid=self._research_candidate_id(primary,tf,config['family'],side,active)
    evaluation=SignalEvaluation(side,100 if side_value>0 else 0,100 if side_value<0 else 0,
                               100,60 if experimental else 85,Grade.B if experimental else Grade.A_PLUS,CandidateStatus.WATCH_ONLY if experimental else CandidateStatus.APPROVED,(),
                               (f'{regime}: {config["family"]} {side.value}',),('UNVALIDATED PAPER EXPERIMENT',) if experimental else (),utcnow())
    plan=build_research_trade_plan(cid,side,quote.reference_price,Decimal(str(x.atr14.iloc[-1])),
                                   config['params'],Decimal(self.account.equity),self.settings.quote_policy,
                                   self.settings.fixed_lot,self.settings.contract_oz_per_lot,not experimental)
    if experimental and plan is not None:
        from dataclasses import replace
        plan=replace(plan,source='PAPER_EXPERIMENT',research_authorized=True,
                     reasons_against=('UNVALIDATED PAPER EXPERIMENT: no robust PASS',),
                     plan_hash=hashlib.sha256((plan.plan_hash+'PAPER_EXPERIMENT').encode()).hexdigest())
    self.repo.save_candidate(cid,evaluation,plan,source='PAPER_EXPERIMENT' if experimental else 'RESEARCH_STRATEGY')
    decision=self.risk.assess(self.account,plan,quote,frames['1m'].index[-1].to_pydatetime()+timedelta(minutes=1)) if plan else None
    self.execution.latest_closed_1m_at=frames['1m'].index[-1].to_pydatetime()+timedelta(minutes=1)
    self.execution.route_context=dict(regime=regime,timeframe=tf,active_strategy=config['family'],side=side.value,
                                      signal_reason=evaluation.reasons_for, parameter_version=active['params']['parameter_version'],unvalidated_experiment=experimental)
    pos=self.execution.execute(self.account,plan,decision,quote) if allow_execution and decision and decision.approved else None
    out.update(strategy_evaluation=evaluation,strategy_signal=side_value,candidate_id=cid,plan=plan,risk=decision,position=pos)
    return out


CoreService.run_once = run_once64

class DailyRiskState64(Base):
    __tablename__='daily_risk_v64'
    key: Mapped[str] = mapped_column(String(80),primary_key=True)
    peak: Mapped[Decimal] = mapped_column(Numeric(24,8))
    breached: Mapped[bool] = mapped_column(Boolean,default=False)


_risk_assess64 = RiskEngine.assess

def daily_assess64(self,account,plan,quote,latest_closed_1m_at=None):
    decision=_risk_assess64(self,account,plan,quote,latest_closed_1m_at)
    positions=self.repository.all_positions(account.id)
    realized=sum(Decimal(p.realized_pnl) for p in positions)
    open_pnl=sum((quote.reference_price-Decimal(p.entry))*(1 if p.side=='BUY' else -1)*Decimal(p.remaining_lot)*100
                 for p in positions if p.status=='OPEN')
    marked=Decimal(account.equity)+realized+open_pnl
    key=f'{account.id}:{utcnow().date()}'
    with self.repository.session_factory.begin() as session:
        state=session.get(DailyRiskState64,key)
        if state is None:
            state=DailyRiskState64(key=key,peak=max(marked,Decimal(account.equity)+realized),breached=False)
            session.add(state)
        state.peak=max(Decimal(state.peak),marked)
        if marked<=Decimal(state.peak)*Decimal('.97'): state.breached=True
        blocked=state.breached
    if blocked:
        return RiskDecision(False,decision.reason_codes+('DAILY_PEAK_DRAWDOWN',),
                            decision.explanation+('Observed UTC-day peak drawdown >=3%; latched until next UTC day',),
                            decision.approved_at,decision.expires_at,decision.plan_hash)
    return decision

RiskEngine.assess=daily_assess64

# Serialize execution within the single-process prototype. Cross-replica atomic
# risk admission requires a broker/transactional service and is not claimed here.
import threading
_EXECUTION_LOCK64=threading.RLock()
_execute_unlocked64=PaperExecutionEngine.execute

def serialized_execute64(self,account,plan,decision,quote):
    with _EXECUTION_LOCK64:
        return _execute_unlocked64(self,account,plan,decision,quote)

PaperExecutionEngine.execute=serialized_execute64


def render_dashboard():
    st.set_page_config(page_title='Gold Intelligence V6.6 Scalp',page_icon='🥇',layout='wide',initial_sidebar_state='collapsed')
    st.markdown('<style>.block-container{padding:1rem .75rem;max-width:100%}</style>',unsafe_allow_html=True)
    st.title('🥇 Gold Intelligence V6.6 — Observable Scalp PAPER')
    st.caption('XAU/USD research · Independent BUY/SELL routes · Forward PAPER validation · 15% is a target, not a guarantee')
    with st.sidebar:
        equity=Decimal(str(st.number_input('PAPER starting equity ($)',100.,1000000.,10000.,100.)))
        policy=st.selectbox('Quote policy',['REFERENCE_SIMULATION','STRICT_EXECUTABLE'])
        st.caption('STRICT blocks entries without genuine bid/ask. REFERENCE_SIMULATION uses simulated fills.')
        auto=st.toggle('Enable Auto PAPER',True)
        kill=st.toggle('Kill switch',False)
        spread=Decimal(str(st.number_input('Assumed spread ($/oz)',0.,5.,.30,.05)))
        slip=Decimal(str(st.number_input('Slippage each side ($/oz)',0.,5.,.05,.01)))
        monitoring=st.toggle('Monitor while session is active',True)
        require_volume=st.checkbox('Require valid provider volume for entry',False)
        allow_no_news=st.checkbox('Allow PAPER without a valid calendar (no news protection)',False)
        session_choice=st.selectbox('Session filter',['ALL','LONDON','NEW_YORK','OVERLAP'])
        st.metric('Original volume','0.03 lot')
        st.caption('TP3 closes exactly 0.015 lot.')
    settings=load_settings(_secrets_dict(),dict(quote_policy=QuotePolicy(policy),reference_assumed_spread_usd=spread,reference_slippage_usd=slip))
    try:
        service=_service(settings)
    except Exception:
        st.error("Database connection failed; verify DATABASE_URL privately in Streamlit Secrets.")
        st.stop()
    service.set_account_controls(equity,auto,kill)
    service.ensure_paper_experiment()
    service.scalp_options=dict(require_volume=require_volume,allow_no_news=allow_no_news,session=session_choice)
    st.warning('PAPER EXPERIMENT — Initial presets are unvalidated; robust gate=FAIL/NOT TESTED. Simulated trades use actual backend reference data.')
    if service.repo.get_active_strategy() is None and st.button('Reactivate experimental PAPER preset'):
        service.start_paper_experiment();st.rerun()
    if settings.database_url.startswith('sqlite'):
        st.warning('SQLite is a prototype store and may be lost on Cloud restarts. PostgreSQL is preferred for durability. Concurrent replicas are not supported.')
    if not settings.twelve_data_api_key: st.info('Set TWELVEDATA_API_KEY in Streamlit Secrets.')
    active=service.repo.get_active_strategy()
    st.sidebar.write('Active strategy:',active.family+' — '+('ROBUST PASS' if active.gate_pass else 'UNVALIDATED PAPER') if active else 'NONE')
    tabs=st.tabs(['Live Dashboard','Analysis & Patterns','Robust Strategy Research','Regime Engine',
                  'Signal Candidates','Paper Positions','Journal','Performance','Risk Control','Setup / Connectors','News Calendar','Cycle Health','Diagnostic Lab'])
    with tabs[0]:
        manual=st.button('Analyze market / manage existing positions',disabled=not bool(settings.twelve_data_api_key))
        @st.fragment(run_every='30s' if monitoring else None)
        def cycle():
            if (manual or monitoring) and settings.twelve_data_api_key:
                try:
                    st.session_state['last65']=service.run_once(allow_execution=monitoring and auto and not kill)
                except Exception:
                    st.error('Cycle failed. Health retains the error and last success; secrets are never displayed.')
            render_health65(service,monitoring)
            result=st.session_state.get('last65')
            if result:
                st.write('Entry / no-entry reason:',result.get('no_entry_reason'))
                st.write('Regime (15m closed):',result['regime'])
                render_scalp_snapshot65(result,settings)
                notional=Decimal('3')*result['quote'].reference_price
                st.metric('Notional exposure',f'${notional:,.2f}')
                st.metric('Exposure / base equity',f'{notional/equity:.2f}×')
                if notional/equity>1: st.warning('Fixed 0.03 lot exceeds 1x starting equity.')
        cycle()
        with st.expander('TradingView FXPRO:XAUUSD — visual 5m chart',expanded=False):
            components.html(advanced_chart_html('FXPRO:XAUUSD','5'),height=500,scrolling=False)
            st.caption('TradingView is visual only. Backend calculations use Twelve Data.')
    result=st.session_state.get('last65')
    with tabs[1]:
        if result:
            st.plotly_chart(scalp_chart65(result['scalp_features'].tail(160)),width='stretch',key='analysis_chart66')
            st.dataframe(pd.DataFrame([{'Condition':k,'Value':str(v)} for k,v in result.get('signal_evidence',{}).items()]),hide_index=True)
            st.caption('Structure levels use previous candles only; the current candle does not define its own breakout level.')
        else: st.info('Run a data cycle first.')
    with tabs[2]:
        st.warning('V6.3 audit already observed: return approx -2.77%, DD -4.48%, PF 0.69, 31 trades, gate=FAIL. This is not an untouched holdout.')
        st.caption('Exact prior audit dates were unavailable. The conservative boundary is 2026-07-01; only move it earlier using the actual prior dates. Later data is excluded from fitting.')
        days=st.number_input('Historical development days before audit boundary',180,540,400,10)
        audit_days=st.number_input('Historical audit days (excluded from selection)',30,180,90,10)
        boundary=st.date_input('Observed audit start / development end',datetime(2026,7,1).date(),max_value=datetime(2026,7,1).date())
        tfs=st.multiselect('Timeframes',['5m','15m','30m','1h'],default=['15m','30m','1h'])
        folds=st.slider('Outer walk-forward folds',3,6,4)
        inner=st.slider('Inner validation blocks',3,5,3)
        ml=st.checkbox('ML development benchmark; never executable',False)
        st.info('Initial history download and nested research can take time. 5m is optional. Base costs 0.30/0.05; stress 0.50/0.10.')
        if st.button('Run V6.4 family research',disabled=not bool(settings.twelve_data_api_key) or not tfs):
            with st.spinner('Downloading, validating routes and checking stability...'):
                try:
                    st.session_state['research64']=service.run_regime_research(days,audit_days,tuple(tfs),str(boundary),folds,inner,ml)
                except Exception:
                    st.error('Research incomplete. Check quota, historical access and data coverage. No model was activated.')
        research=st.session_state.get('research64')
        if research:
            selected=research['selected']; report=selected['report']
            st.subheader('Historical development — nested outer validation (1×)')
            st.dataframe(pd.DataFrame([dict(timeframe=k,**v['report']) for k,v in research['results'].items()]).drop(columns=['components','reasons'],errors='ignore'),hide_index=True)
            st.write('Selected timeframe:',selected['timeframe'])
            st.json(report)
            st.dataframe(pd.DataFrame(list(report['components'].items()),columns=['Robustness component','Score /100']),hide_index=True)
            st.caption('These are explanatory scores, not probabilities. Timeframe selection also creates selection uncertainty; future PAPER validation is required.')
            st.dataframe(selected['route_evidence'],hide_index=True)
            st.dataframe(selected['folds'],hide_index=True)
            st.dataframe(monthly64(selected['trades']),hide_index=True)
            if not selected['trades'].empty:
                st.write('Regime / side / session breakdown')
                st.dataframe(selected['trades'].groupby(['regime','side','session']).ret.agg(['sum','count','mean']))
            if len(selected['curve']): st.line_chart(selected['curve'])
            st.subheader('Historical audit — observed, never used for gating')
            st.write(research['audit_start'],research['audit_end'])
            st.json(research['audit']['metrics'])
            st.dataframe(monthly64(research['audit']['trades']),hide_index=True)
            if not selected['ml'].empty: st.dataframe(selected['ml'],hide_index=True)
            st.download_button('Download outer-validation trades',selected['trades'].to_csv(index=False),'v64_development_trades.csv')
            if st.button('Freeze for future PAPER only',disabled=True):
                service.repo.set_active_strategy(FAMILY64,research['payload'],report,True)
                st.success('Parameter version frozen and activated; future outcomes are recorded only.')
                st.rerun()
            st.info('This research validates base V6.4 families, not the combined scalper. It cannot establish a scalp PASS.')
        if active and st.button('Deactivate model; continue protective management'):
            service.repo.deactivate_strategy(); st.rerun()
    with tabs[3]:
        if result:
            st.metric('Current regime',result['regime'])
            ev=result['regime_evidence']
            if len(ev):
                st.metric('Feature completeness',f'{ev.completeness_pct.iloc[-1]:.0f}%')
                st.caption('Feature completeness is not probability. The classifier uses fixed, interpretable rules.')
                st.dataframe(ev[['adx14','ema_slope','ema_separation','atr_pct','atr_cut','bb_width','vol20','roc10','session64']].tail(1))
                changes=ev.loc[ev.regime_closed.ne(ev.regime_closed.shift(1)),['regime_closed']].tail(20).copy()
                changes['Istanbul']=changes.index.tz_convert('Europe/Istanbul').astype(str)
                st.dataframe(changes)
            routes=json.loads(active.params_json).get('routes',{}) if active else {}
            for side in ('BUY','SELL'):
                st.write(side,routes.get(f'{result["regime"]}|{side}',{'family':'NONE'}))
        else: st.info('Regime evidence appears after a data cycle.')
    with tabs[4]:
        st.dataframe(pd.DataFrame([dict(timestamp=c.created_at,source=c.source,side=c.side,status=c.status,
                                      entry=c.entry_reference,stop=c.sl,reason=c.reasons_json)
                                   for c in service.repo.recent_candidates(100)]),hide_index=True)
    positions=service.repo.all_positions(service.account.id)
    with tabs[5]:
        st.dataframe(pd.DataFrame([dict(id=p.id,side=p.side,policy=p.quote_policy,status=p.status,entry=p.entry,
                                      stop=p.sl_current,original_lot=p.original_lot,remaining_lot=p.remaining_lot,
                                      **{f'TP{i}':getattr(p,f'tp{i}') for i in range(1,6)},
                                      pnl=p.realized_pnl,opened=p.opened_at,closed=p.closed_at) for p in positions]),hide_index=True)
    with tabs[6]:
        events=service.repo.events()
        journal=pd.DataFrame([dict(timestamp=e.occurred_at,position=e.position_id,event=e.event_type,
                                   price=e.price,quantity=e.quantity,pnl=e.pnl,details=e.details_json) for e in events])
        st.dataframe(journal,hide_index=True)
        st.download_button('Download Journal',journal.to_csv(index=False),'v64_forward_journal.csv')
    with tabs[7]:
        st.subheader('Forward PAPER validation — future outcomes are excluded from fitting')
        st.json(summarize(positions))
        st.caption('Starting equity is manually configured; P/L is recorded separately. Account returns require reconciling capital and transfers. These are simulated fills.')
    with tabs[8]:
        st.write('Max 2 global positions, 1 own position; 2% per-trade / 4% aggregate risk; 3% daily drawdown; 5-minute fill spacing; freshness, spread, duplicate and kill-switch controls.')
        st.write('TP1: SL to TP1; TP2: hold; TP3: close 0.015; TP4: SL to TP3; TP5: close remainder. Stops are checked before targets.')
        st.caption('OHLC PAPER management is approximate. Stop amendments apply from the next candle. Monitoring runs only in an active session.')
    with tabs[10]:
        render_news65(service)
    with tabs[11]:
        render_health65(service,monitoring,panel='health')
    with tabs[12]:
        render_lab66(service,result)
    with tabs[9]:
        st.write('Telegram: DISABLED · cTrader: DISABLED · live broker execution: DISABLED')
        st.code('TWELVEDATA_API_KEY = "YOUR_KEY"\n# DATABASE_URL = "postgresql+psycopg2://user:password@host/db"',language='toml')
        st.write('Entrypoint: app.py · Python 3.11/3.12 · Store: gold_v6_5_scalp_paper.db')



EXPERIMENT_VERSION64='paper-preset-v1-unvalidated'

def paper_active64(active, policy):
    if active is None or active.family!=FAMILY64:return False
    if active.gate_pass:return True
    try:
        params=json.loads(active.params_json)
        metrics=json.loads(active.metrics_json)
    except Exception:return False
    return bool(policy==QuotePolicy.REFERENCE_SIMULATION and params.get('paper_experiment')
                and params.get('parameter_version')==EXPERIMENT_VERSION64
                and metrics.get('paper_only') and not metrics.get('pass_gate'))

def preset_paper64():
    # Declared illustrative presets; not fitted to the observed audit window.
    routes={
        'TREND_UP|BUY':dict(family='EMA Pullback',params=dict(fast=20,slow=100,adx=20,rsi_l=45,rsi_s=55,sl=1.5,rr=2.)),
        'TREND_DOWN|SELL':dict(family='EMA Pullback',params=dict(fast=20,slow=100,adx=23,rsi_l=50,rsi_s=50,sl=1.8,rr=2.)),
        'RANGE|BUY':dict(family='Bollinger Mean Reversion',params=dict(n=20,std=2.,rsi_lo=30,rsi_hi=70,adx_max=25,sl=1.5,rr=1.5)),
        'RANGE|SELL':dict(family='Bollinger Mean Reversion',params=dict(n=20,std=2.2,rsi_lo=28,rsi_hi=72,adx_max=23,sl=1.8,rr=1.5))}
    for config in routes.values():config.update(validated=False,paper_only=True)
    return dict(routes=routes,_timeframe='15m',paper_experiment=True,parameter_version=EXPERIMENT_VERSION64,
                frozen_at=utcnow().isoformat(),method='UNVALIDATED_EXPLICIT_PAPER_PRESET')

def start_paper64(self):
    params=preset_paper64()
    return _activate63(self.repo,FAMILY64,params,dict(pass_gate=False,paper_only=True,target_status='NOT TESTED',
                                                   warning='UNVALIDATED PAPER EXPERIMENT'),False)

def ensure_paper64(self):
    # Initialize once only. Deactivation must persist across reruns/restarts.
    with self.sessions() as session:exists=session.get(ActiveStrategyModel,1)
    if exists is None:self.start_paper_experiment()

CoreService.start_paper_experiment=start_paper64
CoreService.ensure_paper_experiment=ensure_paper64

# ===== V6.5 5m scalp PAPER, diagnostics and economic-calendar guard =====
EXPERIMENT_VERSION64='v6.5-scalp-preset-1-unvalidated'
SCALP_FAMILIES65=('Scalp Breakout','Scalp Retest','Scalp Rejection')
CALENDAR_URL65='https://nfs.faireconomy.media/ff_calendar_thisweek.json'

class CycleState65(Base):
    __tablename__='cycle_health_v65'
    id: Mapped[int] = mapped_column(Integer,primary_key=True)
    attempts: Mapped[int] = mapped_column(Integer,default=0)
    successes: Mapped[int] = mapped_column(Integer,default=0)
    failures: Mapped[int] = mapped_column(Integer,default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(40),default='NOT_STARTED')
    diagnostics: Mapped[str] = mapped_column(Text,default='{}')


def heartbeat65(service,status,details=None,start=False,success=False):
    now=utcnow()
    with service.sessions.begin() as session:
        obj=session.get(CycleState65,1)
        if obj is None:
            obj=CycleState65(id=1,attempts=0,successes=0,failures=0,diagnostics='{}');session.add(obj)
        if start:
            obj.attempts+=1;obj.started_at=now
        else:
            obj.completed_at=now
            if success:obj.successes+=1;obj.success_at=now
            elif status=='ERROR':obj.failures+=1
        obj.status=status
        if details is not None:obj.diagnostics=json.dumps(details,default=str,ensure_ascii=False)


def get_health65(service):
    with service.sessions() as session:
        obj=session.get(CycleState65,1)
        if obj is None:return dict(status='NOT_STARTED',attempts=0,successes=0,failures=0)
        age=(utcnow()-_utc(obj.success_at)).total_seconds() if obj.success_at else None
        return dict(status=obj.status,attempts=obj.attempts,successes=obj.successes,failures=obj.failures,
                    last_attempt=str(_utc(obj.started_at)),last_success=str(_utc(obj.success_at)),
                    success_age_seconds=age,details=json.loads(obj.diagnostics or '{}'))


def parse_calendar65(rows,now=None):
    """Only explicit-offset timestamps; provider forecast/actual never drives trades."""
    now=pd.Timestamp(now or utcnow()).tz_convert('UTC')
    if not isinstance(rows,list) or not rows or len(rows)>5000:raise ValueError('CALENDAR_SCHEMA_INVALID')
    parsed=[]
    for r in rows:
        if not isinstance(r,dict):raise ValueError('CALENDAR_SCHEMA_INVALID')
        if not all(k in r for k in ('title','country','date','impact')):raise ValueError('CALENDAR_SCHEMA_INVALID')
        ts=pd.Timestamp(r['date'])
        if pd.isna(ts) or ts.tzinfo is None:raise ValueError('CALENDAR_TIMEZONE_UNKNOWN')
        parsed.append(dict(title=str(r['title'])[:250],currency=str(r['country']).upper(),
                           time_utc=ts.tz_convert('UTC'),impact=str(r['impact']).upper()))
    events=pd.DataFrame(parsed).sort_values('time_utc')
    # Export week is Sunday-to-Saturday in New York time, not computer locale.
    local=now.tz_convert('America/New_York')
    start=local.normalize()-pd.Timedelta(days=(local.weekday()+1)%7)
    end=start+pd.DateOffset(days=7)
    if not events.time_utc.between(start.tz_convert('UTC'),end.tz_convert('UTC'),inclusive='left').any():
        raise ValueError('CALENDAR_WEEK_STALE')
    return dict(events=events,coverage_start=start.tz_convert('UTC'),coverage_end=end.tz_convert('UTC'),
                fetched_at=now,status='OK',source='Forex Factory weekly JSON export')


@st.cache_data(ttl=600,show_spinner=False)
def fetch_calendar65(week_key):
    try:
        response=requests.get(CALENDAR_URL65,timeout=10,headers={'Accept':'application/json'},allow_redirects=False)
        if response.status_code!=200 or len(response.content)>2_000_000:raise ValueError('CALENDAR_UNAVAILABLE')
        return parse_calendar65(response.json())
    except Exception:
        return dict(status='UNAVAILABLE',events=pd.DataFrame(),fetched_at=pd.Timestamp.now(tz='UTC'),
                    source='Forex Factory weekly export',error='Calendar unavailable, invalid or stale; no raw provider errors shown')


def news_gate65(calendar,now=None,allow_unknown=False):
    now=pd.Timestamp(now or utcnow()).tz_convert('UTC')
    known=calendar.get('status')=='OK'
    if known:
        age=(now-calendar['fetched_at']).total_seconds()
        known=0<=age<=1200 and calendar['coverage_start']<=now<calendar['coverage_end']
    if not known:
        return dict(allowed=bool(allow_unknown),status='UNPROTECTED_OPT_IN' if allow_unknown else 'NEWS_DATA_UNKNOWN',
                    reasons=['Calendar unavailable; no news protection' if allow_unknown else 'Entry blocked: calendar unavailable or stale'],events=[])
    events=calendar['events']
    relevant=events[events.currency.isin(['USD','ALL']) & events.impact.isin(['HIGH','MEDIUM'])]
    # +/-20 minutes for scheduled HIGH/MEDIUM USD/ALL events.
    nearby=relevant[(relevant.time_utc>=now-pd.Timedelta(minutes=20)) & (relevant.time_utc<=now+pd.Timedelta(minutes=20))]
    return dict(allowed=nearby.empty,status='CLEAR' if nearby.empty else 'NEWS_BLACKOUT',
                reasons=['Important release window: new entries blocked'] if len(nearby) else ['Outside scheduled news blackout'],
                events=nearby.to_dict('records'))


def calendar_for65(service):
    injected=getattr(service,'calendar_override65',None)
    if injected is not None:return injected
    key=pd.Timestamp.now(tz='America/New_York').strftime('%Y-%U')
    return fetch_calendar65(key)


@st.cache_data(ttl=310,show_spinner=False)
def cached_bars65(_client,interval,count,bucket,identity):
    return _client.fetch_candles(interval,count)


def market_scalp65(self):
    quote=self.market.fetch_reference_quote()
    now=pd.Timestamp.now(tz='UTC')
    # Client cache keyed by credential digest, never raw keys in log/error messages.
    identity=hashlib.sha256((self.settings.symbol+self.settings.twelve_data_api_key).encode()).hexdigest()
    base=_closed_only(cached_bars65(self.market,'5min',4800,str(now.floor('5min')),identity),5)
    minute=_closed_only(cached_bars65(self.market,'1min',500,str(now.floor('min')),identity),1)
    frames={'5m':base,'1m':minute,'15m':resample_ohlc_strict(base,'15min',3),
            '30m':resample_ohlc_strict(base,'30min',6),'1h':resample_ohlc_strict(base,'1h',12)}
    self.repo.save_market_snapshot(quote)
    return quote,frames

CoreService.fetch_market=market_scalp65


def scalp_features65(primary,context15):
    x=add_features(primary.copy())
    y=regime_evidence64(add_features(context15))
    available=y[['regime_closed','completeness_pct']].copy()
    available.index=available.index+pd.Timedelta(minutes=15)
    available.index.name='available_at'
    decision=pd.DataFrame({'available_at':x.index+pd.Timedelta(minutes=5)},index=x.index)
    m=pd.merge_asof(decision.reset_index(drop=True).sort_values('available_at'),
                    available.reset_index().sort_values('available_at'),on='available_at',direction='backward')
    x['regime15']=m.regime_closed.fillna('UNKNOWN').to_numpy()
    x['regime_completeness']=m.completeness_pct.fillna(0).to_numpy()
    x['resistance10']=x.high.shift(1).rolling(10,min_periods=10).max()
    x['support10']=x.low.shift(1).rolling(10,min_periods=10).min()
    x['bb_width_previous']=x.bb_width.shift(1).rolling(20,min_periods=10).median()
    if 'volume' not in x:x['volume']=np.nan
    x['volume']=pd.to_numeric(x.volume,errors='coerce').where(lambda v:v>=0)
    reference=x.volume.shift(1).rolling(20,min_periods=20).mean()
    x['relative_volume']=x.volume/reference.replace(0,np.nan)
    x['volume_available']=x.volume.notna() & reference.gt(0)
    return x


def scalp_masks65(x,p,require_volume=False):
    """Three deterministic setups, disjoint regime families and explicit direction."""
    a=x.atr14
    ready=x[['rsi14','atr14','resistance10','support10','bb_width_previous']].notna().all(axis=1)&a.gt(0)
    vol=(x.volume_available & x.relative_volume.ge(1.1)) if require_volume else pd.Series(True,index=x.index)
    rsil=x.rsi14.between(p.get('rsi_buy_min',52),p.get('rsi_buy_max',75))
    rsis=x.rsi14.between(p.get('rsi_sell_min',25),p.get('rsi_sell_max',48))
    body=x.body_pct.ge(.5)
    bbexp=x.bb_width.ge(.8*x.bb_width_previous)&x.bb_width.gt(x.bb_width.shift(1))
    margin=p.get('buffer',.1)*a
    up=x.regime15.eq('TREND_UP');down=x.regime15.eq('TREND_DOWN');rang=x.regime15.eq('RANGE')
    breakout_buy=ready&vol&up&rsil&body&bbexp&x.close.gt(x.open)&x.close.gt(x.resistance10+margin)&x.close.gt(x.bb_mid)
    breakout_sell=ready&vol&down&rsis&body&bbexp&x.close.lt(x.open)&x.close.lt(x.support10-margin)&x.close.lt(x.bb_mid)
    # Previous bar break level is frozen before its breakout; current bar tests it.
    prior_hi=x.resistance10.shift(1);prior_lo=x.support10.shift(1)
    was_up=x.close.shift(1).gt(prior_hi+p.get('buffer',.1)*a.shift(1))
    was_dn=x.close.shift(1).lt(prior_lo-p.get('buffer',.1)*a.shift(1))
    retest_buy=ready&vol&up&rsil&was_up&x.low.le(prior_hi+.15*a)&x.low.ge(prior_hi-.3*a)&x.close.gt(prior_hi)&x.close.gt(x.open)
    retest_sell=ready&vol&down&rsis&was_dn&x.high.ge(prior_lo-.15*a)&x.high.le(prior_lo+.3*a)&x.close.lt(prior_lo)&x.close.lt(x.open)
    bull=x.bull_pin|x.bull_engulf
    bear=x.bear_pin|x.bear_engulf
    rejection_buy=ready&vol&rang&bull&x.rsi14.le(45)&x.low.le(x.support10+.2*a)&x.low.le(x.bb_dn)&x.close.gt(x.bb_dn)&x.close.gt(x.open)
    rejection_sell=ready&vol&rang&bear&x.rsi14.ge(55)&x.high.ge(x.resistance10-.2*a)&x.high.ge(x.bb_up)&x.close.lt(x.bb_up)&x.close.lt(x.open)
    return {'Scalp Breakout':(breakout_buy,breakout_sell),'Scalp Retest':(retest_buy,retest_sell),
            'Scalp Rejection':(rejection_buy,rejection_sell)}


def scalp_signal65(x,params,options=None):
    options=options or {}
    routes=params.get('routes',{})
    hits=[]
    row=x.iloc[-1]
    evidence={k:float(row[k]) if pd.notna(row[k]) else None for k in
              ['rsi14','atr14','adx14','stoch14','macd_hist','roc10','ema20','ema50','ema100','bb_mid','bb_up','bb_dn','bb_width','resistance10','support10','relative_volume','body_pct']}
    evidence.update(regime15=str(row.regime15),volume_status='PROVIDER_VOLUME_AVAILABLE' if row.volume_available else 'UNAVAILABLE',
                    volume_required=bool(options.get('require_volume')),session_utc=int(x.index[-1].hour))
    if row.regime15=='UNKNOWN':return dict(side=0,reason='REGIME_DATA_INCOMPLETE',evidence=evidence)
    if row.regime15=='VOLATILE':return dict(side=0,reason='VOLATILE_REGIME_BLOCK',evidence=evidence)
    if options.get('require_volume') and not row.volume_available:
        return dict(side=0,reason='VOLUME_REQUIRED_BUT_UNAVAILABLE',evidence=evidence)
    session=options.get('session','ALL')
    hour=(x.index[-1]+pd.Timedelta(minutes=5)).hour
    if session!='ALL' and not {'LONDON':7<=hour<=15,'NEW_YORK':12<=hour<=20,'OVERLAP':12<=hour<=15}.get(session,False):
        return dict(side=0,reason='SESSION_FILTER_BLOCK',evidence=evidence)
    masks=[]
    for key,config in routes.items():
        reg,side=key.split('|')
        if reg!=row.regime15:continue
        for family in SCALP_FAMILIES65:
            buys,sells=scalp_masks65(x,config['params'],options.get('require_volume',False))[family]
            eligible=family in config['setups']
            passed=bool((buys if side=='BUY' else sells).iloc[-1]) and eligible
            masks.append(dict(family=family,side=side,eligible=eligible,passed=passed))
            if passed:hits.append((1 if side=='BUY' else -1,family,config['params']))
    evidence['setup_checks']=masks
    evidence['rule_checks']=dict(bullish_pattern=bool(row.bull_pin or row.bull_engulf),bearish_pattern=bool(row.bear_pin or row.bear_engulf),
        body_ge_50pct=bool(row.body_pct>=.5),close_above_bb_mid=bool(row.close>row.bb_mid),close_below_bb_mid=bool(row.close<row.bb_mid),
        buy_rsi_52_to_75=bool(52<=row.rsi14<=75),sell_rsi_25_to_48=bool(25<=row.rsi14<=48),
        close_above_prior_resistance=bool(row.close>row.resistance10),close_below_prior_support=bool(row.close<row.support10),
        range_buy_rsi_le45=bool(row.rsi14<=45),range_sell_rsi_ge55=bool(row.rsi14>=55),
        lower_band_touched=bool(row.low<=row.bb_dn),upper_band_touched=bool(row.high>=row.bb_up))
    if not hits:return dict(side=0,reason='NO_CONFIRMED_5M_SETUP',evidence=evidence)
    if len({h[0] for h in hits})>1:return dict(side=0,reason='CONFLICTING_DIRECTIONS',evidence=evidence)
    # Prefer a successful retest when both same-direction rules coincide. No voting.
    hits.sort(key=lambda h:SCALP_FAMILIES65.index(h[1]) if h[1]!='Scalp Retest' else -1)
    side,family,p=hits[0]
    return dict(side=side,family=family,params=dict(p),reason='CONFIRMED_'+family.replace(' ','_').upper(),evidence=evidence)


def preset_paper64():
    routes={}
    buy=dict(buffer=.1,rsi_buy_min=52,rsi_buy_max=75,rsi_sell_min=25,rsi_sell_max=48,sl=1.3,rr=1.2)
    sell=dict(buffer=.15,rsi_buy_min=52,rsi_buy_max=75,rsi_sell_min=25,rsi_sell_max=48,sl=1.5,rr=1.3)
    for regime,side,p,setups in [('TREND_UP','BUY',buy,['Scalp Breakout','Scalp Retest']),
                                 ('TREND_DOWN','SELL',sell,['Scalp Breakout','Scalp Retest']),
                                 ('RANGE','BUY',buy,['Scalp Rejection']),('RANGE','SELL',sell,['Scalp Rejection'])]:
        routes[f'{regime}|{side}']=dict(family='Scalp Composite',params=p,setups=setups,validated=False,paper_only=True)
    return dict(routes=routes,_timeframe='5m',paper_experiment=True,scalp65=True,parameter_version=EXPERIMENT_VERSION64,
                frozen_at=utcnow().isoformat(),method='UNVALIDATED_5M_SCALP_PAPER')


def protective65(self,frames):
    for p in self.repo.open_positions(self.account.id):
        self.execution.replay_bars(p.id,frames['1m'])
        current=self.repo.get_position(p.id)
        events=self.repo.events(p.id)
        entry=next((json.loads(e.details_json) for e in reversed(events) if e.event_type=='REGIME_ENTRY'),{})
        context=regime_evidence64(add_features(frames['15m']))
        reg=context.regime_closed.copy();reg.index=reg.index+pd.Timedelta(minutes=15)
        stop=pd.Timestamp(_utc(current.closed_at)) if current.closed_at else pd.Timestamp.now(tz='UTC')
        known=reg.loc[:stop];at_exit=str(known.iloc[-1]) if len(known) else 'UNKNOWN'
        during=reg.loc[pd.Timestamp(_utc(p.opened_at)):stop]
        details=dict(regime=at_exit,regime_at_exit=at_exit if current.status=='CLOSED' else None,
                     regime_changed=bool((during!=entry.get('regime')).any()),result=current.status,
                     pnl=str(current.realized_pnl),r_multiple=str(Decimal(current.realized_pnl)/Decimal(current.frozen_initial_risk_usd)) if current.frozen_initial_risk_usd else None)
        self.repo.add_event(p.id,f'{p.id}:SCALP_REGIME:{frames["1m"].index[-1]}','REGIME_OBSERVATION',utcnow(),details=details)


def make_scalp_plan65(self,signal,x,quote,cid):
    side=Side.BUY if signal['side']==1 else Side.SELL
    p=dict(signal['params']);a=Decimal(str(x.atr14.iloc[-1]));entry=quote.reference_price
    if a<=0:return None,'INVALID_ATR'
    row=x.iloc[-1]
    structure=(Decimal(str(row.low))-a*Decimal('.15')) if side==Side.BUY else (Decimal(str(row.high))+a*Decimal('.15'))
    structure_dist=entry-structure if side==Side.BUY else structure-entry
    distance=max(a*Decimal(str(p['sl'])),structure_dist)
    costs=self.settings.reference_assumed_spread_usd+2*self.settings.reference_slippage_usd
    if distance>3*a:return None,'STOP_TOO_WIDE'
    if distance<costs*Decimal('2.5'):return None,'STOP_TOO_SMALL_FOR_COSTS'
    if distance*Decimal(str(p['rr']))*Decimal('.4')<costs*Decimal('1.5'):return None,'TP1_TOO_SMALL_FOR_COSTS'
    if abs(entry-Decimal(str(row.close)))>a*Decimal('.4'):return None,'PRICE_MOVED_TOO_FAR_AFTER_SIGNAL'
    p['sl']=float(distance/a)
    plan=build_research_trade_plan(cid,side,entry,a,p,Decimal(self.account.equity),self.settings.quote_policy,
                                    self.settings.fixed_lot,self.settings.contract_oz_per_lot,False)
    from dataclasses import replace
    plan=replace(plan,source='PAPER_EXPERIMENT',research_authorized=True,
                 reasons_for=(signal['reason'],),reasons_against=('UNVALIDATED 5m SCALP PAPER',),
                 plan_hash=hashlib.sha256((plan.plan_hash+EXPERIMENT_VERSION64).encode()).hexdigest())
    return plan,None


def finish65(self,out,reason):
    out['no_entry_reason']=reason
    q=out['quote'];frames=out['frames'];now=utcnow()
    details=dict(reason=reason,regime=out['regime'],signal=out.get('strategy_signal',0),
                 quote_received_at=q.received_timestamp.isoformat(),quote_age_seconds=(now-q.received_timestamp).total_seconds(),
                 closed_5m_at=str(frames['5m'].index[-1]+pd.Timedelta(minutes=5)),
                 closed_1m_at=str(frames['1m'].index[-1]+pd.Timedelta(minutes=1)),
                 age_5m_seconds=(pd.Timestamp(now)-frames['5m'].index[-1]-pd.Timedelta(minutes=5)).total_seconds(),
                 age_1m_seconds=(pd.Timestamp(now)-frames['1m'].index[-1]-pd.Timedelta(minutes=1)).total_seconds(),
                 news=out['news_gate']['status'],volume=out.get('signal_evidence',{}).get('volume_status'),
                 fill_position=out['position'].id if out.get('position') else None)
    heartbeat65(self,'OK',details,success=True)
    return out


def run_scalp65(self,*,allow_execution):
    heartbeat65(self,'RUNNING',start=True)
    try:
        self.account=self.repo.get_account(self.account.id)
        quote,frames=self.fetch_market()
        if any(frames[k].empty for k in ('1m','5m','15m')):raise ValueError('EMPTY_CANDLES')
        # Managing OPEN positions precedes all new-entry news/volume/model gates.
        protective65(self,frames)
        x=scalp_features65(frames['5m'],frames['15m'])
        active=self._active_strategy_payload();opts=getattr(self,'scalp_options',{})
        calendar=calendar_for65(self);news=news_gate65(calendar,allow_unknown=opts.get('allow_no_news',False))
        evidence=regime_evidence64(add_features(frames['15m']))
        regime=str(x.regime15.iloc[-1])
        bundle=self.analyze(frames)
        out=dict(quote=quote,frames=frames,bundle=bundle,evaluation=evaluate(bundle),regime=regime,
                 regime_evidence=evidence,scalp_features=x,calendar=calendar,news_gate=news,
                 active_strategy=active,strategy_evaluation=None,strategy_signal=0,candidate_id=None,
                 plan=None,risk=None,position=None,signal_evidence={})
        if not active or not active['params'].get('scalp65'):return finish65(self,out,'NO_ACTIVE_SCALP_PRESET')
        if self.settings.quote_policy!=QuotePolicy.REFERENCE_SIMULATION:return finish65(self,out,'SCALP_EXPERIMENT_REQUIRES_REFERENCE_SIMULATION')
        now=pd.Timestamp.now(tz='UTC');close=x.index[-1]+pd.Timedelta(minutes=5)
        minute_close=frames['1m'].index[-1]+pd.Timedelta(minutes=1)
        if not 0<=(now-close).total_seconds()<=360:return finish65(self,out,'FIVE_MINUTE_DATA_STALE')
        if not 0<=(now-minute_close).total_seconds()<=180:return finish65(self,out,'ONE_MINUTE_DATA_STALE')
        signal=scalp_signal65(x,active['params'],opts)
        out['signal_evidence']=signal['evidence'];out['strategy_signal']=signal['side']
        if signal['side']==0:return finish65(self,out,signal['reason'])
        side=Side.BUY if signal['side']==1 else Side.SELL
        cid=self._research_candidate_id(frames['5m'],'5m',signal['family'],side,active)
        ev=SignalEvaluation(side,100 if side==Side.BUY else 0,100 if side==Side.SELL else 0,100,60,Grade.B,
                            CandidateStatus.WATCH_ONLY,(),(signal['reason'],),('UNVALIDATED SCALP PAPER',),utcnow())
        plan,block=make_scalp_plan65(self,signal,x,quote,cid)
        out.update(strategy_evaluation=ev,candidate_id=cid,plan=plan)
        self.repo.save_candidate(cid,ev,plan,source='PAPER_EXPERIMENT')
        if block:return finish65(self,out,block)
        if not news['allowed']:return finish65(self,out,news['status'])
        risk=self.risk.assess(self.account,plan,quote,minute_close.to_pydatetime());out['risk']=risk
        if not risk.approved:return finish65(self,out,'RISK_BLOCK: '+','.join(risk.reason_codes))
        if not allow_execution:return finish65(self,out,'EXECUTION_DISABLED_MONITOR_ONLY')
        self.execution.latest_closed_1m_at=minute_close.to_pydatetime()
        self.execution.route_context=dict(regime=regime,timeframe='5m',active_strategy=signal['family'],side=side.value,
                  signal_reason=signal['reason'],parameter_version=EXPERIMENT_VERSION64,unvalidated_experiment=True,
                  evidence=signal['evidence'],news_status=news['status'],calendar_source=calendar.get('source'),
                  news_events=news['events'],session_filter=opts.get('session','ALL'))
        # Check time-dependent news gate again just before the execution engine.
        self.execution.entry_guard65=lambda:news_gate65(calendar,allow_unknown=opts.get('allow_no_news',False))['allowed']
        out['position']=self.execution.execute(self.account,plan,risk,quote)
        return finish65(self,out,'PAPER_POSITION_OPENED')
    except Exception as exc:
        # Allow-list internal codes only; never include arbitrary exceptions/URLs.
        code=str(exc) if isinstance(exc,ValueError) and str(exc) in {'EMPTY_CANDLES','CALENDAR_SCHEMA_INVALID'} else type(exc).__name__
        heartbeat65(self,'ERROR',dict(reason='CYCLE_FAILED',error_code=code,managed_entries_disabled=True))
        raise RuntimeError('SCALP_CYCLE_FAILED — inspect Cycle Health') from None

CoreService.run_once=run_scalp65

_execute_before65=PaperExecutionEngine.execute

def guarded_execute65(self,account,plan,decision,quote):
    with _EXECUTION_LOCK64:
        guard=getattr(self,'entry_guard65',None)
        if guard is not None and not guard():raise RuntimeError('NEWS_RECHECK_BLOCK')
        return _execute_before65(self,account,plan,decision,quote)

PaperExecutionEngine.execute=guarded_execute65


def render_health65(service,monitoring):
    h=get_health65(service)
    a,b,c=st.columns(3)
    a.metric('Successful cycles',h['successes']);b.metric('Failed cycles',h['failures'])
    age=h.get('success_age_seconds')
    c.metric('Seconds since last success','—' if age is None else f'{age:.0f}')
    if h['status']=='ERROR':st.error('Latest cycle failed. NONE does not prove cycle health.')
    elif not monitoring:st.info('Automatic monitoring is stopped.')
    elif age is not None and age>120:st.warning('Heartbeat is stale; current cycle health is unconfirmed.')
    elif h['status']=='OK':st.success('Data and evaluation cycle succeeded. This does not confirm profitability.')
    else:st.info('No successful cycle recorded yet.')
    st.write('Last success UTC:',h.get('last_success','—'))
    if h.get('last_success') and h['last_success']!='None':
        st.caption('Istanbul: '+str(pd.Timestamp(h['last_success']).tz_convert('Europe/Istanbul')))
    if h.get('details'):st.json(h['details'])


def render_scalp_snapshot65(result,settings):
    q=result['quote'];signal=result.get('strategy_signal',0)
    a,b,c=st.columns(3)
    a.metric('Actual reference price',f'{q.reference_price:,.2f}')
    b.metric('Signal','BUY' if signal>0 else 'SELL' if signal<0 else 'NONE')
    c.metric('Model status','UNVALIDATED PAPER')
    st.write('News:',result['news_gate']['status'])
    if result.get('signal_evidence'):st.write('Volume:',result['signal_evidence'].get('volume_status'))
    plan=result.get('plan')
    if plan:
        st.write('Entry:',float(plan.entry_reference),'Stop:',float(plan.initial_sl))
        st.write({f'TP{i}':float(v) for i,v in enumerate(plan.provisional_targets,1)})
        st.write('Risk USD:',float(plan.gross_risk_usd),'Risk %:',float(plan.risk_pct))
    if result.get('position'):st.success(f'موقعیت شبیه‌سازی‌شده #{result["position"].id} ثبت شد.')
    if result.get('risk') and not result['risk'].approved:st.warning(', '.join(result['risk'].reason_codes))
    if not result['news_gate']['allowed']:st.warning('News guard blocks new entries. Existing positions remain eligible for protective management.')


def render_news65(service):
    calendar=calendar_for65(service)
    gate=news_gate65(calendar,allow_unknown=getattr(service,'scalp_options',{}).get('allow_no_news',False))
    st.write('Source:',calendar.get('source'),'Status:',gate['status'])
    st.caption('Scheduled releases only; no sentiment, directional forecast or unexpected-news coverage. USD/ALL HIGH/MEDIUM events block entries 20 minutes before and after.')
    events=calendar.get('events',pd.DataFrame())
    if len(events):
        show=events[events.currency.isin(['USD','ALL'])].copy()
        show['Istanbul']=pd.to_datetime(show.time_utc,utc=True).dt.tz_convert('Europe/Istanbul').astype(str)
        st.dataframe(show,hide_index=True)
    else:st.warning('Calendar unavailable; default policy blocks new entries.')
    if gate['status']=='UNPROTECTED_OPT_IN':st.warning('You enabled PAPER without news protection. This is recorded in the Journal.')
    st.caption('No extra API key required. Official Forex Factory JSON export; feed availability or schema changes can stop entries.')


def scalp_chart65(x):
    from plotly.subplots import make_subplots
    import plotly.graph_objects as go
    fig=make_subplots(rows=3,cols=1,shared_xaxes=True,row_heights=[.6,.25,.15],vertical_spacing=.04)
    fig.add_trace(go.Candlestick(x=x.index,open=x.open,high=x.high,low=x.low,close=x.close,name='XAU/USD 5m'),row=1,col=1)
    for col in ['bb_up','bb_mid','bb_dn','ema20','resistance10','support10']:
        fig.add_trace(go.Scatter(x=x.index,y=x[col],mode='lines',name=col),row=1,col=1)
    fig.add_trace(go.Scatter(x=x.index,y=x.rsi14,name='RSI14'),row=2,col=1)
    fig.add_hline(y=30,row=2,col=1);fig.add_hline(y=70,row=2,col=1)
    if x.volume_available.any():fig.add_trace(go.Bar(x=x.index,y=x.volume,name='Provider volume (not consolidated gold volume)'),row=3,col=1)
    else:fig.add_annotation(text='VOLUME UNAVAILABLE — no fabricated values',xref='paper',yref='paper',x=.5,y=.05,showarrow=False)
    fig.update_layout(height=480,xaxis_rangeslider_visible=False,margin=dict(l=10,r=10,t=20,b=10))
    return fig


# ===== V6.6 observable PAPER and independent diagnostic lab =====
class CandleAudit66(Base):
    __tablename__='scalp_candle_audit_v66'
    id: Mapped[str] = mapped_column(String(180),primary_key=True)
    account_id: Mapped[int] = mapped_column(Integer,index=True)
    candle_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str] = mapped_column(String(300))
    signal: Mapped[int] = mapped_column(Integer,default=0)
    attempts: Mapped[int] = mapped_column(Integer,default=0)
    signal_seen: Mapped[bool] = mapped_column(Boolean,default=False)
    news_block: Mapped[bool] = mapped_column(Boolean,default=False)
    risk_block: Mapped[bool] = mapped_column(Boolean,default=False)
    plan_block: Mapped[bool] = mapped_column(Boolean,default=False)
    filled: Mapped[bool] = mapped_column(Boolean,default=False)
    details_json: Mapped[str] = mapped_column(Text,default='{}')

REASONS66={
 'NO_CONFIRMED_5M_SETUP':'No eligible setup satisfies every entry condition.',
 'PAPER_POSITION_OPENED':'A simulated position was opened after risk approval.',
 'NO_ACTIVE_SCALP_PRESET':'No active scalp preset; new entries are disabled.',
 'VOLATILE_REGIME_BLOCK':'VOLATILE regime: current preset blocks new entries.',
 'REGIME_DATA_INCOMPLETE':'Regime data is incomplete.',
 'VOLUME_REQUIRED_BUT_UNAVAILABLE':'Volume is required, but valid provider data is unavailable.',
 'SESSION_FILTER_BLOCK':'Outside the selected UTC session.',
 'FIVE_MINUTE_DATA_STALE':'The latest closed five-minute candle is stale.',
 'ONE_MINUTE_DATA_STALE':'One-minute data is stale for entries and management.',
 'NEWS_DATA_UNKNOWN':'A valid news calendar is unavailable; new entries are blocked.',
 'NEWS_BLACKOUT':'Within a scheduled release blackout window.',
 'EXECUTION_DISABLED_MONITOR_ONLY':'Evaluation completed, but execution is disabled.',
 'STOP_TOO_WIDE':'Stop distance exceeds three ATR.',
 'STOP_TOO_SMALL_FOR_COSTS':'Stop distance is too small relative to costs.',
 'TP1_TOO_SMALL_FOR_COSTS':'TP1 distance is too small relative to costs.',
 'PRICE_MOVED_TOO_FAR_AFTER_SIGNAL':'Reference price moved too far from the signal close.',
 'SCALP_EXPERIMENT_REQUIRES_REFERENCE_SIMULATION':'This experimental preset requires REFERENCE_SIMULATION.'}

def reason_text66(code):
    code=str(code or '')
    if code.startswith('RISK_BLOCK:'):return 'Risk Engine blocked entry: '+code.split(':',1)[1]
    if code.startswith('NEWS_'):return REASONS66.get(code,'News calendar guard blocked entry. See News Calendar for details.')
    return REASONS66.get(code,code)

def diagnostic_rules66(x,params,options=None):
    """Explain exactly the predicates used by scalp_masks65, without changing signals."""
    opts=options or {};r=x.iloc[-1];prior=x.iloc[-2] if len(x)>1 else r;rows=[]
    ready=bool(r[['rsi14','atr14','resistance10','support10','bb_width_previous']].notna().all() and r.atr14>0)
    hour=(x.index[-1]+pd.Timedelta(minutes=5)).hour
    session=opts.get('session','ALL');sess=session=='ALL' or {'LONDON':7<=hour<=15,'NEW_YORK':12<=hour<=20,'OVERLAP':12<=hour<=15}.get(session,False)
    for key,cfg in params.get('routes',{}).items():
        reg,side=key.split('|');p=cfg['params'];buy=side=='BUY';a=r.atr14
        masks=scalp_masks65(x,p,opts.get('require_volume',False))
        for family in SCALP_FAMILIES65:
            if family not in cfg.get('setups',[]):continue
            checks=[('Eligible regime',r.regime15,reg,r.regime15==reg),('Data readiness',ready,True,ready),('UTC session',hour,session,sess)]
            if opts.get('require_volume'):
                checks.append(('Relative volume',r.relative_volume,'>= 1.1 with valid volume',bool(r.volume_available and r.relative_volume>=1.1)))
            checks.append(('Candle direction',r.close-r.open,'Positive' if buy else 'Negative',r.close>r.open if buy else r.close<r.open))
            if family=='Scalp Rejection':
                checks.extend([('Reversal pattern',bool(r.bull_pin or r.bull_engulf) if buy else bool(r.bear_pin or r.bear_engulf),True,bool(r.bull_pin or r.bull_engulf) if buy else bool(r.bear_pin or r.bear_engulf)),
                  ('RSI',r.rsi14,'≤45' if buy else '≥55',r.rsi14<=45 if buy else r.rsi14>=55),
                  ('Prior support / resistance touch',r.low if buy else r.high,r.support10+.2*a if buy else r.resistance10-.2*a,r.low<=r.support10+.2*a if buy else r.high>=r.resistance10-.2*a),
                  ('Bollinger band touch',r.low if buy else r.high,r.bb_dn if buy else r.bb_up,r.low<=r.bb_dn if buy else r.high>=r.bb_up),
                  ('Close back inside band',r.close,r.bb_dn if buy else r.bb_up,r.close>r.bb_dn if buy else r.close<r.bb_up)])
            else:
                lo=p.get('rsi_buy_min',52) if buy else p.get('rsi_sell_min',25);hi=p.get('rsi_buy_max',75) if buy else p.get('rsi_sell_max',48)
                checks.append(('RSI',r.rsi14,f'{lo} تا {hi}',lo<=r.rsi14<=hi))
                if family=='Scalp Breakout':
                    level=r.resistance10+p.get('buffer',.1)*a if buy else r.support10-p.get('buffer',.1)*a
                    checks.extend([('Body / candle range',r.body_pct,'≥0.5',r.body_pct>=.5),
                     ('Band expansion',r.bb_width,f'≥ {0.8*r.bb_width_previous:.6g} و > {prior.bb_width:.6g}',r.bb_width>=.8*r.bb_width_previous and r.bb_width>prior.bb_width),
                     ('Close beyond prior level + buffer',r.close,level,r.close>level if buy else r.close<level),
                     ('Close versus Bollinger midpoint',r.close,r.bb_mid,r.close>r.bb_mid if buy else r.close<r.bb_mid)])
                else:
                    level=prior.resistance10 if buy else prior.support10
                    was=prior.close>level+p.get('buffer',.1)*prior.atr14 if buy else prior.close<level-p.get('buffer',.1)*prior.atr14
                    touch=(level-.3*a<=r.low<=level+.15*a) if buy else (level-.15*a<=r.high<=level+.3*a)
                    checks.extend([('Previous candle breakout',prior.close,level,was),('Retest tolerance',r.low if buy else r.high,f'{level-.3*a:.4f} تا {level+.15*a:.4f}' if buy else f'{level-.15*a:.4f} تا {level+.3*a:.4f}',touch),('Close holds the broken level',r.close,level,r.close>level if buy else r.close<level)])
            passed=bool((masks[family][0 if buy else 1]).iloc[-1]) and sess and r.regime15==reg
            for name,value,required,ok in checks:
                rows.append(dict(route=key,family=family,condition=name,value=str(value),required=str(required),passed=bool(ok),route_passed=passed))
    return pd.DataFrame(rows)

_finish65_original66=finish65

def finish65(self,out,reason):
    out=_finish65_original66(self,out,reason)
    candle=out['frames']['5m'].index[-1].to_pydatetime()
    active=out.get('active_strategy') or {};version=active.get('params',{}).get('parameter_version','NONE')
    key=f'{self.account.id}:{pd.Timestamp(candle).isoformat()}:{version}'
    with self.sessions.begin() as s:
        row=s.get(CandleAudit66,key)
        if row is None:
            row=CandleAudit66(id=key,account_id=self.account.id,candle_at=candle,updated_at=utcnow(),reason=str(reason)[:300],signal=0,attempts=0,signal_seen=False,news_block=False,risk_block=False,plan_block=False,filled=False,details_json='{}');s.add(row)
        row.updated_at=utcnow();row.attempts+=1;row.reason=str(reason)[:300];row.signal=int(out.get('strategy_signal',0))
        row.signal_seen=row.signal_seen or bool(row.signal)
        row.news_block=row.news_block or str(reason).startswith('NEWS_')
        row.risk_block=row.risk_block or str(reason).startswith('RISK_BLOCK')
        row.plan_block=row.plan_block or reason in {'STOP_TOO_WIDE','STOP_TOO_SMALL_FOR_COSTS','TP1_TOO_SMALL_FOR_COSTS','PRICE_MOVED_TOO_FAR_AFTER_SIGNAL','INVALID_ATR'}
        row.filled=row.filled or out.get('position') is not None
        row.details_json=json.dumps(out.get('signal_evidence',{}),default=str,ensure_ascii=False)
    return out

def audit_frame66(service):
    with service.sessions() as s:
        rows=list(s.scalars(select(CandleAudit66).where(CandleAudit66.account_id==service.account.id).order_by(CandleAudit66.candle_at.desc()).limit(10000)))
    return pd.DataFrame([dict(candle_utc=r.candle_at,updated=r.updated_at,reason=r.reason,reason_text=reason_text66(r.reason),signal=r.signal,attempts=r.attempts,signal_seen=r.signal_seen,news_block=r.news_block,risk_block=r.risk_block,plan_block=r.plan_block,filled=r.filled) for r in rows])

_render_health_original66=render_health65

def render_health65(service,monitoring,panel='live'):
    _render_health_original66(service,monitoring)
    h=get_health65(service)
    st.info(reason_text66(h.get('details',{}).get('reason')))
    audit=audit_frame66(service)
    if len(audit):
        counts={'Unique candle / version checks':len(audit),'Candles with signals':int(audit.signal_seen.sum()),'News blocks':int(audit.news_block.sum()),'Risk blocks':int(audit.risk_block.sum()),'Trade-plan blocks':int(audit.plan_block.sum()),'Candles with a fill':int(audit.filled.sum())}
        st.dataframe(pd.DataFrame(counts.items(),columns=['Stage','Count']),hide_index=True)
        st.caption('Counts start with V6.6; latest 10,000 records. Block categories may overlap. Rechecking a candle/version does not count as a new opportunity.')
        st.download_button('Download entry-decision audit CSV',audit.to_csv(index=False),'v66_candle_audit.csv',key='audit66_'+panel)

# No activation, no fitting, no access to future PAPER outcomes in this replay.
def replay_scalp66(raw,params,options=None,cost=None):
    cost=cost or CostModel();options=options or {}
    raw=ensure_utc_datetime_index(raw)
    if len(raw)<350:raise ValueError('REPLAY_NEEDS_350_BARS')
    x=scalp_features65(raw,resample_ohlc_strict(raw,'15min',3))
    signals=pd.Series(0,index=x.index);stops=pd.Series(1.,index=x.index);rewards=pd.Series(1.,index=x.index);routes={};blocks=[]
    # Vector masks are causal; evaluate each eligible route without O(n²) signal recomputation.
    hits={}
    for key,cfg in params.get('routes',{}).items():
        reg,side=key.split('|');sign=1 if side=='BUY' else -1
        for family,(buys,sells) in scalp_masks65(x,cfg['params'],options.get('require_volume',False)).items():
            if family not in cfg['setups']:continue
            mask=(buys if sign==1 else sells)&x.regime15.eq(reg)
            for i in np.flatnonzero(mask.to_numpy()):hits.setdefault(int(i),[]).append((sign,family,cfg['params']))
    for i,found in sorted(hits.items()):
        if i>=len(x)-2:continue
        if len({v[0] for v in found})!=1:blocks.append(dict(time=x.index[i],reason='CONFLICTING_DIRECTIONS'));continue
        hour=(x.index[i]+pd.Timedelta(minutes=5)).hour;session=options.get('session','ALL')
        if session!='ALL' and not {'LONDON':7<=hour<=15,'NEW_YORK':12<=hour<=20,'OVERLAP':12<=hour<=15}.get(session,False):continue
        found.sort(key=lambda z:-1 if z[1]=='Scalp Retest' else SCALP_FAMILIES65.index(z[1]));side,family,p=found[0];r=x.iloc[i]
        entry=float(x.open.iloc[i+1]);a=float(r.atr14)
        structure=float(r.low)-.15*a if side==1 else float(r.high)+.15*a
        distance=max(a*p['sl'],side*(entry-structure));roundtrip=cost.spread_usd_per_oz+2*cost.slippage_each_side_usd_per_oz
        code=None
        if abs(entry-r.close)>.4*a:code='PRICE_MOVED_TOO_FAR_AFTER_SIGNAL'
        elif distance>3*a:code='STOP_TOO_WIDE'
        elif distance<2.5*roundtrip:code='STOP_TOO_SMALL_FOR_COSTS'
        elif distance*p['rr']*.4<1.5*roundtrip:code='TP1_TOO_SMALL_FOR_COSTS'
        if code:blocks.append(dict(time=x.index[i],reason=code));continue
        # Risk distance is measured from the adverse simulated fill to the structure stop.
        signals.iloc[i]=side;stops.iloc[i]=(distance+cost.half_spread+cost.slippage_each_side_usd_per_oz)/a;rewards.iloc[i]=p['rr'];routes[x.index[i+1]]=(family,str(r.regime15))
    trades,metrics,curve=backtest_v5_lifecycle(x,signals,stops,rewards,cost,max_hold_bars=len(x))
    if len(trades):
        trades['family']=[routes[t][0] for t in trades.entry_time];trades['regime']=[routes[t][1] for t in trades.entry_time]
    return dict(trades=trades,metrics=metrics,curve=curve,signal_count=int(signals.ne(0).sum()),plan_blocks=pd.DataFrame(blocks),features=x)

def position_chart66(x,positions,events):
    import plotly.graph_objects as go
    fig=scalp_chart65(x)
    for p in positions[:10]:
        start=pd.Timestamp(_utc(p.opened_at));end=pd.Timestamp(_utc(p.closed_at)) if p.closed_at else pd.Timestamp(utcnow())
        if end<x.index[0] or start>max(x.index[-1]+pd.Timedelta(minutes=5),pd.Timestamp(utcnow())):continue
        for name,value in [('Entry',p.entry),('SL initial',p.sl_initial)]+[(f'TP{i}',getattr(p,f'tp{i}')) for i in range(1,6)]:
            fig.add_trace(go.Scatter(x=[max(start,x.index[0]),end],y=[float(value)]*2,mode='lines',line=dict(dash='dot'),name=f'#{p.id} {name}'),row=1,col=1)
        for e in events:
            if e.position_id!=p.id:continue
            if e.price is not None:
                fig.add_trace(go.Scatter(x=[_utc(e.occurred_at)],y=[float(e.price)],mode='markers',marker=dict(size=10),text=[f'{e.event_type} qty={e.quantity}'],name=f'#{p.id} {e.event_type}'),row=1,col=1)
        fig.add_trace(go.Scatter(x=[end],y=[float(p.sl_current)],mode='markers',marker=dict(symbol='x',size=12),name=f'#{p.id} SL current'),row=1,col=1)
    return fig

def independent_lab66():
    """Actual signal -> risk -> execution in a temporary, separate database; synthetic quotes."""
    import tempfile
    from dataclasses import replace
    with tempfile.TemporaryDirectory(prefix='gold_lab_') as tmp:
        svc=CoreService(Settings(database_url='sqlite:///'+tmp+'/lab.db',quote_policy=QuotePolicy.REFERENCE_SIMULATION))
        try:
            svc.set_account_controls(Decimal('10000'),True,False);svc.ensure_paper_experiment()
            idx=pd.date_range(end=pd.Timestamp.now(tz='UTC').floor('5min')-pd.Timedelta(minutes=5),periods=1200,freq='5min',name='datetime')
            c=2000+np.sin(np.arange(len(idx))/8)*2
            raw=pd.DataFrame(dict(open=c,high=c+1,low=c-1,close=c+.1),index=idx)
            x=scalp_features65(raw,resample_ohlc_strict(raw,'15min',3));i=x.index[-1]
            # Explicit manufactured fixture, never shown as a genuine market signal.
            fixture=dict(regime15='TREND_UP',rsi14=60.,atr14=2.,resistance10=2000.,support10=1998.,bb_mid=2000.,bb_width=.02,bb_width_previous=.01,body_pct=.7,open=2000.1,high=2001.2,low=2000.,close=2001.)
            for k,v in fixture.items():x.loc[i,k]=v
            sig=scalp_signal65(x,preset_paper64());assert sig['side']==1,'LAB_SIGNAL_FAILED'
            q=Quote('XAU/USD',Decimal('2001'),None,None,None,utcnow(),'SYNTHETIC_LAB')
            cid='LAB66-'+hashlib.sha256(str(utcnow()).encode()).hexdigest()[:20]
            plan,block=make_scalp_plan65(svc,sig,x,q,cid);assert plan is not None,block
            ev=SignalEvaluation(Side.BUY,100,0,100,60,Grade.B,CandidateStatus.WATCH_ONLY,(),('SYNTHETIC LAB',),(),utcnow())
            svc.repo.save_candidate(cid,ev,plan,source='PAPER_EXPERIMENT')
            decision=svc.risk.assess(svc.account,plan,q,utcnow());assert decision.approved,decision.reason_codes
            svc.execution.latest_closed_1m_at=utcnow();p=svc.execution.execute(svc.account,plan,decision,q)
            stages=[dict(stage='Signal',result=sig['family']),dict(stage='Risk',result='APPROVED'),dict(stage='Execution',result=f'{p.original_lot} lot')]
            t=utcnow()+timedelta(minutes=1)
            svc.execution.process_closed_bar(p.id,t,t+timedelta(minutes=1),p.entry,p.tp3,p.entry,p.tp3)
            p=svc.repo.get_position(p.id);assert Decimal(p.remaining_lot)==Decimal('.015'),'LAB_TP3_FAILED'
            stages.append(dict(stage='TP3',result=f'remaining={p.remaining_lot}'))
            t+=timedelta(minutes=1)
            svc.execution.process_closed_bar(p.id,t,t+timedelta(minutes=1),p.tp3,p.tp5,p.tp3,p.tp5)
            p=svc.repo.get_position(p.id);assert p.status=='CLOSED','LAB_CLOSE_FAILED'
            events=svc.repo.events(p.id)
            stages.extend([dict(stage='TP5 / Exit',result=p.status),dict(stage='Journal',result=f'{len(events)} events')])
            # Independent SL scenario uses a new temporary account/engine to avoid rolling-fill guard.
            strict=replace(plan,quote_policy=QuotePolicy.STRICT_EXECUTABLE,candidate_id=cid+'strict')
            rejected=svc.risk.assess(svc.account,strict,q,utcnow());assert not rejected.approved
            stages.append(dict(stage='STRICT without bid/ask',result='BLOCKED'))
            slsvc=CoreService(Settings(database_url='sqlite:///'+tmp+'/sl_lab.db',quote_policy=QuotePolicy.REFERENCE_SIMULATION))
            try:
                slsvc.set_account_controls(Decimal('10000'),True,False);slsvc.ensure_paper_experiment()
                sq=replace(q,received_timestamp=utcnow())
                slplan,slblock=make_scalp_plan65(slsvc,sig,x,sq,cid+'sl');assert slplan is not None,slblock
                slsvc.repo.save_candidate(cid+'sl',ev,slplan,source='PAPER_EXPERIMENT')
                slrisk=slsvc.risk.assess(slsvc.account,slplan,sq,utcnow());assert slrisk.approved,slrisk.reason_codes
                slsvc.execution.latest_closed_1m_at=utcnow();sp=slsvc.execution.execute(slsvc.account,slplan,slrisk,sq)
                slsvc.set_account_controls(Decimal('10000'),False,True)
                t=utcnow()+timedelta(minutes=1)
                slsvc.execution.process_closed_bar(sp.id,t,t+timedelta(minutes=1),sp.entry,sp.entry,sp.sl_current-1,sp.sl_current-1)
                sp=slsvc.repo.get_position(sp.id);assert sp.status=='CLOSED' and sp.realized_pnl<0,'LAB_SL_FAILED'
                stages.append(dict(stage='SL with new entries disabled',result='CLOSED / protective management'))
                events+=slsvc.repo.events(sp.id)
            finally:slsvc.engine.dispose()
            return pd.DataFrame(stages),pd.DataFrame([dict(event=e.event_type,quantity=e.quantity,price=e.price,pnl=e.pnl,details=e.details_json) for e in events])
        finally:svc.engine.dispose()

def render_lab66(service,result):
    st.subheader('V6.6 — Inspectable decisions and independent tests')
    if result:
        active=result.get('active_strategy') or {};params=active.get('params',preset_paper64())
        rules=diagnostic_rules66(result['scalp_features'],params,getattr(service,'scalp_options',{}))
        st.write('Current reason:',reason_text66(result.get('no_entry_reason')))
        st.dataframe(rules,hide_index=True)
        st.download_button('Download current candle rules',rules.to_csv(index=False),'v66_rules.csv')
        st.plotly_chart(position_chart66(result['scalp_features'].tail(160),service.repo.all_positions(service.account.id),service.repo.events()),width='stretch',key='position_chart66')
        st.subheader('Frozen scalper replay — 1x research')
        st.caption('Uses cached bars; no extra download or parameter fitting. Next-bar-open entries, current setup rules and conservative TP lifecycle. Historical news and account Risk Engine limits are NOT applied in this research replay. End-of-data exit is forced. Results cannot authorize activation or a robust PASS.')
        bars=st.slider('Replay candles',350,max(350,len(result['frames']['5m'])),min(2000,max(350,len(result['frames']['5m']))),50)
        if st.button('Replay base and stress costs'):
            raw=result['frames']['5m'].tail(bars)
            opts=getattr(service,'scalp_options',{})
            st.session_state['replay66']={'base':replay_scalp66(raw,params,opts,CostModel(.3,.05)),'stress':replay_scalp66(raw,params,opts,CostModel(.5,.1))}
        for label,res in st.session_state.get('replay66',{}).items():
            st.write(label,'Plan-eligible signals:',res['signal_count']);st.json(res['metrics']);st.dataframe(res['trades'],hide_index=True)
            import plotly.graph_objects as go
            st.plotly_chart(go.Figure(go.Scatter(x=res['curve'].index,y=res['curve'],name=label+' 1x equity')).update_layout(height=280),width='stretch',key='replay_curve66_'+label)
            st.download_button('Download trades '+label,res['trades'].to_csv(index=False),f'v66_replay_{label}.csv')
            if len(res['plan_blocks']):st.dataframe(res['plan_blocks'].reason.value_counts().rename_axis('reason').reset_index(name='count'),hide_index=True)
    st.subheader('Independent synthetic lifecycle test')
    st.caption('Technical Signal → Risk → Execution → TP → Journal check in a temporary database, without API calls or changes to main positions. A successful test does not establish profitability or permission to enter the market.')
    if st.button('Run independent lifecycle test'):
        try:st.session_state['lab66']=independent_lab66()
        except Exception:st.error('Independent test failed; market entries were not changed.')
    if 'lab66' in st.session_state:
        st.success('Independent synthetic test passed.');st.dataframe(st.session_state['lab66'][0],hide_index=True);st.dataframe(st.session_state['lab66'][1],hide_index=True)


if __name__=='__main__':
    render_dashboard()
