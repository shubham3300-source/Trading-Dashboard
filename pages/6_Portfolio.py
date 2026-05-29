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

st.set_page_config(page_title="Portfolio", page_icon="💼", layout="wide")

scan_df, _ = load_scan_df()
scan_df = ensure_scores(scan_df) if not scan_df.empty else scan_df
portfolio_df = load_user_file("portfolio.csv", ["symbol","qty","buy_price","target","stop_loss","buy_date","notes"])

st.title("💼 Portfolio & Position Management")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["➕ Add Position", "📊 Current Portfolio", "📈 Analytics", "🎯 Risk Management"])

with tab1:
    st.subheader("➕ Add New Position")
    
    with st.form("portfolio_form", clear_on_submit=True):
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            symbol = st.text_input("Symbol", placeholder="e.g., TCS")
        
        with col2:
            qty = st.number_input("Quantity", min_value=1, value=1, step=1)
        
        with col3:
            buy_price = st.number_input("Buy Price", min_value=0.0, value=0.0, step=0.1, format="%.2f")
        
        with col4:
            buy_date = st.date_input("Buy Date", value=datetime.now())
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            target = st.number_input("Target Price", min_value=0.0, value=0.0, step=1.0)
        
        with col2:
            stop_loss = st.number_input("Stop Loss", min_value=0.0, value=0.0, step=1.0)
        
        with col3:
            st.write("")  # Spacing
        
        notes = st.text_area("Position Notes", placeholder="Reason for entry, strategy, etc.", height=80)
        
        submit = st.form_submit_button("💾 Add Position", use_container_width=True, type="primary")
        
        if submit:
            if symbol.strip() and buy_price > 0:
                new_position = pd.DataFrame([[
                    symbol.upper().strip(),
                    qty,
                    buy_price,
                    target if target > 0 else None,
                    stop_loss if stop_loss > 0 else None,
                    str(buy_date),
                    notes
                ]], columns=["symbol","qty","buy_price","target","stop_loss","buy_date","notes"])
                
                portfolio_df = pd.concat([portfolio_df, new_position], ignore_index=True)
                save_user_file("portfolio.csv", portfolio_df)
                
                investment = buy_price * qty
                st.success(f"✅ Added {qty} shares of {symbol.upper()} @ ₹{buy_price:.2f} (Total: ₹{investment:,.2f})")
                st.rerun()
            else:
                st.error("❌ Please enter symbol and buy price")

with tab2:
    st.subheader("📊 Current Portfolio")
    
    if not portfolio_df.empty:
        # Merge with current prices
        merged = portfolio_df.merge(
            scan_df[[c for c in ["symbol","close","change_pct","pe_ratio","combined_score","signal"] if c in scan_df.columns]],
            on="symbol",
            how="left"
        ) if not scan_df.empty else portfolio_df.copy()
        
        # Calculate P&L
        if "close" in merged.columns:
            merged["current_value"] = pd.to_numeric(merged["close"], errors="coerce") * pd.to_numeric(merged["qty"], errors="coerce")
            merged["investment"] = pd.to_numeric(merged["buy_price"], errors="coerce") * pd.to_numeric(merged["qty"], errors="coerce")
            merged["mtm_pnl"] = merged["current_value"] - merged["investment"]
            merged["pnl_pct"] = (merged["mtm_pnl"] / merged["investment"] * 100).round(2)
            
            # Target & SL distances
            merged["to_target_%"] = (
                (pd.to_numeric(merged["target"], errors="coerce") - pd.to_numeric(merged["close"], errors="coerce")) /
                pd.to_numeric(merged["close"], errors="coerce") * 100
            ).round(2)
            
            merged["to_sl_%"] = (
                (pd.to_numeric(merged["close"], errors="coerce") - pd.to_numeric(merged["stop_loss"], errors="coerce")) /
                pd.to_numeric(merged["close"], errors="coerce") * 100
            ).round(2)
        
        # Portfolio summary
        total_investment = merged["investment"].sum() if "investment" in merged.columns else 0
        total_current = merged["current_value"].sum() if "current_value" in merged.columns else 0
        total_pnl = total_current - total_investment
        total_pnl_pct = (total_pnl / total_investment * 100) if total_investment > 0 else 0
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        col1.metric("💰 Investment", f"₹{total_investment:,.0f}")
        col2.metric("💵 Current Value", f"₹{total_current:,.0f}")
        col3.metric("📊 Total P&L", f"₹{total_pnl:,.0f}", delta=f"{total_pnl_pct:+.2f}%")
        col4.metric("📈 Positions", len(portfolio_df))
        col5.metric("🎯 Avg Return", f"{merged['pnl_pct'].mean():.2f}%" if "pnl_pct" in merged.columns else "N/A")
        
        st.divider()
        
        # Display portfolio
        display_cols = [c for c in [
            "symbol","qty","buy_price","close","target","stop_loss",
            "investment","current_value","mtm_pnl","pnl_pct",
            "to_target_%","to_sl_%","combined_score","signal","buy_date"
        ] if c in merged.columns]
        
        # Color code P&L
        def color_pnl(val):
            if pd.isna(val):
                return ''
            color = 'green' if val > 0 else 'red' if val < 0 else 'gray'
            return f'color: {color}'
        
        st.dataframe(
            merged[display_cols].sort_values("mtm_pnl", ascending=False) if "mtm_pnl" in merged.columns else merged[display_cols],
            use_container_width=True,
            height=500,
            column_config={
                "buy_price": st.column_config.NumberColumn("Buy Price", format="₹%.2f"),
                "close": st.column_config.NumberColumn("CMP", format="₹%.2f"),
                "target": st.column_config.NumberColumn("Target", format="₹%.2f"),
                "stop_loss": st.column_config.NumberColumn("SL", format="₹%.2f"),
                "investment": st.column_config.NumberColumn("Invested", format="₹%.0f"),
                "current_value": st.column_config.NumberColumn("Current", format="₹%.0f"),
                "mtm_pnl": st.column_config.NumberColumn("P&L", format="₹%.0f"),
                "pnl_pct": st.column_config.NumberColumn("Return %", format="%.2f%%"),
                "to_target_%": st.column_config.NumberColumn("To Target %", format="%.2f%%"),
                "to_sl_%": st.column_config.NumberColumn("From SL %", format="%.2f%%"),
                "combined_score": st.column_config.ProgressColumn("Score", format="%.0f", min_value=0, max_value=100),
                "buy_date": st.column_config.DateColumn("Buy Date", format="DD MMM YYYY"),
            }
        )
        
        # Check SL triggers
        if "to_sl_%" in merged.columns:
            sl_triggered = merged[
                (merged["stop_loss"].notna()) & 
                (pd.to_numeric(merged["to_sl_%"], errors="coerce") <= 0)
            ]
            
            if not sl_triggered.empty:
                st.error(f"🚨 {len(sl_triggered)} position(s) hit stop loss!")
                for idx, row in sl_triggered.iterrows():
                    st.warning(f"**{row['symbol']}**: SL ₹{row['stop_loss']:.2f} hit (CMP: ₹{row.get('close', 0):.2f})")
        
        # Check target hits
        if "to_target_%" in merged.columns:
            target_hit = merged[
                (merged["target"].notna()) & 
                (pd.to_numeric(merged["to_target_%"], errors="coerce") <= 0)
            ]
            
            if not target_hit.empty:
                st.success(f"🎯 {len(target_hit)} position(s) hit target!")
                for idx, row in target_hit.iterrows():
                    st.success(f"**{row['symbol']}**: Target ₹{row['target']:.2f} achieved (CMP: ₹{row.get('close', 0):.2f})")
        
        st.divider()
        
        # Actions
        col1, col2, col3 = st.columns(3)
        
        with col1:
            csv = merged[display_cols].to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Download Portfolio",
                csv,
                f"portfolio_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv"
            )
        
        with col2:
            remove_symbol = st.selectbox("Close position", [""] + sorted(portfolio_df["symbol"].unique()))
            if st.button("🗑️ Close Position", use_container_width=True) and remove_symbol:
                portfolio_df = portfolio_df[portfolio_df["symbol"] != remove_symbol]
                save_user_file("portfolio.csv", portfolio_df)
                st.success(f"✅ Closed position in {remove_symbol}")
                st.rerun()
        
        with col3:
            if st.button("📊 Export to Journal", use_container_width=True):
                st.info("💡 Feature coming soon: Auto-export closed positions to trade journal")
    
    else:
        st.info("💼 Your portfolio is empty. Add your first position above!")

with tab3:
    st.subheader("📈 Portfolio Analytics")
    
    if not portfolio_df.empty and not scan_df.empty:
        merged = portfolio_df.merge(scan_df[["symbol","close","sector"]], on="symbol", how="left")
        
        if "close" in merged.columns:
            merged["current_value"] = pd.to_numeric(merged["close"], errors="coerce") * pd.to_numeric(merged["qty"], errors="coerce")
            merged["investment"] = pd.to_numeric(merged["buy_price"], errors="coerce") * pd.to_numeric(merged["qty"], errors="coerce")
            merged["mtm_pnl"] = merged["current_value"] - merged["investment"]
            
            # Pie charts
            col1, col2 = st.columns(2)
            
            with col1:
                # Portfolio allocation by value
                fig = px.pie(
                    merged,
                    values="current_value",
                    names="symbol",
                    title="Portfolio Allocation (Current Value)",
                    hole=0.4
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # P&L contribution
                fig = px.bar(
                    merged.sort_values("mtm_pnl", ascending=True),
                    x="mtm_pnl",
                    y="symbol",
                    orientation='h',
                    title="P&L Contribution by Stock",
                    color="mtm_pnl",
                    color_continuous_scale="RdYlGn"
                )
                st.plotly_chart(fig, use_container_width=True)
            
            st.divider()
            
            # Sector allocation
            if "sector" in merged.columns:
                sector_alloc = merged.groupby("sector")["current_value"].sum().sort_values(ascending=False)
                
                fig = px.bar(
                    x=sector_alloc.index,
                    y=sector_alloc.values,
                    title="Sector-wise Allocation",
                    labels={"x": "Sector", "y": "Value (₹)"}
                )
                st.plotly_chart(fig, use_container_width=True)
            
            st.divider()
            
            # Top performers
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 🏆 Top Gainers")
                top_gain = merged.nlargest(5, "mtm_pnl")[["symbol","buy_price","close","mtm_pnl"]]
                st.dataframe(top_gain, use_container_width=True, hide_index=True)
            
            with col2:
                st.markdown("#### 📉 Top Losers")
                top_loss = merged.nsmallest(5, "mtm_pnl")[["symbol","buy_price","close","mtm_pnl"]]
                st.dataframe(top_loss, use_container_width=True, hide_index=True)
    
    else:
        st.info("📊 Add positions to see analytics")

with tab4:
    st.subheader("🎯 Risk Management Dashboard")
    
    if not portfolio_df.empty and not scan_df.empty:
        merged = portfolio_df.merge(scan_df[["symbol","close"]], on="symbol", how="left")
        
        if "close" in merged.columns:
            merged["investment"] = pd.to_numeric(merged["buy_price"], errors="coerce") * pd.to_numeric(merged["qty"], errors="coerce")
            merged["risk_amt"] = (pd.to_numeric(merged["buy_price"], errors="coerce") - pd.to_numeric(merged["stop_loss"], errors="coerce")) * pd.to_numeric(merged["qty"], errors="coerce")
            merged["risk_pct"] = (merged["risk_amt"] / merged["investment"] * 100).round(2)
            merged["reward_amt"] = (pd.to_numeric(merged["target"], errors="coerce") - pd.to_numeric(merged["buy_price"], errors="coerce")) * pd.to_numeric(merged["qty"], errors="coerce")
            merged["reward_pct"] = (merged["reward_amt"] / merged["investment"] * 100).round(2)
            merged["rr_ratio"] = (merged["reward_amt"] / merged["risk_amt"]).round(2)
            
            # Risk summary
            total_investment = merged["investment"].sum()
            total_risk = merged["risk_amt"].sum()
            portfolio_risk_pct = (total_risk / total_investment * 100) if total_investment > 0 else 0
            
            col1, col2, col3, col4 = st.columns(4)
            
            col1.metric("💰 Total Investment", f"₹{total_investment:,.0f}")
            col2.metric("⚠️ Total Risk", f"₹{total_risk:,.0f}")
            col3.metric("📊 Portfolio Risk %", f"{portfolio_risk_pct:.2f}%")
            col4.metric("🎯 Avg R:R Ratio", f"{merged['rr_ratio'].mean():.2f}" if "rr_ratio" in merged.columns else "N/A")
            
            st.divider()
            
            # Risk table
            risk_cols = ["symbol","investment","risk_amt","risk_pct","reward_amt","reward_pct","rr_ratio"]
            risk_cols = [c for c in risk_cols if c in merged.columns]
            
            st.dataframe(
                merged[risk_cols].sort_values("risk_pct", ascending=False),
                use_container_width=True,
                height=400,
                column_config={
                    "investment": st.column_config.NumberColumn("Investment", format="₹%.0f"),
                    "risk_amt": st.column_config.NumberColumn("Risk Amount", format="₹%.0f"),
                    "risk_pct": st.column_config.NumberColumn("Risk %", format="%.2f%%"),
                    "reward_amt": st.column_config.NumberColumn("Reward Amount", format="₹%.0f"),
                    "reward_pct": st.column_config.NumberColumn("Reward %", format="%.2f%%"),
                    "rr_ratio": st.column_config.NumberColumn("R:R Ratio", format="%.2f"),
                }
            )
            
            st.divider()
            
            # Risk distribution
            fig = px.bar(
                merged.sort_values("risk_pct", ascending=False),
                x="symbol",
                y="risk_pct",
                title="Position-wise Risk %",
                color="rr_ratio",
                color_continuous_scale="RdYlGn"
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Recommendations
            st.markdown("#### 💡 Risk Management Insights")
            
            high_risk = merged[merged["risk_pct"] > 5]
            if not high_risk.empty:
                st.warning(f"⚠️ {len(high_risk)} position(s) have >5% risk: {', '.join(high_risk['symbol'].tolist())}")
            
            poor_rr = merged[merged["rr_ratio"] < 1.5]
            if not poor_rr.empty:
                st.warning(f"⚠️ {len(poor_rr)} position(s) have R:R < 1.5: {', '.join(poor_rr['symbol'].tolist())}")
            
            if high_risk.empty and poor_rr.empty:
                st.success("✅ Portfolio risk parameters look healthy!")
    
    else:
        st.info("🎯 Add positions with SL & target to see risk analysis")