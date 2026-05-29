import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = BASE_DIR if os.path.basename(BASE_DIR) != "pages" else os.path.dirname(BASE_DIR)
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import feedparser

st.set_page_config(page_title="Market News", page_icon="📰", layout="wide")

st.title("📰 Live Market News & Updates")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📈 Market Headlines", "🔥 Trending Stocks", "📊 NSE News", "🌍 Global Markets"])

@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_moneycontrol_news():
    """Fetch top news from MoneyControl RSS"""
    try:
        feed = feedparser.parse("https://www.moneycontrol.com/rss/latestnews.xml")
        news = []
        for entry in feed.entries[:15]:
            news.append({
                "title": entry.title,
                "link": entry.link,
                "published": entry.get("published", ""),
                "summary": entry.get("summary", "")
            })
        return pd.DataFrame(news)
    except Exception as e:
        st.error(f"Error fetching MoneyControl news: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def fetch_economic_times_news():
    """Fetch Economic Times Market News RSS"""
    try:
        feed = feedparser.parse("https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms")
        news = []
        for entry in feed.entries[:15]:
            news.append({
                "title": entry.title,
                "link": entry.link,
                "published": entry.get("published", ""),
                "summary": entry.get("summary", "")
            })
        return pd.DataFrame(news)
    except Exception as e:
        st.error(f"Error fetching ET news: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=600)
def fetch_nse_announcements():
    """Fetch NSE Corporate Announcements"""
    try:
        # Mock data - Replace with actual NSE API when available
        announcements = [
            {
                "company": "TCS",
                "subject": "Board Meeting Announcement",
                "date": datetime.now().strftime("%Y-%m-%d"),
                "description": "Board meeting scheduled for Q4 results"
            },
            {
                "company": "RELIANCE",
                "subject": "Dividend Declaration",
                "date": datetime.now().strftime("%Y-%m-%d"),
                "description": "Interim dividend of ₹8 per share declared"
            }
        ]
        return pd.DataFrame(announcements)
    except Exception as e:
        st.error(f"Error fetching NSE announcements: {e}")
        return pd.DataFrame()

with tab1:
    st.subheader("📈 Latest Market Headlines")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 💰 MoneyControl")
        mc_news = fetch_moneycontrol_news()
        
        if not mc_news.empty:
            for idx, row in mc_news.iterrows():
                with st.expander(f"📌 {row['title'][:100]}..."):
                    st.markdown(f"**Published:** {row.get('published', 'N/A')}")
                    if row.get('summary'):
                        st.write(row['summary'][:300] + "...")
                    st.markdown(f"[Read More]({row['link']})")
        else:
            st.info("Unable to fetch news. Try again later.")
    
    with col2:
        st.markdown("### 📰 Economic Times")
        et_news = fetch_economic_times_news()
        
        if not et_news.empty:
            for idx, row in et_news.iterrows():
                with st.expander(f"📌 {row['title'][:100]}..."):
                    st.markdown(f"**Published:** {row.get('published', 'N/A')}")
                    if row.get('summary'):
                        st.write(row['summary'][:300] + "...")
                    st.markdown(f"[Read More]({row['link']})")
        else:
            st.info("Unable to fetch news. Try again later.")
    
    # Refresh button
    if st.button("🔄 Refresh News", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

with tab2:
    st.subheader("🔥 Trending Stocks in News")
    
    # Search news 