import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = BASE_DIR if os.path.basename(BASE_DIR) != "pages" else os.path.dirname(BASE_DIR)
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data_loader import load_scan_df
from core.strategy_lab import ensure_scores

st.set_page_config(page_title="Technical Filters", page_icon="📊", layout="wide")

scan_df, _ = load_scan_df()
scan_df = ensure_scores(scan_df) if not scan_df.empty else scan_df

st.title("📊 Advanced Technical Filters")

if scan_df.empty:
    st.warning("No data. Run updater first.")
    st.stop()

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📦 Darvas Box Filter", "📈 EMA Alignment", "🕯️ Candlestick Patterns", "🎯 Multi-Filter Combo"])

with tab1:
    st.subheader("📦 Darvas Box Analysis")
    
    st.info("💡 Darvas Box Theory: Identify stocks breaking out of consolidation boxes")
    
    # Filter by Darvas state
    darvas_filter = st.multiselect(
        "Select Darvas States",
        ["Breakout", "Near Breakout", "Inside Box", "Breakdown", "Unknown"],
        default=["Breakout", "Near Breakout"]
    )
    
    # Filter data
    if "darvas_state" in scan_df.columns:
        darvas_df = scan_df[scan_df["darvas_state"].isin(darvas_filter)].copy()
    else:
        st.warning("Darvas state data not available. Run updater with latest code.")
        darvas_df = pd.DataFrame()
    
    if not darvas_df.empty:
        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        
        breakout_count = len(darvas_df[darvas_df.get("darvas_state") == "Breakout"])
        near_breakout = len(darvas_df[darvas_df.get("darvas_state") == "Near Breakout"])
        inside_box = len(darvas_df[darvas_df.get("darvas_state") == "Inside Box"])
        
        col1.metric("🚀 Breakouts", breakout_count)
        col2.metric("⚡ Near Breakout", near_breakout)
        col3.metric("📦 Inside Box", inside_box)
        col4.metric("📊 Total Filtered", len(darvas_df))
        
        st.divider()
        
        # Sort by combined score
        darvas_df = darvas_df.sort_values("combined_score", ascending=False)
        
        # Display table
        display_cols = [c for c in [
            "symbol", "sector", "close", "darvas_state",
            "box_high", "box_low", "volume_ratio",
            "technical_score", "combined_score", "signal"
        ] if c in darvas_df.columns]
        
        st.dataframe(
            darvas_df[display_cols],
            use_container_width=True,
            height=500,
            column_config={
                "close": st.column_config.NumberColumn("CMP", format="₹%.2f"),
                "box_high": st.column_config.NumberColumn("Box High", format="₹%.2f"),
                "box_low": st.column_config.NumberColumn("Box Low", format="₹%.2f"),
                "darvas_state": st.column_config.TextColumn("Darvas State"),
                "combined_score": st.column_config.ProgressColumn("Score", format="%.0f", min_value=0, max_value=100),
            }
        )
        
        # Export
        csv = darvas_df[display_cols].to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Download Darvas Filtered Stocks",
            csv,
            f"darvas_filter_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
            "text/csv"
        )
        
        st.divider()
        
        # Darvas state distribution
        state_dist = darvas_df["darvas_state"].value_counts()
        
        fig = go.Figure(data=[go.Pie(
            labels=state_dist.index,
            values=state_dist.values,
            hole=0.4,
            marker=dict(colors=['#10b981', '#f59e0b', '#3b82f6', '#ef4444'])
        )])
        fig.update_layout(title="Darvas State Distribution", height=400)
        st.plotly_chart(fig, use_container_width=True)
        
    else:
        st.info(f"No stocks found with selected Darvas states: {', '.join(darvas_filter)}")

with tab2:
    st.subheader("📈 EMA Alignment Filter")
    
    st.info("💡 EMA Alignment: Identify trending stocks based on EMA positioning")
    
    # EMA filter options
    ema_pattern = st.selectbox(
        "Select EMA Pattern",
        [
            "Golden Cross (EMA 20 > EMA 50 > EMA 200)",
            "Strong Uptrend (Price > EMA 20 > EMA 50 > EMA 200)",
            "Death Cross (EMA 20 < EMA 50 < EMA 200)",
            "Above All EMAs (Price > EMA 20, 50, 200)",
            "Below All EMAs (Price < EMA 20, 50, 200)",
            "Price Between EMA 20-50",
            "Custom"
        ]
    )
    
    # Mock EMA data (replace with actual EMA calculations from yfinance)
    # For now, use trend column as proxy
    
    if "trend" in scan_df.columns:
        if ema_pattern == "Golden Cross (EMA 20 > EMA 50 > EMA 200)":
            ema_df = scan_df[scan_df["trend"].isin(["Strong Uptrend", "Uptrend"])].copy()
        elif ema_pattern == "Strong Uptrend (Price > EMA 20 > EMA 50 > EMA 200)":
            ema_df = scan_df[scan_df["trend"] == "Strong Uptrend"].copy()
        elif ema_pattern == "Death Cross (EMA 20 < EMA 50 < EMA 200)":
            ema_df = scan_df[scan_df["trend"].isin(["Strong Downtrend", "Downtrend"])].copy()
        elif ema_pattern == "Above All EMAs (Price > EMA 20, 50, 200)":
            ema_df = scan_df[scan_df["trend"].isin(["Strong Uptrend", "Uptrend"])].copy()
        elif ema_pattern == "Below All EMAs (Price < EMA 20, 50, 200)":
            ema_df = scan_df[scan_df["trend"].isin(["Strong Downtrend", "Downtrend"])].copy()
        else:
            ema_df = scan_df[scan_df["trend"] == "Sideways"].copy()
    else:
        st.warning("Trend data not available")
        ema_df = pd.DataFrame()
    
    if not ema_df.empty:
        # Metrics
        col1, col2, col3 = st.columns(3)
        
        col1.metric("📊 Matched Stocks", len(ema_df))
        col2.metric("📈 Avg Score", f"{ema_df['combined_score'].mean():.1f}" if "combined_score" in ema_df.columns else "N/A")
        col3.metric("💰 Avg PE", f"{ema_df['pe_ratio'].mean():.2f}" if "pe_ratio" in ema_df.columns else "N/A")
        
        st.divider()
        
        # Display
        display_cols = [c for c in [
            "symbol", "sector", "close", "change_pct", "trend",
            "volume_ratio", "relative_strength_pct",
            "technical_score", "combined_score", "signal"
        ] if c in ema_df.columns]
        
        st.dataframe(
            ema_df.sort_values("combined_score", ascending=False)[display_cols],
            use_container_width=True,
            height=500,
            column_config={
                "close": st.column_config.NumberColumn("Price", format="₹%.2f"),
                "change_pct": st.column_config.NumberColumn("Change %", format="%.2f%%"),
                "combined_score": st.column_config.ProgressColumn("Score", format="%.0f", min_value=0, max_value=100),
            }
        )
        
        # Export
        csv = ema_df[display_cols].to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Download EMA Filtered Stocks",
            csv,
            f"ema_filter_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
            "text/csv"
        )
    else:
        st.info(f"No stocks found matching pattern: {ema_pattern}")

with tab3:
    st.subheader("🕯️ Candlestick Pattern Filter")
    
    st.info("💡 Identify stocks with bullish/bearish candlestick patterns")
    
    # Pattern filter
    pattern_type = st.multiselect(
        "Select Candlestick Patterns",
        [
            "Doji",
            "Hammer",
            "Shooting Star",
            "Bullish Engulfing",
            "Bearish Engulfing",
            "Bullish Marubozu",
            "Bearish Marubozu",
            "Strong Bull",
            "Strong Bear"
        ],
        default=["Hammer", "Bullish Engulfing", "Bullish Marubozu"]
    )
    
    if "candle" in scan_df.columns and pattern_type:
        pattern_df = scan_df[scan_df["candle"].isin(pattern_type)].copy()
        
        if not pattern_df.empty:
            # Metrics
            col1, col2, col3 = st.columns(3)
            
            col1.metric("🕯️ Matched Stocks", len(pattern_df))
            col2.metric("📈 Bullish Patterns", len(pattern_df[pattern_df["candle"].str.contains("Bull|Hammer", case=False, na=False)]))
            col3.metric("📉 Bearish Patterns", len(pattern_df[pattern_df["candle"].str.contains("Bear|Shooting", case=False, na=False)]))
            
            st.divider()
            
            # Display
            display_cols = [c for c in [
                "symbol", "sector", "close", "change_pct", "candle",
                "volume_ratio", "darvas_state", "trend",
                "technical_score", "combined_score", "signal"
            ] if c in pattern_df.columns]
            
            st.dataframe(
                pattern_df.sort_values("combined_score", ascending=False)[display_cols],
                use_container_width=True,
                height=500,
                column_config={
                    "close": st.column_config.NumberColumn("Price", format="₹%.2f"),
                    "change_pct": st.column_config.NumberColumn("Change %", format="%.2f%%"),
                    "combined_score": st.column_config.ProgressColumn("Score", format="%.0f", min_value=0, max_value=100),
                }
            )
            
            # Pattern distribution
            pattern_dist = pattern_df["candle"].value_counts()
            
            fig = go.Figure(data=[go.Bar(
                x=pattern_dist.index,
                y=pattern_dist.values,
                marker=dict(color=pattern_dist.values, colorscale='Viridis')
            )])
            fig.update_layout(title="Candlestick Pattern Distribution", height=400, xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
            
        else:
            st.info(f"No stocks found with selected patterns")
    else:
        st.warning("Candlestick pattern data not available. Run updater with latest code.")

with tab4:
    st.subheader("🎯 Multi-Filter Combination")
    
    st.info("💡 Combine multiple technical filters for high-conviction setups")
    
    with st.form("multi_filter"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**Darvas Box**")
            use_darvas = st.checkbox("Enable Darvas Filter")
            darvas_states = st.multiselect("States", ["Breakout", "Near Breakout"], default=["Breakout"], key="mf_darvas")
        
        with col2:
            st.markdown("**Trend**")
            use_trend = st.checkbox("Enable Trend Filter")
            trends = st.multiselect("Trends", ["Strong Uptrend", "Uptrend"], default=["Strong Uptrend"], key="mf_trend")
        
        with col3:
            st.markdown("**Volume**")
            use_volume = st.checkbox("Enable Volume Filter")
            min_vol = st.number_input("Min Volume Ratio", 0.0, 10.0, 1.5, 0.1)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**Score**")
            use_score = st.checkbox("Enable Score Filter", value=True)
            min_score = st.slider("Min Combined Score", 0, 100, 70)
        
        with col2:
            st.markdown("**RS**")
            use_rs = st.checkbox("Enable RS Filter")
            min_rs = st.number_input("Min Relative Strength %", -50, 100, 5)
        
        with col3:
            st.markdown("**PE**")
            use_pe = st.checkbox("Enable PE Filter")  # ✅ This was missing
            max_pe = st.number_input("Max PE Ratio", 0, 100, 30)
        
        submit = st.form_submit_button("🔍 Apply Filters", use_container_width=True, type="primary")
    
    if submit:
        filtered = scan_df.copy()
        
        # Apply filters
        if use_darvas and "darvas_state" in filtered.columns:
            filtered = filtered[filtered["darvas_state"].isin(darvas_states)]
        
        if use_trend and "trend" in filtered.columns:
            filtered = filtered[filtered["trend"].isin(trends)]
        
        if use_volume and "volume_ratio" in filtered.columns:
            filtered = filtered[pd.to_numeric(filtered["volume_ratio"], errors="coerce") >= min_vol]
        
        if use_score and "combined_score" in filtered.columns:
            filtered = filtered[pd.to_numeric(filtered["combined_score"], errors="coerce") >= min_score]
        
        if use_rs and "relative_strength_pct" in filtered.columns:
            filtered = filtered[pd.to_numeric(filtered["relative_strength_pct"], errors="coerce") >= min_rs]
        
        if use_pe and "pe_ratio" in filtered.columns:
            filtered = filtered[pd.to_numeric(filtered["pe_ratio"], errors="coerce").fillna(999) <= max_pe]
        
        # Results
        st.success(f"✅ Found {len(filtered)} stocks matching all filters")
        
        if not filtered.empty:
            display_cols = [c for c in [
                "symbol", "sector", "close", "darvas_state", "trend", "candle",
                "volume_ratio", "relative_strength_pct", "pe_ratio",
                "technical_score", "value_score", "combined_score", "signal"
            ] if c in filtered.columns]
            
            st.dataframe(
                filtered.sort_values("combined_score", ascending=False)[display_cols],
                use_container_width=True,
                height=500,
                column_config={
                    "close": st.column_config.NumberColumn("Price", format="₹%.2f"),
                    "combined_score": st.column_config.ProgressColumn("Score", format="%.0f", min_value=0, max_value=100),
                }
            )
            
            # Export
            csv = filtered[display_cols].to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Download Multi-Filtered Stocks",
                csv,
                f"multi_filter_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
                "text/csv"
            )
        else:
            st.warning("No stocks match all selected filters. Try relaxing some criteria.")