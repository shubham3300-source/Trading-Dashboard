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
from datetime import datetime, timedelta
from data_loader import load_user_file, save_user_file

st.set_page_config(page_title="Trade Journal", page_icon="📓", layout="wide")

journal_df = load_user_file("trade_journal.csv", ["date","symbol","setup","entry","exit","qty","pnl","lesson","tag"])

st.title("📓 Trade Journal & Performance Analytics")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["➕ Add Trade", "📊 Journal Entries", "📈 Performance Analytics", "📚 Trade Insights"])

with tab1:
    st.subheader("➕ Add New Trade Entry")
    
    with st.form("journal_form", clear_on_submit=True):
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            trade_date = st.date_input("Trade Date", value=datetime.now())
        
        with col2:
            symbol = st.text_input("Symbol", placeholder="e.g., TCS")
        
        with col3:
            setup = st.selectbox("Setup Type", [
                "Breakout",
                "Value Pick",
                "Trend Following",
                "Reversal",
                "Support/Resistance",
                "Other"
            ])
        
        with col4:
            qty = st.number_input("Quantity", min_value=1, value=1, step=1)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            entry_price = st.number_input("Entry Price", min_value=0.0, value=0.0, step=0.1, format="%.2f")
        
        with col2:
            exit_price = st.number_input("Exit Price", min_value=0.0, value=0.0, step=0.1, format="%.2f")
        
        with col3:
            tag = st.selectbox("Tag", ["Win", "Loss", "Breakeven", "Ongoing"])
        
        lesson = st.text_area("Trade Notes / Lesson Learned", placeholder="What worked? What didn't? What did you learn?", height=100)
        
        submit = st.form_submit_button("💾 Save Trade", use_container_width=True, type="primary")
        
        if submit:
            if symbol.strip():
                pnl = round((exit_price - entry_price) * qty, 2)
                pnl_pct = round((exit_price - entry_price) / entry_price * 100, 2) if entry_price > 0 else 0
                
                new_trade = pd.DataFrame([[
                    str(trade_date),
                    symbol.upper().strip(),
                    setup,
                    entry_price,
                    exit_price,
                    qty,
                    pnl,
                    lesson,
                    tag
                ]], columns=["date","symbol","setup","entry","exit","qty","pnl","lesson","tag"])
                
                journal_df = pd.concat([journal_df, new_trade], ignore_index=True)
                save_user_file("trade_journal.csv", journal_df)
                
                st.success(f"✅ Trade saved! P&L: ₹{pnl:,.2f} ({pnl_pct:+.2f}%)")
                st.rerun()
            else:
                st.error("❌ Please enter a symbol")

with tab2:
    st.subheader("📊 Trade Journal Entries")
    
    if not journal_df.empty:
        # Filters
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            symbol_filter = st.multiselect(
                "Filter by Symbol",
                options=sorted(journal_df["symbol"].unique()),
                default=[]
            )
        
        with col2:
            setup_filter = st.multiselect(
                "Filter by Setup",
                options=sorted(journal_df["setup"].unique()),
                default=[]
            )
        
        with col3:
            tag_filter = st.multiselect(
                "Filter by Tag",
                options=sorted(journal_df["tag"].unique()) if "tag" in journal_df.columns else [],
                default=[]
            )
        
        with col4:
            date_range = st.selectbox("Date Range", ["Last 7 days", "Last 30 days", "Last 90 days", "All time"])
        
        # Apply filters
        filtered_journal = journal_df.copy()
        
        if symbol_filter:
            filtered_journal = filtered_journal[filtered_journal["symbol"].isin(symbol_filter)]
        
        if setup_filter:
            filtered_journal = filtered_journal[filtered_journal["setup"].isin(setup_filter)]
        
        if tag_filter and "tag" in filtered_journal.columns:
            filtered_journal = filtered_journal[filtered_journal["tag"].isin(tag_filter)]
        
        if date_range != "All time":
            days = {"Last 7 days": 7, "Last 30 days": 30, "Last 90 days": 90}[date_range]
            cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            filtered_journal["date"] = pd.to_datetime(filtered_journal["date"], errors="coerce")
            filtered_journal = filtered_journal[filtered_journal["date"] >= cutoff_date]
        
        # Calculate returns
        filtered_journal["pnl_pct"] = (
            (pd.to_numeric(filtered_journal["exit"], errors="coerce") - 
             pd.to_numeric(filtered_journal["entry"], errors="coerce")) / 
            pd.to_numeric(filtered_journal["entry"], errors="coerce") * 100
        ).round(2)
        
        # Display
        st.dataframe(
            filtered_journal.sort_values("date", ascending=False),
            use_container_width=True,
            height=500,
            column_config={
                "date": st.column_config.DateColumn("Date", format="DD MMM YYYY"),
                "entry": st.column_config.NumberColumn("Entry", format="₹%.2f"),
                "exit": st.column_config.NumberColumn("Exit", format="₹%.2f"),
                "pnl": st.column_config.NumberColumn("P&L", format="₹%.2f"),
                "pnl_pct": st.column_config.NumberColumn("Return %", format="%.2f%%"),
            }
        )
        
        # Export
        csv = filtered_journal.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Download Journal",
            csv,
            f"trade_journal_{datetime.now().strftime('%Y%m%d')}.csv",
            "text/csv"
        )
    else:
        st.info("📝 No trades yet. Add your first trade above!")

with tab3:
    st.subheader("📈 Performance Analytics")
    
    if not journal_df.empty:
        # Calculate metrics
        journal_df["pnl_numeric"] = pd.to_numeric(journal_df["pnl"], errors="coerce").fillna(0)
        journal_df["entry_numeric"] = pd.to_numeric(journal_df["entry"], errors="coerce")
        journal_df["exit_numeric"] = pd.to_numeric(journal_df["exit"], errors="coerce")
        
        total_trades = len(journal_df)
        winning_trades = len(journal_df[journal_df["pnl_numeric"] > 0])
        losing_trades = len(journal_df[journal_df["pnl_numeric"] < 0])
        breakeven_trades = len(journal_df[journal_df["pnl_numeric"] == 0])
        
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        total_pnl = journal_df["pnl_numeric"].sum()
        avg_win = journal_df[journal_df["pnl_numeric"] > 0]["pnl_numeric"].mean() if winning_trades > 0 else 0
        avg_loss = journal_df[journal_df["pnl_numeric"] < 0]["pnl_numeric"].mean() if losing_trades > 0 else 0
        
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0
        
        # Top metrics
        col1, col2, col3, col4, col5 = st.columns(5)
        
        col1.metric("📊 Total Trades", total_trades)
        col2.metric("✅ Win Rate", f"{win_rate:.1f}%")
        col3.metric("💰 Total P&L", f"₹{total_pnl:,.2f}", delta="📈" if total_pnl > 0 else "📉")
        col4.metric("📈 Avg Win", f"₹{avg_win:,.2f}")
        col5.metric("📉 Avg Loss", f"₹{avg_loss:,.2f}")
        
        st.divider()
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            # Win/Loss distribution
            fig = go.Figure(data=[go.Pie(
                labels=['Wins', 'Losses', 'Breakeven'],
                values=[winning_trades, losing_trades, breakeven_trades],
                hole=0.4,
                marker=dict(colors=['#10b981', '#ef4444', '#94a3b8'])
            )])
            fig.update_layout(title="Win/Loss Distribution", height=350)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Setup performance
            setup_pnl = journal_df.groupby("setup")["pnl_numeric"].sum().sort_values(ascending=False)
            
            fig = go.Figure(data=[go.Bar(
                x=setup_pnl.index,
                y=setup_pnl.values,
                marker=dict(color=setup_pnl.values, colorscale='RdYlGn', showscale=True)
            )])
            fig.update_layout(title="P&L by Setup Type", height=350, xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        
        # Cumulative P&L
        journal_df["date"] = pd.to_datetime(journal_df["date"], errors="coerce")
        journal_sorted = journal_df.sort_values("date")
        journal_sorted["cumulative_pnl"] = journal_sorted["pnl_numeric"].cumsum()
        
        fig = px.line(
            journal_sorted,
            x="date",
            y="cumulative_pnl",
            title="📈 Cumulative P&L Over Time",
            markers=True
        )
        fig.add_hline(y=0, line_dash="dash", line_color="gray")
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        
        # Monthly performance
        journal_sorted["month"] = journal_sorted["date"].dt.to_period('M').astype(str)
        monthly_pnl = journal_sorted.groupby("month").agg({
            "pnl_numeric": "sum",
            "symbol": "count"
        }).rename(columns={"symbol": "trades"})
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=monthly_pnl.index,
            y=monthly_pnl["pnl_numeric"],
            name="P&L",
            marker=dict(color=monthly_pnl["pnl_numeric"], colorscale='RdYlGn')
        ))
        fig.update_layout(title="📊 Monthly P&L", height=400, xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(
            monthly_pnl.sort_index(ascending=False),
            use_container_width=True,
            column_config={
                "pnl_numeric": st.column_config.NumberColumn("P&L", format="₹%.2f"),
                "trades": st.column_config.NumberColumn("Trades")
            }
        )
        
        st.divider()
        
        # Best and worst trades
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🏆 Top 5 Winning Trades")
            best_trades = journal_df.nlargest(5, "pnl_numeric")[["date","symbol","setup","entry","exit","pnl"]]
            st.dataframe(best_trades, use_container_width=True, hide_index=True)
        
        with col2:
            st.markdown("#### 📉 Top 5 Losing Trades")
            worst_trades = journal_df.nsmallest(5, "pnl_numeric")[["date","symbol","setup","entry","exit","pnl"]]
            st.dataframe(worst_trades, use_container_width=True, hide_index=True)
        
    else:
        st.info("📊 Add some trades to see performance analytics")

with tab4:
    st.subheader("📚 Trade Insights & Learnings")
    
    if not journal_df.empty:
        # Most traded symbols
        st.markdown("#### 🎯 Most Traded Symbols")
        symbol_stats = journal_df.groupby("symbol").agg({
            "pnl": lambda x: pd.to_numeric(x, errors="coerce").sum(),
            "symbol": "count"
        }).rename(columns={"symbol": "trades", "pnl": "total_pnl"})
        symbol_stats["avg_pnl"] = (symbol_stats["total_pnl"] / symbol_stats["trades"]).round(2)
        symbol_stats = symbol_stats.sort_values("trades", ascending=False).head(10)
        
        st.dataframe(
            symbol_stats,
            use_container_width=True,
            column_config={
                "total_pnl": st.column_config.NumberColumn("Total P&L", format="₹%.2f"),
                "avg_pnl": st.column_config.NumberColumn("Avg P&L", format="₹%.2f"),
            }
        )
        
        st.divider()
        
        # Setup win rates
        st.markdown("#### 🎲 Setup Type Win Rates")
        
        setup_stats = journal_df.groupby("setup").apply(lambda x: pd.Series({
            "total_trades": len(x),
            "wins": len(x[pd.to_numeric(x["pnl"], errors="coerce") > 0]),
            "losses": len(x[pd.to_numeric(x["pnl"], errors="coerce") < 0]),
            "total_pnl": pd.to_numeric(x["pnl"], errors="coerce").sum(),
            "win_rate": len(x[pd.to_numeric(x["pnl"], errors="coerce") > 0]) / len(x) * 100
        })).reset_index()
        
        fig = px.bar(
            setup_stats,
            x="setup",
            y="win_rate",
            color="total_pnl",
            title="Win Rate by Setup Type",
            labels={"win_rate": "Win Rate %", "setup": "Setup Type"},
            color_continuous_scale="RdYlGn"
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(
            setup_stats.sort_values("win_rate", ascending=False),
            use_container_width=True,
            hide_index=True,
            column_config={
                "win_rate": st.column_config.NumberColumn("Win Rate %", format="%.1f%%"),
                "total_pnl": st.column_config.NumberColumn("Total P&L", format="₹%.2f"),
            }
        )
        
        st.divider()
        
        # Recent lessons
        st.markdown("#### 📝 Recent Trade Lessons")
        
        recent_lessons = journal_df[journal_df["lesson"].notna() & (journal_df["lesson"] != "")].tail(10)
        
        for idx, row in recent_lessons.iterrows():
            with st.expander(f"📌 {row['symbol']} - {row['date']} ({row['setup']})"):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown(f"**Lesson:** {row['lesson']}")
                
                with col2:
                    pnl_val = pd.to_numeric(row['pnl'], errors='coerce')
                    st.metric("P&L", f"₹{pnl_val:,.2f}" if pd.notna(pnl_val) else "N/A")
                    st.metric("Entry", f"₹{row['entry']}")
                    st.metric("Exit", f"₹{row['exit']}")
    else:
        st.info("📚 Add trades with lessons to build your trading knowledge base")