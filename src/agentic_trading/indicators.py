"""Causal indicators; None represents insufficient history, never a fabricated value."""
from math import log, sqrt
from statistics import mean, pstdev
from .models import Candle, TradingError


def sma(values, period):
    if period < 1:
        raise TradingError("positive period required")
    return [None if i + 1 < period else mean(values[i-period+1:i+1]) for i in range(len(values))]


def ema(values, period):
    if period < 1:
        raise TradingError("positive period required")
    out = [None] * len(values)
    if len(values) >= period:
        out[period-1] = mean(values[:period])
        alpha = 2 / (period + 1)
        for i in range(period, len(values)):
            out[i] = alpha * values[i] + (1-alpha) * out[i-1]
    return out


def wilder(values, period):
    if period < 1:
        raise TradingError("positive period required")
    out = [None] * len(values)
    if len(values) >= period:
        out[period-1] = mean(values[:period])
        for i in range(period, len(values)):
            out[i] = (out[i-1] * (period-1) + values[i]) / period
    return out


def rsi(values, period=14):
    changes = [b-a for a, b in zip(values, values[1:])]
    gains = wilder([max(x, 0) for x in changes], period)
    losses = wilder([max(-x, 0) for x in changes], period)
    return [None] + [None if g is None else (50 if g == l == 0 else 100 if l == 0 else 100-100/(1+g/l)) for g, l in zip(gains, losses)] if values else []


def atr(bars, period=14):
    tr = [float(b.high-b.low) if i == 0 else max(float(b.high-b.low), abs(float(b.high-bars[i-1].close)), abs(float(b.low-bars[i-1].close))) for i, b in enumerate(bars)]
    return wilder(tr, period)


def adx(bars, period=14):
    if len(bars) < 2:
        return [None] * len(bars)
    plus, minus, tr = [], [], []
    for a, b in zip(bars, bars[1:]):
        up, down = float(b.high-a.high), float(a.low-b.low)
        plus.append(up if up > down and up > 0 else 0)
        minus.append(down if down > up and down > 0 else 0)
        tr.append(max(float(b.high-b.low), abs(float(b.high-a.close)), abs(float(b.low-a.close))))
    p, m, t = wilder(plus, period), wilder(minus, period), wilder(tr, period)
    dx = []
    for pv, mv, tv in zip(p, m, t):
        if tv is None:
            continue
        denominator = pv + mv
        dx.append(0 if denominator == 0 else 100 * abs(pv-mv)/denominator)
    result = wilder(dx, period)
    return [None] * min(period, len(bars)) + result


def bollinger(values, period=20, deviations=2):
    averages = sma(values, period)
    return [None if avg is None else {"middle": avg, "upper": avg+deviations*pstdev(values[i-period+1:i+1]), "lower": avg-deviations*pstdev(values[i-period+1:i+1])} for i, avg in enumerate(averages)]


def macd(values, fast=12, slow=26, signal=9):
    f, s = ema(values, fast), ema(values, slow)
    line = [None if a is None or b is None else a-b for a, b in zip(f, s)]
    valid = [v for v in line if v is not None]
    sig = [None] * (len(line)-len(valid)) + ema(valid, signal)
    return [{"macd": m, "signal": s, "histogram": None if m is None or s is None else m-s} for m, s in zip(line, sig)]


def vwap(bars):
    out, numerator, denominator, day = [], 0.0, 0.0, None
    for b in bars:
        if b.time.date() != day:
            numerator, denominator, day = 0.0, 0.0, b.time.date()
        numerator += float((b.high+b.low+b.close)/3*b.volume)
        denominator += float(b.volume)
        out.append(numerator/denominator if denominator else None)
    return out


def summary(bars: list[Candle]):
    closes = [float(b.close) for b in bars]
    if not closes:
        raise TradingError("no bars")
    returns = [log(b/a) for a, b in zip(closes, closes[1:])]
    av = atr(bars)[-1]
    relative = float(bars[-1].volume) / mean(float(b.volume) for b in bars[-21:-1]) if len(bars)>20 and sum(b.volume for b in bars[-21:-1]) else None
    return {"rsi": rsi(closes)[-1], "atr": av, "normalized_atr": av/closes[-1] if av else None,
            "adx": adx(bars)[-1], "macd": macd(closes)[-1], "bollinger": bollinger(closes)[-1],
            "vwap": vwap(bars)[-1], "relative_volume": relative,
            "realized_volatility_per_bar": pstdev(returns) if len(returns)>1 else None,
            "momentum_10": closes[-1]/closes[-11]-1 if len(closes)>10 else None,
            "support": min(float(b.low) for b in bars[-21:-1]) if len(bars)>20 else None,
            "resistance": max(float(b.high) for b in bars[-21:-1]) if len(bars)>20 else None,
            **{f"ema_{p}": ema(closes,p)[-1] for p in (20,50,100,200)}, "sma_20": sma(closes,20)[-1]}
