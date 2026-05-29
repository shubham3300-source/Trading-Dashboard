import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = BASE_DIR if os.path.basename(BASE_DIR) != "pages" else os.path.dirname(BASE_DIR)
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from data_loader import load_scan_df, load_user_file, save_user_file
from core.strategy_lab import ensure_scores

st.set_page_config(page_title="Strategy Lab", page_icon="🔬", layout="wide")

scan_df, _ = load_scan_df()
scan_df = ensure_scores(scan_df) if not scan_df.empty else scan_df

st.title("🔬 Strategy Lab & Backtesting")

if scan_df.empty:
    st.warning("No data.")
    st.stop()

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📊 Score Analysis", "🎯 Custom Strategy", "📈 Backtesting", "💡 Strategy Ideas"])

with tab1:
    st.subheader("📊 Multi-Dimensional Score Analysis")
    
    # Prepare data for plotting (handle negative/null values)
    plot_df = scan_df.copy()
    
    # Ensure numeric columns
    for col in ["value_score", "technical_score", "combined_score", "pe_ratio", "roe_pct", "market_cap_cr"]:
        if col in plot_df.columns:
            plot_df[col] = pd.to_numeric(plot_df[col], errors="coerce").fillna(0)
    
    # Create positive size values (clip at minimum 1 for visibility)
    plot_df["plot_size"] = plot_df["combined_score"].clip(lower=1)
    plot_df["plot_market_cap"] = plot_df["market_cap_cr"].clip(lower=1) if "market_cap_cr" in plot_df.columns else 1
    
    # Score distribution
    col1, col2 = st.columns(2)
    
    with col1:
        # Value vs Technical scatter
        fig = px.scatter(
            plot_df,
            x="value_score",
            y="technical_score",
            color="signal",
            size="plot_size",
            hover_data=["symbol", "sector", "close", "pe_ratio", "combined_score"],
            title="Value vs Technical Score Matrix",
            labels={"value_score": "Value Score", "technical_score": "Technical Score"},
            color_discrete_sequence=px.colors.qualitative.Bold
        )
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # PE vs ROE scatter
        # Filter valid PE and ROE values
        pe_roe_df = plot_df[
            (plot_df["pe_ratio"] > 0) & 
            (plot_df["pe_ratio"] < 100) &
            (plot_df["roe_pct"] > -50) &
            (plot_df["roe_pct"] < 100)
        ].copy()
        
        if not pe_roe_df.empty:
            fig = px.scatter(
                pe_roe_df,
                x="pe_ratio",
                y="roe_pct",
                color="combined_score",
                size="plot_market_cap",
                hover_data=["symbol", "sector", "pb_ratio"],
                title="PE vs ROE Analysis",
                labels={"pe_ratio": "PE Ratio", "roe_pct": "ROE %"},
                color_continuous_scale="RdYlGn"
            )
            fig.update_xaxes(range=[0, 50])
            fig.update_yaxes(range=[0, 40])
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Insufficient data for PE vs ROE analysis")
    
    st.divider()
    
    # Score distribution histograms
    col1, col2, col3 = st.columns(3)
    
    with col1:
        fig = px.histogram(
            plot_df[plot_df["combined_score"] >= 0], 
            x="combined_score", 
            nbins=20, 
            title="Combined Score Distribution"
        )
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        fig = px.histogram(
            plot_df[plot_df["technical_score"] >= 0], 
            x="technical_score", 
            nbins=20, 
            title="Technical Score Distribution"
        )
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
    
    with col3:
        fig = px.histogram(
            plot_df[plot_df["value_score"] >= 0], 
            x="value_score", 
            nbins=20, 
            title="Value Score Distribution"
        )
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    # Top performers table
    st.subheader("🏆 Top Performers by Score")
    
    cols_to_show = [c for c in ["symbol","sector","close","pe_ratio","roe_pct","technical_score","value_score","combined_score","signal"] if c in scan_df.columns]
    
    top_combined = scan_df.nlargest(10, "combined_score")
    st.markdown("#### Top 10 by Combined Score")
    st.dataframe(
        top_combined[cols_to_show], 
        use_container_width=True, 
        height=300,
        column_config={
            "close": st.column_config.NumberColumn("Price", format="₹%.2f"),
            "combined_score": st.column_config.ProgressColumn("Combined", format="%.0f", min_value=0, max_value=100),
            "technical_score": st.column_config.ProgressColumn("Technical", format="%.0f", min_value=0, max_value=100),
            "value_score": st.column_config.ProgressColumn("Value", format="%.0f", min_value=0, max_value=100),
        }
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        top_technical = scan_df.nlargest(10, "technical_score")
        st.markdown("#### Top 10 by Technical Score")
        st.dataframe(
            top_technical[cols_to_show], 
            use_container_width=True, 
            height=300,
            column_config={
                "close": st.column_config.NumberColumn("Price", format="₹%.2f"),
                "technical_score": st.column_config.ProgressColumn("Technical", format="%.0f", min_value=0, max_value=100),
            }
        )
    
    with col2:
        top_value = scan_df.nlargest(10, "value_score")
        st.markdown("#### Top 10 by Value Score")
        st.dataframe(
            top_value[cols_to_show], 
            use_container_width=True, 
            height=300,
            column_config={
                "close": st.column_config.NumberColumn("Price", format="₹%.2f"),
                "value_score": st.column_config.ProgressColumn("Value", format="%.0f", min_value=0, max_value=100),
            }
        )

with tab2:
    st.subheader("🎯 Custom Strategy Builder")
    
    st.info("💡 Create your own stock screening strategy by setting custom criteria")
    
    with st.expander("📋 Strategy Parameters", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("##### Score Criteria")
            min_comb = st.slider("Min Combined Score", 0, 100, 70)
            min_tech = st.slider("Min Technical Score", 0, 100, 50)
            min_val = st.slider("Min Value Score", 0, 100, 40)
        
        with col2:
            st.markdown("##### Fundamental Criteria")
            max_pe = st.slider("Max PE Ratio", 0, 100, 25)
            min_roe = st.slider("Min ROE %", 0, 50, 12)
            max_debt = st.slider("Max Debt/Equity", 0.0, 3.0, 1.0)
        
        with col3:
            st.markdown("##### Technical Criteria")
            min_vol = st.slider("Min Volume Ratio", 0.0, 5.0, 1.5)
            min_rs = st.slider("Min Relative Strength %", -20, 50, 2)
            signal_filter = st.multiselect(
                "Signal Types",
                ["Breakout Candidate", "Near Breakout", "Strong Uptrend", "Trend Strength - Monitor"],
                default=["Breakout Candidate", "Near Breakout"]
            )
    
    # Apply custom strategy
    strategy_df = scan_df.copy()
    
    if "combined_score" in strategy_df.columns:
        strategy_df = strategy_df[pd.to_numeric(strategy_df["combined_score"], errors="coerce") >= min_comb]
    if "technical_score" in strategy_df.columns:
        strategy_df = strategy_df[pd.to_numeric(strategy_df["technical_score"], errors="coerce") >= min_tech]
    if "value_score" in strategy_df.columns:
        strategy_df = strategy_df[pd.to_numeric(strategy_df["value_score"], errors="coerce") >= min_val]
    if "pe_ratio" in strategy_df.columns:
        strategy_df = strategy_df[pd.to_numeric(strategy_df["pe_ratio"], errors="coerce").fillna(999) <= max_pe]
    if "roe_pct" in strategy_df.columns:
        strategy_df = strategy_df[pd.to_numeric(strategy_df["roe_pct"], errors="coerce").fillna(0) >= min_roe]
    if "debt_equity" in strategy_df.columns:
        strategy_df = strategy_df[pd.to_numeric(strategy_df["debt_equity"], errors="coerce").fillna(999) <= max_debt]
    if "volume_ratio" in strategy_df.columns:
        strategy_df = strategy_df[pd.to_numeric(strategy_df["volume_ratio"], errors="coerce").fillna(0) >= min_vol]
    if "relative_strength_pct" in strategy_df.columns:
        strategy_df = strategy_df[pd.to_numeric(strategy_df["relative_strength_pct"], errors="coerce").fillna(-999) >= min_rs]
    if "signal" in strategy_df.columns and signal_filter:
        strategy_df = strategy_df[strategy_df["signal"].isin(signal_filter)]
    
    strategy_df = strategy_df.sort_values("combined_score", ascending=False)
    
    # Results
    st.divider()
    st.subheader(f"📋 Strategy Results: {len(strategy_df)} stocks matched")
    
    if not strategy_df.empty:
        cols_to_show = [c for c in ["symbol","sector","close","pe_ratio","roe_pct","volume_ratio","relative_strength_pct","technical_score","value_score","combined_score","signal"] if c in strategy_df.columns]
        st.dataframe(strategy_df[cols_to_show], use_container_width=True, height=400)
        
        # Export strategy
        col1, col2, col3 = st.columns(3)
        
        with col1:
            csv = strategy_df[cols_to_show].to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Download Results",
                csv,
                f"custom_strategy_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "text/csv",
                use_container_width=True
            )
        
        with col2:
            strategy_name = st.text_input("Strategy Name", "My Custom Strategy")
        
        with col3:
            if st.button("💾 Save Strategy", use_container_width=True):
                strategy_params = {
                    "name": strategy_name,
                    "date": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "min_combined_score": min_comb,
                    "min_technical_score": min_tech,
                    "min_value_score": min_val,
                    "max_pe": max_pe,
                    "min_roe": min_roe,
                    "max_debt_equity": max_debt,
                    "min_volume_ratio": min_vol,
                    "min_rs": min_rs,
                    "signals": ",".join(signal_filter),
                    "matched_stocks": len(strategy_df)
                }
                
                strategies_df = load_user_file("saved_strategies.csv", list(strategy_params.keys()))
                strategies_df = pd.concat([strategies_df, pd.DataFrame([strategy_params])], ignore_index=True)
                save_user_file("saved_strategies.csv", strategies_df)
                st.success(f"✅ Strategy '{strategy_name}' saved!")
    else:
        st.warning("No stocks matched your criteria. Try relaxing the parameters.")

with tab3:
    st.subheader("📈 Simple Backtesting")
    
    st.info("💡 Backtest your strategy on historical scanner data")
    
    # Load saved strategies
    strategies_df = load_user_file("saved_strategies.csv", ["name","date","min_combined_score","matched_stocks"])
    
    if not strategies_df.empty:
        st.markdown("#### 📚 Your Saved Strategies")
        st.dataframe(strategies_df, use_container_width=True, height=200)
    
    st.markdown("#### 🔍 Historical Performance")
    
    # Simple backtest simulation
    backtest_period = st.selectbox("Select Period", ["1 Week", "2 Weeks", "1 Month", "3 Months"])
    
    if st.button("🚀 Run Backtest", use_container_width=True):
        # Simulate backtest results (simplified version)
        st.info("📊 Backtest simulation based on current top picks...")
        
        top_picks = scan_df.nlargest(20, "combined_score")
        
        # Simulated returns (random for demo - replace with actual historical data)
        import numpy as np
        simulated_returns = np.random.normal(5, 10, len(top_picks))
        
        backtest_results = top_picks.copy()
        backtest_results["simulated_return_%"] = simulated_returns
        backtest_results["profit_loss"] = (backtest_results["close"] * simulated_returns / 100).round(2)
        
        st.dataframe(
            backtest_results[["symbol","sector","close","combined_score","simulated_return_%","profit_loss"]],
            use_container_width=True,
            height=400
        )
        
        avg_return = simulated_returns.mean()
        win_rate = (simulated_returns > 0).sum() / len(simulated_returns) * 100
        
        col1, col2, col3 = st.columns(3)
        col1.metric("📊 Avg Return", f"{avg_return:.2f}%")
        col2.metric("✅ Win Rate", f"{win_rate:.1f}%")
        col3.metric("📈 Total P&L", f"₹{backtest_results['profit_loss'].sum():.2f}")
        
        st.warning("⚠️ Note: This is a simulated backtest. Replace with actual historical data for real results.")

with tab4:
    st.subheader("💡 Pre-Built Strategy Ideas")
    
    strategies = {
        "🚀 Momentum Breakout": {
            "description": "High momentum stocks breaking out of consolidation",
            "criteria": "Combined Score > 75, Volume Ratio > 2.0, Signal = Breakout Candidate",
            "filters": {"combined_score": 75, "volume_ratio": 2.0, "signal": "Breakout Candidate"}
        },
        "💎 Value Investment": {
            "description": "Undervalued stocks with strong fundamentals",
            "criteria": "PE < 15, ROE > 18%, Debt/Equity < 0.6, Value Score > 70",
            "filters": {"pe_ratio": 15, "roe_pct": 18, "debt_equity": 0.6, "value_score": 70}
        },
        "⚡ Quality Growth": {
            "description": "High quality stocks with growth potential",
            "criteria": "ROE > 20%, PE < 30, Technical Score > 60, RS > 5%",
            "filters": {"roe_pct": 20, "pe_ratio": 30, "technical_score": 60, "relative_strength_pct": 5}
        },
        "🎯 Balanced Play": {
            "description": "Mix of value and momentum",
            "criteria": "Combined Score > 65, PE < 25, ROE > 12%, Volume Ratio > 1.5",
            "filters": {"combined_score": 65, "pe_ratio": 25, "roe_pct": 12, "volume_ratio": 1.5}
        },
        "🔥 High Conviction": {
            "description": "Only the best setups",
            "criteria": "Combined Score > 80, Value Score > 60, Technical Score > 70",
            "filters": {"combined_score": 80, "value_score": 60, "technical_score": 70}
        }
    }
    
    for strategy_name, details in strategies.items():
        with st.expander(f"{strategy_name}", expanded=False):
            st.markdown(f"**Description:** {details['description']}")
            st.markdown(f"**Criteria:** {details['criteria']}")
            
            # Apply filters
                        # Apply filters
            temp_df = scan_df.copy()
            
            if "combined_score" in details["filters"]:
                temp_df = temp_df[pd.to_numeric(temp_df.get("combined_score", 0), errors="coerce") >= details["filters"]["combined_score"]]
            if "technical_score" in details["filters"]:
                temp_df = temp_df[pd.to_numeric(temp_df.get("technical_score", 0), errors="coerce") >= details["filters"]["technical_score"]]
            if "value_score" in details["filters"]:
                temp_df = temp_df[pd.to_numeric(temp_df.get("value_score", 0), errors="coerce") >= details["filters"]["value_score"]]
            if "pe_ratio" in details["filters"]:
                temp_df = temp_df[pd.to_numeric(temp_df.get("pe_ratio", 999), errors="coerce") <= details["filters"]["pe_ratio"]]
            if "roe_pct" in details["filters"]:
                temp_df = temp_df[pd.to_numeric(temp_df.get("roe_pct", 0), errors="coerce") >= details["filters"]["roe_pct"]]
            if "debt_equity" in details["filters"]:
                temp_df = temp_df[pd.to_numeric(temp_df.get("debt_equity", 999), errors="coerce") <= details["filters"]["debt_equity"]]
            if "volume_ratio" in details["filters"]:
                temp_df = temp_df[pd.to_numeric(temp_df.get("volume_ratio", 0), errors="coerce") >= details["filters"]["volume_ratio"]]
            if "relative_strength_pct" in details["filters"]:
                temp_df = temp_df[pd.to_numeric(temp_df.get("relative_strength_pct", -999), errors="coerce") >= details["filters"]["relative_strength_pct"]]
            if "signal" in details["filters"]:
                temp_df = temp_df[temp_df.get("signal", "") == details["filters"]["signal"]]