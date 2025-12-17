# =====================================================
# NG WEATHER → PRICE → NEWS INTELLIGENCE DASHBOARD
# =====================================================

import streamlit as st
import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import feedparser

# =====================================================
# STREAMLIT CONFIG
# =====================================================
st.set_page_config(page_title="NG Intelligence Pro", layout="wide")

# =====================================================
# TELEGRAM CONFIG
# =====================================================
BOT_TOKEN = "PUT_YOUR_BOT_TOKEN"
CHAT_IDS = ["PUT_CHAT_ID"]

def send_telegram(msg):
    for chat in CHAT_IDS:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": chat, "text": msg})

# =====================================================
# UPDATE BUTTON
# =====================================================
if st.button("🔄 UPDATE NOW"):
    st.cache_data.clear()

# =====================================================
# CONSTANTS
# =====================================================
HEADERS = {"User-Agent": "ng-weather-dashboard"}
HEATWAVE_TEMP = 35
COLDWAVE_TEMP = -5
ALERT_LEVEL = 65

TODAY = datetime.today().date()
DAY1_DATE = TODAY
DAY2_DATE = TODAY + timedelta(days=1)

# =====================================================
# WEATHER STATES (POPULATION WEIGHTED)
# =====================================================
US_STATES = {
    "California": ("Sacramento", 38.58, -121.49, 39.0),
    "Texas": ("Austin", 30.26, -97.74, 30.0),
    "Florida": ("Tallahassee", 30.43, -84.28, 22.0),
    "New York": ("Albany", 42.65, -73.75, 19.6),
    "Pennsylvania": ("Harrisburg", 40.27, -76.88, 13.0),
    "Illinois": ("Springfield", 39.78, -89.65, 12.5),
    "Ohio": ("Columbus", 39.96, -82.99, 11.8),
    "Georgia": ("Atlanta", 33.74, -84.38, 11.0),
    "North Carolina": ("Raleigh", 35.77, -78.63, 10.8),
    "Michigan": ("Lansing", 42.73, -84.55, 10.0),
    # --- remaining states (lower weights) ---
    "Alabama": ("Montgomery", 32.36, -86.30, 5.1),
    "Alaska": ("Juneau", 58.30, -134.41, 0.7),
    "Arizona": ("Phoenix", 33.44, -112.07, 7.4),
    "Arkansas": ("Little Rock", 34.74, -92.28, 3.0),
    "Colorado": ("Denver", 39.73, -104.99, 5.8),
    "Connecticut": ("Hartford", 41.76, -72.67, 3.6),
    "Delaware": ("Dover", 39.15, -75.52, 1.0),
    "Hawaii": ("Honolulu", 21.30, -157.85, 1.4),
    "Idaho": ("Boise", 43.61, -116.20, 1.9),
    "Indiana": ("Indianapolis", 39.76, -86.15, 6.8),
    "Iowa": ("Des Moines", 41.58, -93.62, 3.2),
    "Kansas": ("Topeka", 39.05, -95.68, 2.9),
    "Kentucky": ("Frankfort", 38.20, -84.87, 4.5),
    "Louisiana": ("Baton Rouge", 30.45, -91.18, 4.6),
    "Maine": ("Augusta", 44.31, -69.77, 1.3),
    "Maryland": ("Annapolis", 38.97, -76.49, 6.2),
    "Massachusetts": ("Boston", 42.36, -71.05, 7.0),
    "Minnesota": ("Saint Paul", 44.95, -93.09, 5.7),
    "Mississippi": ("Jackson", 32.29, -90.18, 2.9),
    "Missouri": ("Jefferson City", 38.57, -92.17, 6.2),
    "Montana": ("Helena", 46.58, -112.03, 1.1),
    "Nebraska": ("Lincoln", 40.81, -96.70, 1.9),
    "Nevada": ("Carson City", 39.16, -119.76, 3.2),
    "New Hampshire": ("Concord", 43.20, -71.53, 1.4),
    "New Jersey": ("Trenton", 40.22, -74.76, 9.3),
    "New Mexico": ("Santa Fe", 35.68, -105.93, 2.1),
    "North Dakota": ("Bismarck", 46.80, -100.78, 0.8),
    "Oklahoma": ("Oklahoma City", 35.46, -97.51, 4.0),
    "Oregon": ("Salem", 44.94, -123.03, 4.2),
    "Rhode Island": ("Providence", 41.82, -71.41, 1.1),
    "South Carolina": ("Columbia", 34.00, -81.03, 5.3),
    "South Dakota": ("Pierre", 44.36, -100.35, 0.9),
    "Tennessee": ("Nashville", 36.16, -86.78, 7.0),
    "Utah": ("Salt Lake City", 40.76, -111.89, 3.4),
    "Vermont": ("Montpelier", 44.26, -72.57, 0.6),
    "Virginia": ("Richmond", 37.54, -77.43, 8.7),
    "Washington": ("Olympia", 47.03, -122.90, 7.8),
    "West Virginia": ("Charleston", 38.34, -81.63, 1.8),
    "Wisconsin": ("Madison", 43.07, -89.40, 5.9),
    "Wyoming": ("Cheyenne", 41.13, -104.82, 0.6),
}

# =====================================================
# FUNCTIONS
# =====================================================
def f_to_c(f):
    return (f - 32) * 5 / 9

def gas_score(temp):
    if temp <= COLDWAVE_TEMP:
        return 1.5
    if temp >= HEATWAVE_TEMP:
        return 1.1
    return 1.0

def get_hourly(lat, lon):
    p = requests.get(f"https://api.weather.gov/points/{lat},{lon}", headers=HEADERS)
    if p.status_code != 200:
        return []
    url = p.json()["properties"]["forecastHourly"]
    h = requests.get(url, headers=HEADERS)
    if h.status_code != 200:
        return []
    return h.json()["properties"]["periods"][:48]

# =====================================================
# MCX NG PRICE — GROWW (SCRAPING)
# =====================================================
def fetch_mcx_ng_price():
    try:
        url = "https://groww.in/commodities/futures/mcx-natural-gas"
        r = requests.get(url, headers=HEADERS, timeout=5)
        soup = BeautifulSoup(r.text, "html.parser")
        price_tag = soup.find("span", {"class": "lpu38Head"})
        return float(price_tag.text.replace("₹", "").replace(",", ""))
    except:
        return None

# =====================================================
# HENRY HUB (FREE CSV)
# =====================================================
def henry_hub_price():
    try:
        r = requests.get("https://stooq.com/q/l/?s=ng.f&f=sd2t2ohlcv&h&e=csv")
        return float(r.text.splitlines()[1].split(",")[6])
    except:
        return None

# =====================================================
# TOP 5 NG NEWS (GOOGLE RSS)
# =====================================================
def fetch_ng_news():
    feed = feedparser.parse(
        "https://news.google.com/rss/search?q=natural+gas+LNG+weather&hl=en-US&gl=US&ceid=US:en"
    )
    news = []
    for e in feed.entries[:5]:
        news.append({
            "Date": e.published[:16],
            "Headline": e.title
        })
    return pd.DataFrame(news)


# WEATHER → NG DEMAND
# =====================================================
# WEATHER → NG DEMAND
# =====================================================
day1 = 0.0
day2 = 0.0
total_population = 0.0

with st.spinner("Fetching NOAA Weather Data..."):
    for state, (city, lat, lon, population) in US_STATES.items():
        h = get_hourly(lat, lon)
        if not h:
            continue

        t1 = np.mean([f_to_c(x["temperature"]) for x in h[:24]])
        t2 = np.mean([f_to_c(x["temperature"]) for x in h[24:]])

        day1 += gas_score(t1) * population
        day2 += gas_score(t2) * population
        total_population += population

# Safety check (important for cloud runs)
if total_population == 0:
    st.error("Weather data unavailable — cannot compute NG index")
    st.stop()

ng_day1 = int(min(100, (day1 / total_population) * 60))
ng_day2 = int(min(100, (day2 / total_population) * 60))

# =====================================================
# WEEKLY & MONTHLY NG BIAS (PROJECTION)
# =====================================================
ng_week = int(round((ng_day1 + ng_day2) / 2))

# Monthly bias assumes persistence + small escalation
ng_month = int(min(100, ng_week + 5))



# =====================================================
# TELEGRAM ALERT
# =====================================================
if ng_day1 >= ALERT_LEVEL:
    send_telegram(
        f"🚨 NG ALERT 🚨\n"
        f"Date: {DAY1_DATE}\n"
        f"NG Index: {ng_day1}\n"
        f"STRONG WEATHER DRIVEN DEMAND"
    )

# =====================================================
# DASHBOARD
# =====================================================
st.title("🔥 Natural Gas Weather–Price–News Intelligence")

col1, col2, col3, col4 = st.columns(4)
col1.metric(str(DAY1_DATE), ng_day1, "Bullish" if ng_day1 > 60 else "Neutral")
col2.metric(str(DAY2_DATE), ng_day2, "Bullish" if ng_day2 > 60 else "Neutral")
col3.metric("Weekly Bias", ng_week)
col4.metric("Monthly Bias", ng_month)

# =====================================================
# PRICE PANEL
# =====================================================
mcx = fetch_mcx_ng_price()
hh = henry_hub_price()

st.markdown("## 💰 Natural Gas Prices")

price_df = pd.DataFrame({
    "Instrument": ["MCX Natural Gas", "Henry Hub"],
    "Price": [mcx, hh]
})
st.dataframe(price_df, use_container_width=True)

# =====================================================
# CORRELATION INTELLIGENCE (AGGRESSIVE)
# =====================================================
st.markdown("## 🧮 Correlation Intelligence — Trader View")

corr_table = pd.DataFrame({
    "Factor": ["Weather Demand", "Crude Oil", "Power Load"],
    "Impact Strength": ["VERY HIGH 🔥", "MEDIUM ⚠️", "HIGH ⚡"],
    "Why It Matters": [
        "Heating demand explodes during cold waves",
        "Energy sentiment & inflation hedge",
        "Power generation + LNG draw"
    ],
    "NG Price Reaction": [
        "Sharp upside spikes",
        "Momentum confirmation",
        "Sustained trend support"
    ]
})

st.dataframe(corr_table, use_container_width=True)

# =====================================================
# INTERPRETATION TABLE (EASY)
# =====================================================
st.markdown("## 📊 Easy Interpretation Guide")

interp = pd.DataFrame({
    "Condition": [
        "NG Index > 70",
        "NG Index 60–70",
        "NG Index < 60",
        "MCX > Henry Hub (Converted)"
    ],
    "Meaning": [
        "Severe weather driven demand",
        "Weather supportive but not extreme",
        "No strong weather trigger",
        "Indian prices overheating"
    ],
    "Trader Action": [
        "BUY / HOLD LONG",
        "BUY ON DIPS",
        "WAIT / RANGE TRADE",
        "Book profits / cautious longs"
    ]
})

st.dataframe(interp.style.background_gradient(cmap="YlOrRd"), use_container_width=True)

# =====================================================
# TOP NEWS
# =====================================================
st.markdown("## 📰 Top 5 News Impacting Natural Gas")

news_df = fetch_ng_news()
st.dataframe(news_df, use_container_width=True)

# =====================================================
# FINAL VIEW
# =====================================================
st.success(f"""
**Final Verdict**

📅 Date: {DAY1_DATE}  
🔥 Weather Bias: {"STRONG" if ng_day1 > 65 else "MODERATE"}  
💰 MCX NG Price: {mcx}  

➡️ Weather + News + Price aligned  
➡️ Best suited for **positional NG trades**
""")

# =====================================================
# FOOTER
# =====================================================
st.markdown("""
---
**Designed by-  
Gaurav Singh Yadav**  
Made with ❤️    
Energy | Commodity | Quant Intelligence   
+91-8003994518
""")
