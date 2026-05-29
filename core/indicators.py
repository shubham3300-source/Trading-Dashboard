import pandas as pd

def calc_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def detect_candle(o, h, l, c):
    body = abs(c - o)
    rng = h - l
    if rng == 0:
        return "Neutral"
    upper_wick = h - max(o, c)
    lower_wick = min(o, c) - l
    body_ratio = body / rng
    if body_ratio < 0.1:
        return "Doji"
    if body_ratio > 0.7:
        return "Bullish Marubozu" if c > o else "Bearish Marubozu"
    if lower_wick > body * 2 and upper_wick < body:
        return "Hammer" if c > o else "Hanging Man"
    if upper_wick > body * 2 and lower_wick < body:
        return "Shooting Star"
    if c > o and body_ratio > 0.5:
        return "Strong Bull"
    if c < o and body_ratio > 0.5:
        return "Strong Bear"
    return "Normal"

def detect_engulfing(prev_o, prev_c, curr_o, curr_c):
    if curr_c > curr_o and prev_c < prev_o:
        if curr_o < prev_c and curr_c > prev_o:
            return "Bullish Engulfing"
    if curr_c < curr_o and prev_c > prev_o:
        if curr_o > prev_c and curr_c < prev_o:
            return "Bearish Engulfing"
    return None

def detect_inside_bar(prev_h, prev_l, curr_h, curr_l):
    return "Inside Bar" if curr_h < prev_h and curr_l > prev_l else None

def calc_darvas(highs, lows, closes, lookback=20):
    if len(closes) < lookback:
        return None, None, "Unknown"
    box_high = float(highs[-lookback:].max())
    box_low  = float(lows[-lookback:].min())
    last_close = float(closes.iloc[-1])
    last_high  = float(highs.iloc[-1])
    if last_close > box_high * 1.002:
        state = "Breakout"
    elif last_high >= box_high * 0.995:
        state = "Near Breakout"
    elif last_close < box_low * 0.998:
        state = "Breakdown"
    else:
        state = "Inside Box"
    return round(box_high, 2), round(box_low, 2), state

def calc_trend(closes, ema20, ema50, ema200):
    c, e20, e50, e200 = (float(closes.iloc[-1]), float(ema20.iloc[-1]),
                          float(ema50.iloc[-1]), float(ema200.iloc[-1]))
    if c > e20 > e50 > e200:
        return "Strong Uptrend"
    elif c > e50 and c > e200:
        return "Uptrend"
    elif c < e20 < e50 < e200:
        return "Strong Downtrend"
    elif c < e50 and c < e200:
        return "Downtrend"
    return "Sideways"

def calc_rs(closes, bench_closes):
    if closes is None or bench_closes is None:
        return 0.0
    if len(closes) < 20 or len(bench_closes) < 20:
        return 0.0
    try:
        sym_ret   = (float(closes.iloc[-1]) / float(closes.iloc[-20]) - 1) * 100
        bench_ret = (float(bench_closes.iloc[-1]) / float(bench_closes.iloc[-20]) - 1) * 100
        return round(sym_ret - bench_ret, 2)
    except Exception:
        return 0.0

def final_score(darvas_state, trend, vol_ratio=1.0, rs=0.0, candle="Normal", profile="swing"):
    score = 0
    darvas_w = {"Breakout": 35, "Near Breakout": 20, "Inside Box": 5}
    score += darvas_w.get(darvas_state, 0) if profile == "swing" else (darvas_w.get(darvas_state, 0) - 5)
    trend_w = {"Strong Uptrend": 25, "Uptrend": 15, "Sideways": 5}
    score += trend_w.get(trend, 0) if profile == "swing" else (trend_w.get(trend, 0) - 5)
    if vol_ratio > 2.0:
        score += 12 if profile == "swing" else 20
    elif vol_ratio > 1.5:
        score += 8 if profile == "swing" else 12
    elif vol_ratio > 1.0:
        score += 4 if profile == "swing" else 6
    if rs > 5:
        score += 15
    elif rs > 2:
        score += 8
    elif rs > 0:
        score += 3
    bullish_candles = {"Hammer", "Bullish Engulfing", "Bullish Marubozu", "Strong Bull"}
    bearish_candles = {"Shooting Star", "Bearish Engulfing", "Bearish Marubozu", "Strong Bear"}
    if candle in bullish_candles:
        score += 10
    elif candle in bearish_candles:
        score -= 5
    return min(max(score, 0), 100)