import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = BASE_DIR if os.path.basename(BASE_DIR) != "pages" else os.path.dirname(BASE_DIR)
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

import streamlit as st
import pandas as pd
from datetime import datetime
from data_loader import load_scan_df, load_user_file, save_user_file
from core.strategy_lab import ensure_scores

st.set_page_config(page_title="Watchlist", page_icon="👁️", layout="wide")

scan_df, _ = load_scan_df()
scan_df = ensure_scores(scan_df) if not scan_df.empty else scan_df
watchlist_df = load_user_file("watchlist.csv", ["symbol","tag","note","target_price","alert_price","added_date"])

st.title("👁️ Watchlist & Price Alerts")

# Tabs
tab1, tab2, tab3 = st.tabs(["➕ Add to Watchlist", "📋 My Watchlist", "🔔 Price Alerts"])

with tab1:
    st.subheader("➕ Add Stock to Watchlist")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        with st.form("add_watchlist", clear_on_submit=True):
            symbol = st.text_input("Stock Symbol", placeholder="e.g., TCS, INFY, RELIANCE")
            
            col1, col2 = st.columns(2)
            
            with col1:
                tag = st.selectbox("Tag/Category", [
                    "Breakout Watch",
                    "Value Pick",
                    "Long Term",
                    "Swing Trade",
                    "High Risk",
                    "Dividend Stock",
                    "Other"
                ])
            
            with col2:
                target_price = st.number_input("Target Price (Optional)", min_value=0.0, value=0.0, step=1.0)
            
            alert_price = st.number_input("Alert Price (Optional)", min_value=0.0, value=0.0, step=1.0, 
                                         help="Get notified when price crosses this level")
            
            note = st.text_area("Notes", placeholder="Why are you watching this stock?", height=100)
            
            submit = st.form_submit_button("➕ Add to Watchlist", use_container_width=True, type="primary")
            
            if submit:
                if symbol.strip():
                    symbol_upper = symbol.upper().strip()
                    
                    # Check if already in watchlist
                    if symbol_upper in watchlist_df["symbol"].values:
                        st.warning(f"⚠️ {symbol_upper} is already in your watchlist")
                    else:
                        new_entry = pd.DataFrame([[
                            symbol_upper,
                            tag,
                            note,
                            target_price if target_price > 0 else None,
                            alert_price if alert_price > 0 else None,
                            datetime.now().strftime('%Y-%m-%d')
                        ]], columns=["symbol","tag","note","target_price","alert_price","added_date"])
                        
                        watchlist_df = pd.concat([watchlist_df, new_entry], ignore_index=True)
                        save_user_file("watchlist.csv", watchlist_df)
                        
                        st.success(f"✅ {symbol_upper} added to watchlist!")
                        st.rerun()
                else:
                    st.error("❌ Please enter a symbol")
    
       with col2:
        st.markdown("#### 🚀 Quick Add from Scanner")
        
        if not scan_df.empty:
            quick_add_type = st.radio("Add from:", ["Top Breakouts", "Top Value Picks", "High Volume"])
            
            if quick_add_type == "Top Breakouts":
                top_stocks = scan_df[scan_df.get("signal","")=="Breakout Candidate"].nlargest(5, "combined_score")
            elif quick_add_type == "Top Value Picks":
                top_stocks = scan_df[scan_df.get("value_category","")=="Undervalued"].nlargest(5, "value_score")
            else:
                top_stocks = scan_df.nlargest(5, "volume_ratio") if "volume_ratio" in scan_df.columns else pd.DataFrame()
            
            if not top_stocks.empty:
                for idx, row in top_stocks.iterrows():
                    col_a, col_b = st.columns([3, 1])
                    
                    with col_a:
                        st.write(f"**{row['symbol']}** - ₹{row.get('close', 0):.2f}")
                        st.caption(f"Score: {row.get('combined_score', 0):.0f}")
                    
                    with col_b:
                        # ✅ Button OUTSIDE form with unique key
                        if st.button("➕", key=f"quick_add_{idx}_{row['symbol']}"):
                            if row['symbol'] not in watchlist_df["symbol"].values:
                                new_entry = pd.DataFrame([[
                                    row['symbol'],
                                    quick_add_type,
                                    f"Auto-added from scanner - Score: {row.get('combined_score', 0):.0f}",
                                    None,
                                    None,
                                    datetime.now().strftime('%Y-%m-%d')
                                ]], columns=["symbol","tag","note","target_price","alert_price","added_date"])
                                
                                watchlist_df = pd.concat([watchlist_df, new_entry], ignore_index=True)
                                save_user_file("watchlist.csv", watchlist_df)
                                st.success(f"✅ Added {row['symbol']}")
                                st.rerun()
                            else:
                                st.info(f"{row['symbol']} already in watchlist")

with tab2:
    st.subheader("📋 My Watchlist")
    
    if not watchlist_df.empty:
        # Merge with scan data
        merged = watchlist_df.merge(
            scan_df[[c for c in ["symbol","sector","close","change_pct","pe_ratio","roe_pct","volume_ratio","technical_score","value_score","combined_score","signal"] if c in scan_df.columns]],
            on="symbol",
            how="left"
        ) if not scan_df.empty else watchlist_df.copy()
        
        # Calculate distance to target
        if "close" in merged.columns and "target_price" in merged.columns:
            merged["target_distance_%"] = (
                (pd.to_numeric(merged["target_price"], errors="coerce") - 
                 pd.to_numeric(merged["close"], errors="coerce")) / 
                pd.to_numeric(merged["close"], errors="coerce") * 100
            ).round(2)
        
        # Filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            tag_filter = st.multiselect(
                "Filter by Tag",
                options=sorted(merged["tag"].unique()),
                default=[]
            )
        
        with col2:
            sort_by = st.selectbox("Sort by", [
                "Added Date (Recent)",
                "Combined Score (High to Low)",
                "Price Change % (High to Low)",
                "Symbol (A-Z)"
            ])
        
        with col3:
            show_alerts_only = st.checkbox("Show only with Price Alerts")
        
        # Apply filters
        filtered = merged.copy()
        
        if tag_filter:
            filtered = filtered[filtered["tag"].isin(tag_filter)]
        
        if show_alerts_only:
            filtered = filtered[filtered["alert_price"].notna() & (filtered["alert_price"] > 0)]
        
        # Sort
        if sort_by == "Added Date (Recent)":
            filtered = filtered.sort_values("added_date", ascending=False)
        elif sort_by == "Combined Score (High to Low)":
            filtered = filtered.sort_values("combined_score", ascending=False) if "combined_score" in filtered.columns else filtered
        elif sort_by == "Price Change % (High to Low)":
            filtered = filtered.sort_values("change_pct", ascending=False) if "change_pct" in filtered.columns else filtered
        else:
            filtered = filtered.sort_values("symbol")
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("👁️ Total Watchlist", len(watchlist_df))
        col2.metric("📊 Filtered", len(filtered))
        col3.metric("🔔 With Alerts", len(watchlist_df[watchlist_df["alert_price"].notna() & (watchlist_df["alert_price"] > 0)]))
        
        # Check for triggered alerts
        if "close" in filtered.columns and "alert_price" in filtered.columns:
            triggered = filtered[
                (filtered["alert_price"].notna()) & 
                (pd.to_numeric(filtered["alert_price"], errors="coerce") > 0) &
                (pd.to_numeric(filtered["close"], errors="coerce") >= pd.to_numeric(filtered["alert_price"], errors="coerce"))
            ]
            col4.metric("🚨 Triggered Alerts", len(triggered))
            
            if len(triggered) > 0:
                st.warning(f"🚨 {len(triggered)} price alert(s) triggered!")
        
        st.divider()
        
        # Display table
        display_cols = [c for c in [
            "symbol","tag","close","change_pct","target_price","target_distance_%","alert_price",
            "pe_ratio","roe_pct","volume_ratio","combined_score","signal","note","added_date"
        ] if c in filtered.columns]
        
        st.dataframe(
            filtered[display_cols],
            use_container_width=True,
            height=500,
            column_config={
                "close": st.column_config.NumberColumn("Price", format="₹%.2f"),
                "change_pct": st.column_config.NumberColumn("Change %", format="%.2f%%"),
                "target_price": st.column_config.NumberColumn("Target", format="₹%.2f"),
                "target_distance_%": st.column_config.NumberColumn("To Target %", format="%.2f%%"),
                "alert_price": st.column_config.NumberColumn("Alert Price", format="₹%.2f"),
                "combined_score": st.column_config.ProgressColumn("Score", format="%.0f", min_value=0, max_value=100),
                "added_date": st.column_config.DateColumn("Added", format="DD MMM YYYY"),
            }
        )
        
        # Actions
        col1, col2, col3 = st.columns(3)
        
        with col1:
            csv = filtered[display_cols].to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Download Watchlist",
                csv,
                f"watchlist_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv"
            )
        
        with col2:
            remove_symbol = st.selectbox("Remove from watchlist", [""] + sorted(watchlist_df["symbol"].unique()))
            if st.button("🗑️ Remove", use_container_width=True) and remove_symbol:
                watchlist_df = watchlist_df[watchlist_df["symbol"] != remove_symbol]
                save_user_file("watchlist.csv", watchlist_df)
                st.success(f"✅ Removed {remove_symbol}")
                st.rerun()
        
        with col3:
            if st.button("🗑️ Clear All Watchlist", use_container_width=True):
                if st.session_state.get("confirm_clear"):
                    watchlist_df = pd.DataFrame(columns=["symbol","tag","note","target_price","alert_price","added_date"])
                    save_user_file("watchlist.csv", watchlist_df)
                    st.success("✅ Watchlist cleared")
                    st.session_state["confirm_clear"] = False
                    st.rerun()
                else:
                    st.session_state["confirm_clear"] = True
                    st.warning("⚠️ Click again to confirm")
    
    else:
        st.info("👁️ Your watchlist is empty. Add some stocks above!")

with tab3:
    st.subheader("🔔 Price Alert Monitor")
    
    if not watchlist_df.empty:
        # Filter stocks with alerts
        alerts_watch = watchlist_df[watchlist_df["alert_price"].notna() & (watchlist_df["alert_price"] > 0)]
        
        if not alerts_watch.empty:
            # Merge with current prices
            alerts_merged = alerts_watch.merge(
                scan_df[["symbol","close","change_pct"]] if not scan_df.empty and "close" in scan_df.columns else pd.DataFrame(),
                on="symbol",
                how="left"
            )
            
            # Calculate distance to alert
            alerts_merged["distance_to_alert_%"] = (
                (pd.to_numeric(alerts_merged["alert_price"], errors="coerce") - 
                 pd.to_numeric(alerts_merged["close"], errors="coerce")) / 
                pd.to_numeric(alerts_merged["close"], errors="coerce") * 100
            ).round(2)
            
            # Check triggered
            alerts_merged["status"] = alerts_merged.apply(
                lambda row: "🚨 TRIGGERED" if pd.notna(row.get("close")) and 
                           pd.to_numeric(row.get("close", 0), errors="coerce") >= 
                           pd.to_numeric(row.get("alert_price", 0), errors="coerce") 
                else "⏳ Pending",
                axis=1
            )
            
            # Display
            st.dataframe(
                alerts_merged[["symbol","close","alert_price","distance_to_alert_%","status","tag","note"]],
                use_container_width=True,
                height=400,
                column_config={
                    "close": st.column_config.NumberColumn("Current Price", format="₹%.2f"),
                    "alert_price": st.column_config.NumberColumn("Alert Price", format="₹%.2f"),
                    "distance_to_alert_%": st.column_config.NumberColumn("Distance %", format="%.2f%%"),
                }
            )
            
            # Show triggered alerts
            triggered = alerts_merged[alerts_merged["status"] == "🚨 TRIGGERED"]
            
            if not triggered.empty:
                st.error(f"🚨 {len(triggered)} alert(s) triggered!")
                
                for idx, row in triggered.iterrows():
                    st.warning(f"**{row['symbol']}** reached alert price ₹{row['alert_price']:.2f} (Current: ₹{row.get('close', 0):.2f})")
        else:
            st.info("🔔 No price alerts set. Add alert prices in your watchlist!")
    else:
        st.info("👁️ Add stocks to watchlist first")