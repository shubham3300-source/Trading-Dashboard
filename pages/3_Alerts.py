import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = BASE_DIR if os.path.basename(BASE_DIR) != "pages" else os.path.dirname(BASE_DIR)
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from data_loader import load_scan_df, load_user_file, save_user_file
from core.strategy_lab import ensure_scores
from services.telegram_service import send_message

st.set_page_config(page_title="Alerts", page_icon="🔔", layout="wide")

scan_df, _ = load_scan_df()
scan_df = ensure_scores(scan_df) if not scan_df.empty else scan_df
alerts_df = load_user_file("alert_history.csv", ["date","symbol","signal","message","status"])

st.title("🔔 Alert Center & Automation")

# Tabs
tab1, tab2, tab3 = st.tabs(["📤 Send Alerts", "📊 Alert History", "⏰ Alert Scheduler"])

with tab1:
    st.subheader("📤 Send Alerts to Telegram")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("#### 🚀 Quick Alert Templates")
        
        alert_type = st.radio(
            "Select Alert Type",
            ["Top Breakouts", "Top Value Picks", "High Volume Surge", "Custom Message"]
        )
        
        if alert_type == "Top Breakouts":
            num_stocks = st.slider("Number of stocks", 1, 10, 5)
            
            if st.button("📱 Send Top Breakout Alerts", use_container_width=True):
                if not scan_df.empty:
                    top = scan_df[scan_df.get("signal","")=="Breakout Candidate"].sort_values("combined_score", ascending=False).head(num_stocks)
                    
                    if not top.empty:
                        msg = f"🚀 Top {len(top)} Breakout Candidates - {datetime.now().strftime('%d %b %Y, %I:%M %p')}\n\n"
                        for idx, r in top.iterrows():
                            msg += f"• {r['symbol']} ({r.get('sector','')})\n"
                            msg += f"  Price: ₹{r.get('close',0):.2f} | Score: {r.get('combined_score',0):.0f}\n"
                            msg += f"  PE: {r.get('pe_ratio','N/A')} | ROE: {r.get('roe_pct','N/A')}%\n\n"
                        
                        ok, resp = send_message(msg)
                        status = "sent" if ok else "failed"
                        
                        for idx, r in top.iterrows():
                            new = pd.DataFrame([[datetime.now().strftime('%Y-%m-%d %H:%M:%S'), r['symbol'], "breakout", msg, status]], 
                                             columns=["date","symbol","signal","message","status"])
                            alerts_df = pd.concat([alerts_df, new], ignore_index=True)
                        
                        save_user_file("alert_history.csv", alerts_df)
                        
                        if ok:
                            st.success(f"✅ Sent {len(top)} breakout alerts!")
                        else:
                            st.error(f"❌ Failed: {resp}")
                    else:
                        st.warning("No breakout candidates found")
        
        elif alert_type == "Top Value Picks":
            num_stocks = st.slider("Number of stocks", 1, 10, 5)
            
            if st.button("📱 Send Top Value Alerts", use_container_width=True):
                if not scan_df.empty:
                    top = scan_df[scan_df.get("value_category","")=="Undervalued"].sort_values("value_score", ascending=False).head(num_stocks)
                    
                    if not top.empty:
                        msg = f"💎 Top {len(top)} Value Picks - {datetime.now().strftime('%d %b %Y, %I:%M %p')}\n\n"
                        for idx, r in top.iterrows():
                            msg += f"• {r['symbol']} ({r.get('sector','')})\n"
                            msg += f"  Price: ₹{r.get('close',0):.2f} | Value Score: {r.get('value_score',0):.0f}\n"
                            msg += f"  PE: {r.get('pe_ratio','N/A')} | ROE: {r.get('roe_pct','N/A')}% | PB: {r.get('pb_ratio','N/A')}\n\n"
                        
                        ok, resp = send_message(msg)
                        status = "sent" if ok else "failed"
                        
                        for idx, r in top.iterrows():
                            new = pd.DataFrame([[datetime.now().strftime('%Y-%m-%d %H:%M:%S'), r['symbol'], "value", msg, status]], 
                                             columns=["date","symbol","signal","message","status"])
                            alerts_df = pd.concat([alerts_df, new], ignore_index=True)
                        
                        save_user_file("alert_history.csv", alerts_df)
                        
                        if ok:
                            st.success(f"✅ Sent {len(top)} value alerts!")
                        else:
                            st.error(f"❌ Failed: {resp}")
                    else:
                        st.warning("No undervalued stocks found")
        
        elif alert_type == "High Volume Surge":
            min_vol_ratio = st.slider("Min Volume Ratio", 1.0, 5.0, 2.0, 0.1)
            
            if st.button("📱 Send Volume Surge Alerts", use_container_width=True):
                if not scan_df.empty and "volume_ratio" in scan_df.columns:
                    top = scan_df[pd.to_numeric(scan_df["volume_ratio"], errors="coerce") >= min_vol_ratio].nlargest(5, "volume_ratio")
                    
                    if not top.empty:
                        msg = f"📢 High Volume Surge - {datetime.now().strftime('%d %b %Y, %I:%M %p')}\n\n"
                        for idx, r in top.iterrows():
                            msg += f"• {r['symbol']} - Volume Ratio: {r.get('volume_ratio',0):.2f}x\n"
                            msg += f"  Price: ₹{r.get('close',0):.2f} | Change: {r.get('change_pct',0):.2f}%\n\n"
                        
                        ok, resp = send_message(msg)
                        status = "sent" if ok else "failed"