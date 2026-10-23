from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN
from enum import StrEnum
import hashlib
import json
from typing import Any


class TradingError(ValueError):
    """Invalid input or a fail-closed trading decision."""


class Mode(StrEnum):
    BACKTEST = "BACKTEST"
    REPLAY = "REPLAY"
    PAPER = "PAPER"
    LIVE_READ_ONLY = "LIVE_READ_ONLY"
    LIVE_EXECUTION = "LIVE_EXECUTION"


def D(value: Any) -> Decimal:
    if isinstance(value, bool):
        raise TradingError("boolean is not a financial number")
    try:
        result = Decimal(str(value))
    except Exception as exc:
        raise TradingError("invalid decimal") from exc
    if not result.is_finite():
        raise TradingError("non-finite financial number")
    return result


def utc(value: str | datetime) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else value
    if result.tzinfo is None:
        raise TradingError("timezone is required")
    return result.astimezone(timezone.utc)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    raise TypeError(type(value).__name__)


def dumps(value: Any) -> str:
    return json.dumps(value, default=json_default, sort_keys=True, ensure_ascii=False, allow_nan=False)


def fingerprint(value: Any) -> str:
    return hashlib.sha256(dumps(value).encode()).hexdigest()


def floor_step(value: Decimal, step: Decimal) -> Decimal:
    if step <= 0:
        raise TradingError("positive quantity step required")
    return (value / step).to_integral_value(rounding=ROUND_DOWN) * step


@dataclass(frozen=True)
class Candle:
    time: datetime  # close/availability time, not the opening timestamp
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal

    def __post_init__(self):
        object.__setattr__(self, "time", utc(self.time))
        for name in ("open", "high", "low", "close", "volume"):
            object.__setattr__(self, name, D(getattr(self, name)))
        if min(self.open, self.high, self.low, self.close) <= 0 or self.volume < 0:
            raise TradingError("invalid OHLCV")
        if self.high < max(self.open, self.close, self.low) or self.low > min(self.open, self.close):
            raise TradingError("inconsistent OHLC")

    @classmethod
    def from_dict(cls, row: dict) -> Candle:
        return cls(utc(row["time"]), *(D(row[k]) for k in ("open", "high", "low", "close", "volume")))


def validate_candles(bars: list[Candle]) -> None:
    if not bars or any(a.time >= b.time for a, b in zip(bars, bars[1:])):
        raise TradingError("empty, duplicate or unordered candles")


@dataclass(frozen=True)
class Instrument:
    symbol: str
    point_value: Decimal = Decimal("1")
    tick_size: Decimal = Decimal("0.01")
    quantity_step: Decimal = Decimal("0.0001")
    minimum_quantity: Decimal = Decimal("0.0001")
    max_leverage: Decimal = Decimal("1")
    maintenance_margin_rate: Decimal = Decimal("0.005")
    correlation_group: str = "crypto"
    specs_verified: bool = False
    currency: str = "USD"

    def __post_init__(self):
        for name in ("point_value", "tick_size", "quantity_step", "minimum_quantity", "max_leverage", "maintenance_margin_rate"):
            object.__setattr__(self, name, D(getattr(self, name)))
        if min(self.point_value, self.tick_size, self.quantity_step, self.minimum_quantity) <= 0:
            raise TradingError("positive contract specifications required")
        if self.max_leverage < 1 or not 0 <= self.maintenance_margin_rate < 1:
            raise TradingError("invalid leverage or maintenance margin")


@dataclass(frozen=True)
class TakeProfit:
    price: Decimal
    fraction: Decimal  # fraction of initial quantity

    def __post_init__(self):
        object.__setattr__(self, "price", D(self.price))
        object.__setattr__(self, "fraction", D(self.fraction))
        if self.price <= 0 or not 0 < self.fraction <= 1:
            raise TradingError("invalid take-profit")


@dataclass(frozen=True)
class TradePlan:
    symbol: str
    side: str
    entry: Decimal
    stop_loss: Decimal
    quantity: Decimal
    leverage: Decimal
    take_profits: tuple[TakeProfit, ...]
    strategy: str
    score: Decimal
    data_time: datetime
    signal_id: str
    reason: str = ""

    def __post_init__(self):
        for name in ("entry", "stop_loss", "quantity", "leverage", "score"):
            object.__setattr__(self, name, D(getattr(self, name)))
        object.__setattr__(self, "data_time", utc(self.data_time))
        object.__setattr__(self, "take_profits", tuple(self.take_profits))
        if self.side not in ("LONG", "SHORT") or not self.signal_id or not self.symbol:
            raise TradingError("symbol, direction and signal ID required")
        if min(self.entry, self.stop_loss, self.quantity) <= 0 or self.leverage < 1:
            raise TradingError("invalid plan numbers")
        if not 0 <= self.score <= 100:
            raise TradingError("score outside 0..100")
        if self.sign * (self.entry - self.stop_loss) <= 0:
            raise TradingError("stop is on the wrong side")
        if not 1 <= len(self.take_profits) <= 5 or sum(t.fraction for t in self.take_profits) != 1:
            raise TradingError("one to five targets must sum exactly to one")
        distances = [self.sign * (t.price - self.entry) for t in self.take_profits]
        if min(distances) <= 0 or distances != sorted(set(distances)):
            raise TradingError("targets must be profitable and strictly ordered")

    @property
    def sign(self) -> Decimal:
        return D(1 if self.side == "LONG" else -1)

    @property
    def id(self) -> str:
        return fingerprint(self)

    @classmethod
    def from_dict(cls, data: dict) -> TradePlan:
        data = dict(data)
        data["take_profits"] = tuple(TakeProfit(**t) for t in data["take_profits"])
        data["data_time"] = utc(data["data_time"])
        return cls(**data)
