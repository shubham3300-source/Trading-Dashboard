import io, os, time, requests, pandas as pd, yfinance as yf
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(BASE_DIR, "generated_data")
os.makedirs(OUT_DIR, exist_ok=True)

INDEX_URLS = [
    "https://archives.nseindia.com/content/indices/ind_nifty500list.csv",
    "https://niftyindices.com/IndexConstituent/ind_nifty500list.csv",
]


def fetch_nifty500_list():
    for url in INDEX_URLS:
        try:
            r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            df = pd.read_csv(io.StringIO(r.text))
            cols = {c.lower().strip(): c for c in df.columns}
            company_col = cols.get("company name") or list(df.columns)[0]
            sector_col = cols.get("industry") or list(df.columns)[1]
            symbol_col = cols.get("symbol") or list(df.columns)[2]
            out = df[[company_col, sector_col, symbol_col]].copy()
            out.columns = ["company_name", "sector", "symbol"]
            out["symbol"] = out["symbol"].astype(str).str.strip().str.upper()
            print(f"Fetched {len(out)} constituents from {url}")
            return out
        except Exception as e:
            print(f"Failed {url}: {e}")
    raise RuntimeError("Cannot fetch Nifty 500 list")


def chunked(lst, n=50):
    for i in range(0, len(lst), n):
        yield lst[i:i+n]


def get_fundamentals(symbols):
    rows = {}
    total = len(symbols)
    for i, sym in enumerate(symbols):
        try:
            t = yf.Ticker(f"{sym}.NS")
            info = t.info or {}
            rows[sym] = {
                "pe_ratio": info.get("trailingPE") or info.get("forwardPE"),
                "forward_pe": info.get("forwardPE"),
                "pb_ratio": info.get("priceToBook"),
                "eps_ttm": info.get("trailingEps"),
                "roe_pct": round(info.get("returnOnEquity", 0) * 100, 2) if info.get("returnOnEquity") else None,
                "market_cap_cr": round(info.get("marketCap", 0) / 1e7, 2) if info.get("marketCap") else None,
                "debt_equity": info.get("debtToEquity"),
                "dividend_yield_pct": round(info.get("dividendYield", 0) * 100, 2) if info.get("dividendYield") else None,
                "book_value": info.get("bookValue"),
                "sector_yf": info.get("sector", ""),
            }
            if (i + 1) % 25 == 0:
                print(f"  Fundamentals: {i+1}/{total}")
            time.sleep(0.15)
        except Exception:
            rows[sym] = {}
    return pd.DataFrame.from_dict(rows, orient="index").reset_index().rename(columns={"index": "symbol"})


def download_snapshot(symbols):
    rows = []
    yahoo_symbols = [f"{s}.NS" for s in symbols]
    for batch in chunked(yahoo_symbols, 50):
        try:
            data = yf.download(batch, period="6mo", interval="1d",
                               auto_adjust=False, progress=False,
                               group_by="ticker", threads=True)
            if data is None or len(data) == 0:
                continue
            if isinstance(data.columns, pd.MultiIndex):
                for t in sorted(set(data.columns.get_level_values(0))):
                    try:
                        df = data[t].dropna(how="all").copy()
                        if df.empty or len(df) < 25:
                            continue
                        latest = df.iloc[-1]
                        prev = df.iloc[-2] if len(df) > 1 else latest
                        avg_vol = df["Volume"].tail(20).mean()
                        high52 = df["High"].max()
                        low52 = df["Low"].min()
                        rs = ((latest["Close"] / df["Close"].tail(20).mean()) - 1) * 100 if df["Close"].tail(20).mean() else 0
                        chg = ((latest["Close"] - prev["Close"]) / prev["Close"] * 100) if prev["Close"] else 0
                        rows.append({
                            "symbol": t.replace('.NS', ''),
                            "open": round(float(latest["Open"]), 2),
                            "high": round(float(latest["High"]), 2),
                            "low": round(float(latest["Low"]), 2),
                            "close": round(float(latest["Close"]), 2),
                            "change_pct": round(float(chg), 2),
                            "volume": int(latest["Volume"]),
                            "avg_20d_volume": int(avg_vol) if pd.notna(avg_vol) else 0,
                            "volume_ratio": round(float(latest["Volume"] / avg_vol), 2) if avg_vol else 0,
                            "high_52w": round(float(high52), 2),
                            "high_52w_date": str(pd.to_datetime(df["High"].idxmax()).date()),
                            "low_52w": round(float(low52), 2),
                            "low_52w_date": str(pd.to_datetime(df["Low"].idxmin()).date()),
                            "distance_from_52w_high_pct": round(((float(latest["Close"]) / float(high52)) - 1) * 100, 2),
                            "relative_strength_pct": round(float(rs), 2),
                            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                    except Exception:
                        continue
        except Exception as e:
            print(f"Batch error: {e}")
    return pd.DataFrame(rows)


def score_signals(df):
    vals = []
    for _, r in df.iterrows():
        s = 0
        if r.get("change_pct", 0) > 1.5: s += 20
        if r.get("volume_ratio", 0) > 1.5: s += 20
        if r.get("relative_strength_pct", 0) > 2: s += 20
        if r.get("distance_from_52w_high_pct", -999) > -5: s += 20
        if r.get("close", 0) > r.get("open", 0): s += 20
        vals.append(s)
    df["final_score"] = vals
    df["signal"] = df["final_score"].apply(
        lambda x: "Breakout Candidate" if x >= 80 else (
            "Watchlist - Near Breakout" if x >= 60 else (
                "Trend Strength - Monitor" if x >= 40 else "Avoid / No Edge"
            )
        )
    )
    return df
   
def add_technical_indicators(df):
    """Add Darvas Box and Candlestick pattern columns"""
    import yfinance as yf
    
    enhanced_rows = []
    
    for idx, row in df.iterrows():
        symbol = row['symbol']
        
        try:
            # Download recent data for technical analysis
            ticker = yf.Ticker(f"{symbol}.NS")
            hist = ticker.history(period="3mo")
            
            if hist.empty or len(hist) < 20:
                # Skip if insufficient data
                enhanced_rows.append({
                    **row.to_dict(),
                    'darvas_state': 'Unknown',
                    'box_high': None,
                    'box_low': None,
                    'candle': 'Normal',
                    'trend': 'Unknown'
                })
                continue
            
            # Calculate Darvas Box
            lookback = 20
            highs = hist['High'][-lookback:]
            lows = hist['Low'][-lookback:]
            closes = hist['Close']
            
            box_high = float(highs.max())
            box_low = float(lows.min())
            last_close = float(closes.iloc[-1])
            last_high = float(hist['High'].iloc[-1])
            
            if last_close > box_high * 1.002:
                darvas_state = "Breakout"
            elif last_high >= box_high * 0.995:
                darvas_state = "Near Breakout"
            elif last_close < box_low * 0.998:
                darvas_state = "Breakdown"
            else:
                darvas_state = "Inside Box"
            
            # Detect candlestick pattern
            o, h, l, c = (float(hist['Open'].iloc[-1]), float(hist['High'].iloc[-1]),
                         float(hist['Low'].iloc[-1]), float(hist['Close'].iloc[-1]))
            
            body = abs(c - o)
            rng = h - l
            
            if rng == 0:
                candle = "Neutral"
            else:
                body_ratio = body / rng
                
                if body_ratio < 0.1:
                    candle = "Doji"
                elif body_ratio > 0.7:
                    candle = "Bullish Marubozu" if c > o else "Bearish Marubozu"
                else:
                    lower_wick = min(o, c) - l
                    upper_wick = h - max(o, c)
                    
                    if lower_wick > body * 2 and upper_wick < body:
                        candle = "Hammer"
                    elif upper_wick > body * 2 and lower_wick < body:
                        candle = "Shooting Star"
                    elif c > o and body_ratio > 0.5:
                        candle = "Strong Bull"
                    elif c < o and body_ratio > 0.5:
                        candle = "Strong Bear"
                    else:
                        candle = "Normal"
            
            # Calculate EMAs and trend
            ema20 = closes.ewm(span=20, adjust=False).mean()
            ema50 = closes.ewm(span=50, adjust=False).mean()
            ema200 = closes.ewm(span=200, adjust=False).mean() if len(closes) >= 200 else ema50
            
            c_val = float(closes.iloc[-1])
            e20 = float(ema20.iloc[-1])
            e50 = float(ema50.iloc[-1])
            e200 = float(ema200.iloc[-1])
            
            if c_val > e20 > e50 > e200:
                trend = "Strong Uptrend"
            elif c_val > e50 and c_val > e200:
                trend = "Uptrend"
            elif c_val < e20 < e50 < e200:
                trend = "Strong Downtrend"
            elif c_val < e50 and c_val < e200:
                trend = "Downtrend"
            else:
                trend = "Sideways"
            
            enhanced_rows.append({
                **row.to_dict(),
                'darvas_state': darvas_state,
                'box_high': round(box_high, 2),
                'box_low': round(box_low, 2),
                'candle': candle,
                'trend': trend
            })
            
        except Exception as e:
            print(f"Error processing {symbol}: {e}")
            enhanced_rows.append({
                **row.to_dict(),
                'darvas_state': 'Unknown',
                'box_high': None,
                'box_low': None,
                'candle': 'Normal',
                'trend': 'Unknown'
            })
    
    return pd.DataFrame(enhanced_rows)

def value_category(pe):
    if pe is None or pd.isna(pe): return "N/A"
    if pe < 15: return "Undervalued"
    if pe < 25: return "Fairly Valued"
    if pe < 40: return "Expensive"
    return "Overvalued"


def main():
    print("Step 1: Fetching Nifty 500 list...")
    idx = fetch_nifty500_list()
    idx.to_csv(os.path.join(OUT_DIR, "nifty500_constituents.csv"), index=False)

    print("Step 2: Downloading market snapshot...")
    snap = download_snapshot(idx["symbol"].tolist())
    if snap.empty:
        print("ERROR: No market data downloaded.")
        return

    print("Step 3: Fetching fundamentals (PE, PB, EPS, ROE)...")
    funds = get_fundamentals(idx["symbol"].tolist())

    print("Step 4: Merging and scoring...")
    final = idx.merge(snap, on="symbol", how="left")
    final = final.merge(funds, on="symbol", how="left")
    final = score_signals(final)
    final["value_category"] = final["pe_ratio"].apply(value_category)
    
    print("Step 5: Adding technical indicators (Darvas, Candlestick, EMA)...")
    final = add_technical_indicators(final)  # NEW LINE
    
    final = final.sort_values(["final_score", "relative_strength_pct"], ascending=[False, False])

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    latest_path = os.path.join(OUT_DIR, "nifty500_live_latest.csv")
    snap_path = os.path.join(OUT_DIR, f"nifty500_live_{ts}.csv")
    final.to_csv(latest_path, index=False)
    final.to_csv(snap_path, index=False)
    print(f"Done. Saved: {latest_path}")
    print(final[["symbol", "close", "pe_ratio", "pb_ratio", "eps_ttm", "roe_pct", "signal", "value_category"]].head(10).to_string(index=False))


if __name__ == "__main__":
    main()
