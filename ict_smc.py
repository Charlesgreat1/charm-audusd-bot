# Simple ICT/SMC-style heuristic module for demonstration.
# This is a lightweight, deterministic approximation for signals using price series.
# It looks for:
# - SMA crossover (fast/slow)
# - simple "liquidity sweep" detection (spike beyond recent high/low)
# - small FVG-like gap detection on daily data (three-bar pattern)
import math

def sma(prices, period):
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period

def detect_sma_crossover(prices, short=3, long=7):
    if len(prices) < long + 1:
        return None
    prev_short = sma(prices[:-1], short)
    prev_long = sma(prices[:-1], long)
    cur_short = sma(prices, short)
    cur_long = sma(prices, long)
    if prev_short is None or prev_long is None or cur_short is None or cur_long is None:
        return None
    # bullish crossover
    if prev_short <= prev_long and cur_short > cur_long:
        return "BUY"
    if prev_short >= prev_long and cur_short < cur_long:
        return "SELL"
    return None

def detect_liquidity_sweep(prices):
    # liquidity sweep: last price moves beyond max/min of previous N by a margin
    if len(prices) < 6:
        return None
    window = prices[-6:-1]
    last = prices[-1]
    prev_high = max(window)
    prev_low = min(window)
    # thresholds relative
    if last > prev_high * 1.002:  # small upward spike
        return "LIQ_UP"
    if last < prev_low * 0.998:   # small downward spike
        return "LIQ_DOWN"
    return None

def detect_fvg(prices):
    # simple three-point imbalance: A, B, C where A high < C low or A low > C high
    if len(prices) < 3:
        return None
    a, b, c = prices[-3], prices[-2], prices[-1]
    # treat daily closes as proxies; detect if there's an imbalance
    if a < c:
        return ("FVG_BULL", (a, c))
    if a > c:
        return ("FVG_BEAR", (c, a))
    return None

def analyze_prices(prices):
    # returns dict with candidate signals and reasons
    res = {}
    res['sma'] = detect_sma_crossover(prices)
    res['liq'] = detect_liquidity_sweep(prices)
    res['fvg'] = detect_fvg(prices)
    # combine heuristics: prefer SMA signal, but require no conflicting liquidity
    final = None
    reason = []
    if res['sma']:
        final = res['sma']
        reason.append(f"SMA crossover suggests {res['sma']}")
    if res['fvg']:
        reason.append(f"FVG detected {res['fvg'][0]} zone {res['fvg'][1]}")
    if res['liq']:
        reason.append(f"Liquidity event: {res['liq']}")
        # if liquidity contradicts SMA, ignore SMA
        if (res['liq']=="LIQ_UP" and res['sma']=="SELL") or (res['liq']=="LIQ_DOWN" and res['sma']=="BUY"):
            final = None
            reason.append("Liquidity sweep contradicts SMA -> hold")
    res['final'] = final
    res['reason_list'] = reason
    return res

def format_signal(res, last_price, last_date):
    if not res:
        return "No signal (insufficient data)."
    lines = []
    lines.append(f"AUD/USD — {last_date} — price {last_price:.6f}")
    if res['final']:
        lines.append(f"Signal: {res['final']}")
    else:
        lines.append("Signal: NO TRADE")
    if res['reason_list']:
        lines.append("Reasons:")
        for r in res['reason_list']:
            lines.append(f"- {r}")
    lines.append("\\n(Note: This is a heuristic signal. Test on paper first.)")
    return "\\n".join(lines)
