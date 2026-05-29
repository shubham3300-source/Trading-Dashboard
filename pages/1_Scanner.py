import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = BASE_DIR if os.path.basename(BASE_DIR) != "pages" else os.path.dirname(BASE_DIR)
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from data_loader import load_scan_df, load_user_file, save_user_file
from core.strategy_lab import ensure_scores
from services.telegram_service import send_message

st.set_page_config(page_title="Scanner", page_icon="📊", layout="wide")

# Load data
scan_df, _ = load_scan_df()
scan_df = ensure_scores(scan_df) if not scan_df.empty else scan_df
alerts_df = load_user_file("alert_history.csv", ["date","symbol","signal","message","status"])
watchlist_df = load_user_file("watchlist.csv", ["symbol","tag","note"])

st.title("📊 Advanced Stock Scanner")

if scan_df.empty:
    st.warning("⚠️ No data. Run updater first.")
    st.stop()

# Sidebar Filters
with st.sidebar:
    st.header("🔍 Filters")
    
    # Sector filter
    sectors = sorted(scan_df["sector"].dropna().unique()) if "sector" in scan_df.columns else []
    sel_sectors = st.multiselect("Sector", sectors, default=sectors)
    
    # Score filters
    st.subheader("Score Range")
    min_combined = st.slider("Min Combined Score", 0, 100, 0)
    min_technical = st.slider("Min Technical Score", 0, 100, 0)
    min_value = st.slider("Min Value Score", 0, 100, 0)
    
    # Signal filter
    if "signal" in scan_df.columns:
        signals = scan_df["signal"].unique().tolist()
        sel_signals = st.multiselect("Signal Type", signals, default=signals)
    else:
        sel_signals = []
    
    # Value category filter
    if "value_category" in scan_df.columns:
        categories = scan_df["value_category"].unique().tolist()
        sel_categories = st.multiselect("Value Category", categories, default=categories)
    else:
        sel_categories = []
    
    # Fundamental filters
    st.subheader("Fundamentals")
    max_pe = st.number_input("Max PE Ratio", value=100.0, step=5.0)
    min_roe = st.number_input("Min ROE %", value=0.0, step=1.0)
    
    # Technical filters
    st.subheader("Technical")
    min_vol_ratio = st.number_input("Min Volume Ratio", value=0.0, step=0.1)
    min_rs = st.number_input("Min Relative Strength %", value=-100.0, step=1.0)

# Apply filters
fd = scan_df.copy()

if "sector" in fd.columns:
    fd = fd[fd["sector"].isin(sel_sectors)]

if "combined_score" in fd.columns:
    fd = fd[pd.to_numeric(fd["combined_score"], errors="coerce") >= min_combined]

if "technical_score" in fd.columns:
    fd = fd[pd.to_numeric(fd["technical_score"], errors="coerce") >= min_technical]

if "value_score" in fd.columns:
    fd = fd[pd.to_numeric(fd["value_score"], errors="coerce") >= min_value]

if "signal" in fd.columns and sel_signals:
    fd = fd[fd["signal"].isin(sel_signals)]

if "value_category" in fd.columns and sel_categories:
    fd = fd[fd["value_category"].isin(sel_categories)]

if "pe_ratio" in fd.columns:
    fd = fd[pd.to_numeric(fd["pe_ratio"], errors="coerce").fillna(999) <= max_pe]

if "roe_pct" in fd.columns:
    fd = fd[pd.to_numeric(fd["roe_pct"], errors="coerce").fillna(0) >= min_roe]

if "volume_ratio" in fd.columns:
    fd = fd[pd.to_numeric(fd["volume_ratio"], errors="coerce").fillna(0) >= min_vol_ratio]

if "relative_strength_pct" in fd.columns:
    fd = fd[pd.to_numeric(fd["relative_strength_pct"], errors="coerce").fillna(-999) >= min_rs]

# Sort by combined score
if "combined_score" in fd.columns:
    fd = fd.sort_values("combined_score", ascending=False)

# Display stats
col1, col2, col3, col4 = st.columns(4)
col1.metric("🎯 Filtered Stocks", len(fd))
col2.metric("📊 Total Scanned", len(scan_df))
col3.metric("🚀 Breakouts", len(fd[fd.get("signal","")=="Breakout Candidate"]) if "signal" in fd.columns else 0)
col4.metric("💎 Undervalued", len(fd[fd.get("value_category","")=="Undervalued"]) if "value_category" in fd.columns else 0)

st.divider()

# Main Table
show_cols = [c for c in [
    "symbol", "company_name", "sector", "close", "change_pct",
    "pe_ratio", "pb_ratio", "roe_pct", "debt_equity",
    "volume_ratio", "relative_strength_pct",
    "technical_score", "value_score", "combined_score",
    "signal", "value_category"
] if c in fd.columns]

st.subheader(f"📋 Scanner Results ({len(fd)} stocks)")

st.dataframe(
    fd[show_cols],
    use_container_width=True,
    height=500,
    column_config={
        "combined_score": st.column_config.ProgressColumn("Combined", format="%.0f", min_value=0, max_value=100),
        "technical_score": st.column_config.ProgressColumn("Technical", format="%.0f", min_value=0, max_value=100),
        "value_score": st.column_config.ProgressColumn("Value", format="%.0f", min_value=0, max_value=100),
        "close": st.column_config.NumberColumn("Price", format="₹%.2f"),
        "change_pct": st.column_config.NumberColumn("Change %", format="%.2f%%"),
    }
)

# Export options
col1, col2, col3 = st.columns(3)

with col1:
    csv = fd[show_cols].to_csv(index=False).encode('utf-8')
    st.download_button(
        "📥 Download CSV",
        csv,
        f"scanner_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        "text/csv",
        use_container_width=True
    )

with col2:
    if st.button("➕ Add All to Watchlist", use_container_width=True):
        for sym in fd["symbol"].head(20):  # Limit to top 20
            if sym not in watchlist_df["symbol"].values:
                new_row = pd.DataFrame([[sym, "scanner", f"Added on {datetime.now().strftime('%Y-%m-%d')}"]], 
                                      columns=["symbol","tag","note"])
                watchlist_df = pd.concat([watchlist_df, new_row], ignore_index=True)
        save_user_file("watchlist.csv", watchlist_df)
        st.success(f"✅ Added {min(20, len(fd))} stocks to watchlist")

with col3:
    if st.button("📱 Send Top 5 to Telegram", use_container_width=True):
        top5 = fd.head(5)
        msg = f"🎯 Top 5 Scanner Picks - {datetime.now().strftime('%d %b %Y')}\n\n"
        for idx, row in top5.iterrows():
            msg += f"{row['symbol']}: ₹{row.get('close',0):.2f} | Score: {row.get('combined_score',0):.0f} | {row.get('signal','')}\n"
        
        ok, resp = send_message(msg)
        if ok:
            st.success("✅ Alert sent!")
            new_alert = pd.DataFrame([[datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "MULTIPLE", "scanner", msg, "sent"]], 
                                    columns=["date","symbol","signal","message","status"])
            alerts_df = pd.concat([alerts_df, new_alert], ignore_index=True)
            save_user_file("alert_history.csv", alerts_df)
        else:
            st.error(f"❌ Failed: {resp}")

# Stock Detail View
st.divider()
st.subheader("🔍 Stock Detail View")

if not fd.empty:
    selected_symbol = st.selectbox("Select Stock", fd["symbol"].tolist())
    
    if selected_symbol:
        stock_data = fd[fd["symbol"]==selected_symbol].iloc[0]
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("### 📊 Price Info")
            st.metric("Close", f"₹{stock_data.get('close', 0):.2f}")
            st.metric("Change %", f"{stock_data.get('change_pct', 0):.2f}%")
            st.metric("Volume Ratio", f"{stock_data.get('volume_ratio', 0):.2f}x")
        
        with col2:
            st.markdown("### 💰 Fundamentals")
            st.metric("PE Ratio", f"{stock_data.get('pe_ratio', 0):.2f}")
            st.metric("ROE %", f"{stock_data.get('roe_pct', 0):.2f}%")
            st.metric("Debt/Equity", f"{stock_data.get('debt_equity', 0):.2f}")
        
        with col3:
            st.markdown("### 🎯 Scores")
            st.metric("Combined", f"{stock_data.get('combined_score', 0):.0f}/100")
            st.metric("Technical", f"{stock_data.get('technical_score', 0):.0f}/100")
            st.metric("Value", f"{stock_data.get('value_score', 0):.0f}/100")
        
        # Actions
        st.markdown("### ⚡ Quick Actions")
        acol1, acol2, acol3 = st.columns(3)
        
        with acol1:
            if st.button("➕ Add to Watchlist", key="add_watch"):
                if selected_symbol not in watchlist_df["symbol"].values:
                    new_row = pd.DataFrame([[selected_symbol, "manual", f"Added on {datetime.now().strftime('%Y-%m-%d')}"]], 
                                          columns=["symbol","tag","note"])
                    watchlist_df = pd.concat([watchlist_df, new_row], ignore_index=True)
                    save_user_file("watchlist.csv", watchlist_df)
                    st.success("✅ Added to watchlist")
                else:
                    st.info("Already in watchlist")
        
        with acol2:
            alert_msg = st.text_input("Alert message", f"{selected_symbol}: Breakout setup")
            if st.button("📱 Send Alert", key="send_alert"):
                ok, resp = send_message(alert_msg)
                if ok:
                    st.success("✅ Alert sent!")
                    new_alert = pd.DataFrame([[datetime.now().strftime('%Y-%m-%d %H:%M:%S'), selected_symbol, "manual", alert_msg, "sent"]], 
                                            columns=["date","symbol","signal","message","status"])
                    alerts_df = pd.concat([alerts_df, new_alert], ignore_index=True)
                    save_user_file("alert_history.csv", alerts_df)
                else:
                    st.error(f"❌ {resp}")