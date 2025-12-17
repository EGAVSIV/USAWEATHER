# =====================================================
# NG WEATHER → PRICE → NEWS INTELLIGENCE DASHBOARD
# CLEAN, ORDER-SAFE, PRODUCTION VERSION
# =====================================================

import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import feedparser
from tvDatafeed import TvDatafeed, Interval
import socket, ssl, time

# =====================================================
# STREAMLIT CONFIG
# =====================================================
st.set_page_config(page_title="NG Intelligence Pro", layout="wide")

# =====================================================
# TELEGRAM CONFIG
# =====================================================
BOT_TOKEN = "8268990134:AAGJJQrPzbi_3ROJWlDzF1sOl1RJLWP1t50"
CHAT_IDS = ["5332984891"]

def send_telegram(message: str):
    for chat_id in CHAT_IDS:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": chat_id, "text": message})

# =====================================================
# TV DATAFEED LOGIN (INTERNATIONAL NG)
# =====================================================
tv = TvDatafeed("EGAVSIV", "Eric$1234")

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
# US STATES (POPULATION WEIGHTED)
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
}

# =====================================================
# FUNCTIONS
# =====================================================
def f_to_c(f):
    return (f - 32) * 5 / 9

def gas_score(temp_c):
    if temp_c <= COLDWAVE_TEMP:
        return 1.5
    if temp_c >= HEATWAVE_TEMP:
        return 1.1
    return 1.0

def get_hourly(lat, lon):
    try:
        p = requests.get(f"https://api.weather.gov/points/{lat},{lon}", headers=HEADERS)
        if p.status_code != 200:
            return []
        url = p.json()["properties"]["forecastHourly"]
        h = requests.get(url, headers=HEADERS)
        if h.status_code != 200:
            return []
        return h.json()["properties"]["periods"][:48]
    except:
        return []

# =====================================================
# MCX NATURAL GAS – ALL FUTURES (DHAN)
# =====================================================
def fetch_mcx_ng_futures():
    try:
        url = "https://dhan.co/commodity/natural-gas-futures-summary/"
        r = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")

        table = soup.find("table")
        rows = table.find_all("tr")[1:]

        data = []
        for row in rows:
            cols = [c.text.strip() for c in row.find_all("td")]
            if len(cols) >= 8:
                data.append({
                    "Contract": cols[0],
                    "Days to Expiry": cols[1],
                    "LTP": cols[2],
                    "Change": cols[3],
                    "Change %": cols[4],
                    "Volume": cols[5],
                    "Open Interest": cols[6],
                    "OI Change %": cols[7],
                })

        return pd.DataFrame(data)
    except:
        return pd.DataFrame()

# =====================================================
# INTERNATIONAL NATURAL GAS (CAPITAL.COM)
# =====================================================
def fetch_international_ng():
    try:
        df = tv.get_hist(
            symbol="NATURALGAS",
            exchange="CAPITALCOM",
            interval=Interval.in_daily,
            n_bars=1
        )
        if df is not None and not df.empty:
            return float(df["close"].iloc[-1])
    except (socket.timeout, ssl.SSLError):
        return None

# =====================================================
# NEWS
# =====================================================
def fetch_ng_news():
    feed = feedparser.parse(
        "https://news.google.com/rss/search?q=natural+gas+LNG+weather&hl=en-US&gl=US&ceid=US:en"
    )
    return pd.DataFrame(
        [{"Date": e.published[:16], "Headline": e.title} for e in feed.entries[:5]]
    )

# =====================================================
# WEATHER → NG DEMAND
# =====================================================
day1_weight, day2_weight, total_population = 0.0, 0.0, 0.0

with st.spinner("Fetching NOAA Weather Data..."):
    for _, (city, lat, lon, population) in US_STATES.items():
        hourly = get_hourly(lat, lon)
        if not hourly:
            continue

        t1 = np.mean([f_to_c(h["temperature"]) for h in hourly[:24]])
        t2 = np.mean([f_to_c(h["temperature"]) for h in hourly[24:]])

        day1_weight += gas_score(t1) * population
        day2_weight += gas_score(t2) * population
        total_population += population

if total_population == 0:
    st.error("Weather data unavailable")
    st.stop()

# =====================================================
# NG INDEX
# =====================================================
ng_day1 = int(min(100, (day1_weight / total_population) * 60))
ng_day2 = int(min(100, (day2_weight / total_population) * 60))

# =====================================================
# MANUAL UPDATE BUTTON (ONLY TELEGRAM TRIGGER)
# =====================================================
if st.button("🔄 UPDATE NOW"):
    if ng_day1 >= ALERT_LEVEL:
        send_telegram(
            f"🔔 NG ALERT\n"
            f"Date: {DAY1_DATE}\n"
            f"NG Index: {ng_day1}\n"
            f"Weather Driven Demand"
        )
        st.success("Telegram alert sent ✔")
    else:
        st.info("NG Index below alert level — no alert sent")

# =====================================================
# WEEKLY / MONTHLY BIAS
# =====================================================
ng_week = int(round((ng_day1 + ng_day2) / 2))
ng_month = min(100, ng_week + 5)

# =====================================================
# DASHBOARD
# =====================================================
st.title("🔥 Natural Gas Weather–Price–News Intelligence")

c1, c2, c3, c4 = st.columns(4)
c1.metric(str(DAY1_DATE), ng_day1, "Bullish" if ng_day1 >= 60 else "Neutral")
c2.metric(str(DAY2_DATE), ng_day2, "Bullish" if ng_day2 >= 60 else "Neutral")
c3.metric("Weekly Bias", ng_week)
c4.metric("Monthly Bias", ng_month)

# =====================================================
# PRICE TABLES
# =====================================================
st.subheader("💰 Natural Gas Prices")

mcx_df = fetch_mcx_ng_futures()
if not mcx_df.empty:
    st.markdown("### 🇮🇳 MCX Natural Gas – Futures Curve")
    st.dataframe(mcx_df, use_container_width=True)
else:
    st.warning("MCX futures data not available")

intl_price = fetch_international_ng()
st.markdown("### 🌍 International Natural Gas (Capital.com)")
st.dataframe(pd.DataFrame({
    "Market": ["International NG"],
    "Close Price": [intl_price]
}), use_container_width=True)

# =====================================================
# NEWS
# =====================================================
st.subheader("📰 Top 5 News Impacting Natural Gas")
st.dataframe(fetch_ng_news(), use_container_width=True)

# =====================================================
# FINAL VERDICT
# =====================================================
st.success(f"""
**Final Verdict**

📅 Date: {DAY1_DATE}  
🔥 NG Index: {ng_day1}  
➡️ Weather-driven bias confirmed  
➡️ Best suited for positional trades
""")

# =====================================================
# FOOTER
# =====================================================
st.markdown("""
---
**Designed by:-  
Gaurav Singh Yadav**  
Energy | Commodity | Quant Intelligence  
📱 +91-8003994518
""")
