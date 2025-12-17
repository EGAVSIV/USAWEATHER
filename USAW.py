import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import matplotlib.pyplot as plt
import time, socket, ssl
from tvDatafeed import TvDatafeed, Interval

# =====================================================
# STREAMLIT CONFIG
# =====================================================
st.set_page_config(
    page_title="USA Weather → Natural Gas Demand Intelligence",
    layout="wide"
)

# =====================================================
# ENERGY THEME CSS
# =====================================================
st.markdown("""
<style>
.card {
    padding:18px;
    border-radius:14px;
    background:linear-gradient(135deg,#0f2027,#203a43,#2c5364);
    color:white;
    text-align:center;
    box-shadow:0 0 12px rgba(0,255,200,0.3);
}
.card h1 {font-size:34px;margin:0;}
.card h3 {color:#00ffcc;margin-bottom:6px;}
</style>
""", unsafe_allow_html=True)

# =====================================================
# TELEGRAM CONFIG
# =====================================================
BOT_TOKEN = '8268990134:AAGJJQrPzbi_3ROJWlDzF1sOl1RJLWP1t50'
CHAT_IDS = ['5332984891']

def send_telegram(msg):
    for cid in CHAT_IDS:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": cid, "text": msg})

# =====================================================
# CONSTANTS
# =====================================================
HEADERS = {"User-Agent": "weather-ng-dashboard"}
HEATWAVE_TEMP = 35
COLDWAVE_TEMP = -5

tv = TvDatafeed()  # no login

# =====================================================
# ALL 50 STATES (INLINE – NO EXTERNAL FILE)
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
def f_to_c(f): return round((f - 32) * 5 / 9, 1)

def gas_score(t):
    if t <= COLDWAVE_TEMP: return 1.5
    if t >= HEATWAVE_TEMP: return 1.1
    return 1.0

def risk_flag(t):
    if t >= HEATWAVE_TEMP: return "🔥 Heatwave"
    if t <= COLDWAVE_TEMP: return "❄️ Coldwave"
    return "Normal"

def fetch_hourly(lat, lon):
    p = requests.get(f"https://api.weather.gov/points/{lat},{lon}", headers=HEADERS)
    h = requests.get(p.json()["properties"]["forecastHourly"], headers=HEADERS)
    return h.json()["properties"]["periods"][:48]

# =====================================================
# DATA FETCH
# =====================================================
rows = []
weighted, pop_sum = 0, 0

for state, (city, lat, lon, pop) in US_STATES.items():
    h = fetch_hourly(lat, lon)
    t = f_to_c(h[0]["temperature"])
    s = gas_score(t)
    weighted += s * pop
    pop_sum += pop
    rows.append({"State": state, "Temp (°C)": t, "Risk": risk_flag(t), "Gas Score": s})

df = pd.DataFrame(rows)
ng_index = int(min(100, (weighted / pop_sum) * 60))

# =====================================================
# MOBILE KPI CARDS
# =====================================================
c1, c2, c3 = st.columns(3)
c1.markdown(f"<div class='card'><h3>NG Index</h3><h1>{ng_index}/100</h1></div>", unsafe_allow_html=True)
c2.markdown("<div class='card'><h3>States</h3><h1>50</h1></div>", unsafe_allow_html=True)
c3.markdown(f"<div class='card'><h3>Bias</h3><h1>{'BULLISH' if ng_index>=55 else 'NEUTRAL'}</h1></div>", unsafe_allow_html=True)

# =====================================================
# ANIMATED CHARTS
# =====================================================
st.markdown("### 🔥 Animated Energy Charts")
st.plotly_chart(px.pie(df, names="Risk", title="Weather Risk Distribution"), use_container_width=True)
st.plotly_chart(px.histogram(df, x="Gas Score", color="Risk", title="Gas Demand Intensity"), use_container_width=True)

# =====================================================
# TELEGRAM ALERT
# =====================================================
if st.button("📩 Send Telegram Alert"):
    send_telegram(f"🛢️ NG Index: {ng_index}/100 | Bias: {'Bullish' if ng_index>=55 else 'Neutral'}")
    st.success("Telegram alert sent ✅")
