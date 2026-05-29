import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from data_loader import load_scan_df, load_user_file
from core.strategy_lab import ensure_scores

try:
    from streamlit_autorefresh import st_autorefresh
    AUTO = True
except ImportError:
    AUTO = False

# Page config
st.set_page_config(
    page_title="Trading AI Dashboard V11",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 1rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .stAlert {
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar - Auto Refresh
with st.sidebar:
    st.image("https://raw.githubusercontent.com/streamlit/streamlit/develop/docs/logo.svg", width=50)
    st.title("⚙️ Settings")
    
    if AUTO:
        st.subheader("Auto Refresh")
        refresh_on = st.toggle("Enable Auto Refresh", False)
        refresh_mins = st.selectbox("Refresh Interval", [1, 5, 10, 15, 30], index=2)
        if refresh_on:
            st_autorefresh(interval=refresh_mins*60*1000, key="auto_refresh")
            st.success(f"🔄 Refreshing every {refresh_mins} min")
    
    st.divider()
    
    # Quick Actions
    st.subheader("🚀 Quick Actions")
    if st.button("🔄 Reload Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    if st.button("📊 Run Updater", use_container_width=True):
        with st.spinner("Fetching latest data..."):
            import subprocess
            result = subprocess.run(["python", "nifty500_auto_updater.py"], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                st.success("✅ Data updated!")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error(f"❌ Update failed:\n{result.stderr}")

# Load data
@st.cache_data(ttl=300)
def load_all_data():
    scan_df, scan_file = load_scan_df()
    scan_df = ensure_scores(scan_df) if not scan_df.empty else scan_df
    journal_df = load_user_file("trade_journal.csv", ["date","symbol","setup","entry","exit","qty","pnl","lesson"])
    alerts_df = load_user_file("alert_history.csv", ["date","symbol","signal","message","status"])
    portfolio_df = load_user_file("portfolio.csv", ["symbol","qty","buy_price","target","stop_loss"])
    watchlist_df = load_user_file("watchlist.csv", ["symbol","tag","note"])
    return scan_df, scan_file, journal_df, alerts_df, portfolio_df, watchlist_df

scan_df, scan_file, journal_df, alerts_df, portfolio_df, watchlist_df = load_all_data()

# Header
st.markdown('<h1 class="main-header">📈 Trading AI Dashboard V11</h1>', unsafe_allow_html=True)
st.caption(f"🕒 Last Updated: {datetime.now().strftime('%d %b %Y, %I:%M %p')}")

# Top Metrics
col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    st.metric("📊 Stocks Scanned", len(scan_df), help="Total stocks in database")

with col2:
    breakouts = int((scan_df.get("signal","")=="Breakout Candidate").sum()) if not scan_df.empty and "signal" in scan_df.columns else 0
    st.metric("🚀 Breakouts", breakouts, help="Darvas breakout with score ≥70")

with col3:
    undervalued = int((scan_df.get("value_category","")=="Undervalued").sum()) if not scan_df.empty and "value_category" in scan_df.columns else 0
    st.metric("💎 Undervalued", undervalued, help="PE < 15")

with col4:
    st.metric("📓 Journal Trades", len(journal_df))

with col5:
    total_pnl = round(pd.to_numeric(journal_df["pnl"], errors="coerce").fillna(0).sum(), 2) if not journal_df.empty else 0
    pnl_delta = "📈" if total_pnl > 0 else "📉"
    st.metric("💰 Total P&L", f"₹{total_pnl:,.0f}", delta=pnl_delta)

with col6:
    st.metric("💼 Portfolio", len(portfolio_df))

st.divider()

# Data source info
if scan_file:
    st.success(f"✅ Data loaded from: `{os.path.basename(scan_file)}`")
else:
    st.warning("⚠️ No scan data found. Click '📊 Run Updater' in sidebar.")

# Main Content Tabs
tab1, tab2, tab3, tab4 = st.tabs(["🎯 Top Picks", "📊 Sector Heatmap", "📈 Market Overview", "🔥 Trending"])

with tab1:
    st.subheader("🎯 Top Stock Recommendations")
    
    if not scan_df.empty:
        # Top Breakouts
        st.markdown("### 🚀 Top 5 Breakout Candidates")
        breakout_df = scan_df[scan_df.get("signal","")=="Breakout Candidate"].sort_values("combined_score", ascending=False).head(5)
        
        if not breakout_df.empty:
            cols_to_show = [c for c in ["symbol","sector","close","pe_ratio","roe_pct","volume_ratio","relative_strength_pct","combined_score","signal"] if c in breakout_df.columns]
            st.dataframe(
                breakout_df[cols_to_show],
                use_container_width=True,
                column_config={
                    "combined_score": st.column_config.ProgressColumn(
                        "Score",
                        format="%.0f",
                        min_value=0,
                        max_value=100,
                    ),
                    "close": st.column_config.NumberColumn("Price", format="₹%.2f"),
                }
            )
        else:
            st.info("No breakout candidates found")
        
        st.divider()
        
        # Top Value Picks
        st.markdown("### 💎 Top 5 Value Picks")
        value_df = scan_df[scan_df.get("value_category","")=="Undervalued"].sort_values("value_score", ascending=False).head(5)
        
        if not value_df.empty:
            cols_to_show = [c for c in ["symbol","sector","close","pe_ratio","pb_ratio","roe_pct","debt_equity","value_score","value_category"] if c in value_df.columns]
            st.dataframe(
                value_df[cols_to_show],
                use_container_width=True,
                column_config={
                    "value_score": st.column_config.ProgressColumn(
                        "Value Score",
                        format="%.0f",
                        min_value=0,
                        max_value=100,
                    ),
                    "close": st.column_config.NumberColumn("Price", format="₹%.2f"),
                }
            )
        else:
            st.info("No undervalued stocks found")

with tab2:
    st.subheader("📊 Sector Performance Heatmap")
    
    if not scan_df.empty and "sector" in scan_df.columns:
        sector_stats = scan_df.groupby("sector").agg({
            "symbol": "count",
            "change_pct": "mean",
            "combined_score": "mean",
            "volume_ratio": "mean"
        }).round(2)
        sector_stats.columns = ["Stocks", "Avg Change %", "Avg Score", "Avg Vol Ratio"]
        sector_stats = sector_stats.sort_values("Avg Score", ascending=False)
        
        # Heatmap
        fig = go.Figure(data=go.Heatmap(
            z=sector_stats["Avg Score"].values.reshape(-1, 1),
            y=sector_stats.index,
            x=["Combined Score"],
            colorscale="RdYlGn",
            text=sector_stats["Avg Score"].values.reshape(-1, 1),
            texttemplate="%{text:.1f}",
            textfont={"size": 14},
            colorbar=dict(title="Score")
        ))
        fig.update_layout(height=600, title="Sector-wise Average Combined Score")
        st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(sector_stats, use_container_width=True)

with tab3:
    st.subheader("📈 Market Overview")
    
    if not scan_df.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            # Signal distribution
            if "signal" in scan_df.columns:
                signal_dist = scan_df["signal"].value_counts()
                fig = go.Figure(data=[go.Pie(
                    labels=signal_dist.index,
                    values=signal_dist.values,
                    hole=0.4,
                    marker=dict(colors=['#667eea', '#764ba2', '#f093fb', '#4facfe', '#43e97b'])
                )])
                fig.update_layout(title="Signal Distribution", height=400)
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Value category distribution
            if "value_category" in scan_df.columns:
                value_dist = scan_df["value_category"].value_counts()
                fig = go.Figure(data=[go.Bar(
                    x=value_dist.index,
                    y=value_dist.values,
                    marker=dict(color=['#10b981', '#3b82f6', '#f59e0b', '#ef4444'])
                )])
                fig.update_layout(title="Value Category Distribution", height=400)
                st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.subheader("🔥 Trending Stocks")
    
    if not scan_df.empty:
        # High volume ratio stocks
        high_vol = scan_df.nlargest(10, "volume_ratio") if "volume_ratio" in scan_df.columns else pd.DataFrame()
        
        if not high_vol.empty:
            st.markdown("### 📢 Highest Volume Surge")
            cols_to_show = [c for c in ["symbol","sector","close","change_pct","volume_ratio","relative_strength_pct","signal"] if c in high_vol.columns]
            st.dataframe(high_vol[cols_to_show], use_container_width=True)
        
        st.divider()
        
        # Best relative strength
        high_rs = scan_df.nlargest(10, "relative_strength_pct") if "relative_strength_pct" in scan_df.columns else pd.DataFrame()
        
        if not high_rs.empty:
            st.markdown("### 💪 Strongest Relative Strength")
            cols_to_show = [c for c in ["symbol","sector","close","change_pct","relative_strength_pct","technical_score","signal"] if c in high_rs.columns]
            st.dataframe(high_rs[cols_to_show], use_container_width=True)

# Footer
st.divider()
st.info("💡 **Navigation:** Use the sidebar to access Scanner, Strategy Lab, Alerts, Journal, Watchlist, and Portfolio pages")