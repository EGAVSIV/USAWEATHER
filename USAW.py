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
# THEME
# =====================================================
st.markdown("""
<style>
.card {
    padding:18px;
    border-radius:12px;
    background:linear-gradient(135deg,#0f2027,#203a43,#2c5364);
    color:white;
    text-align:center;
}
.card h1 {font-size:30px;}
.card h3 {color:#00ffcc;}
</style>
""", unsafe_allow_html=True)

# =====================================================
# TELEGRAM SETUP
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

tv = TvDatafeed()

# =====================================================
# FUNCTIONS (OLD LOGIC PRESERVED)
# =====================================================
def f_to_c(f): return round((f - 32) * 5 / 9, 1)

def risk_flag(t):
    if t >= HEATWAVE_TEMP: return "🔥 Heatwave"
    if t <= COLDWAVE_TEMP: return "❄️ Coldwave"
    return "Normal"

def gas_score(t):
    if t <= COLDWAVE_TEMP: return 1.5
    if t >= HEATWAVE_TEMP: return 1.1
    return 1.0

def fetch_hourly(lat, lon):
    p = requests.get(f"https://api.weather.gov/points/{lat},{lon}", headers=HEADERS)
    h = requests.get(p.json()["properties"]["forecastHourly"], headers=HEADERS)
    return h.json()["properties"]["periods"][:48]

def fetch_futures(symbol, exchange):
    try:
        df = tv.get_hist(symbol, exchange, Interval.in_daily, n_bars=10)
        return df
    except:
        return pd.DataFrame()

# =====================================================
# LOAD STATE DATA (KEEP YOUR FULL 50 STATES DICT HERE)
# =====================================================
from states_data import US_STATES  # <-- OPTIONAL if large dict; else inline

# =====================================================
# DATA FETCH
# =====================================================
summary = []
weighted, pop_sum = 0, 0

for state, (city, lat, lon, pop) in US_STATES.items():
    h = fetch_hourly(lat, lon)
    t = f_to_c(h[0]["temperature"])
    score = gas_score(t)
    weighted += score * pop
    pop_sum += pop

    summary.append({
        "State": state,
        "Temp (°C)": t,
        "Risk": risk_flag(t),
        "Gas Demand Score": score
    })

df = pd.DataFrame(summary)
ng_index = int(min(100, (weighted / pop_sum) * 60))

# =====================================================
# MOBILE-FRIENDLY KPI CARDS
# =====================================================
st.markdown("### ⚡ Energy Snapshot")

c1, c2, c3 = st.columns(3)
c1.markdown(f"<div class='card'><h3>NG Index</h3><h1>{ng_index}/100</h1></div>", unsafe_allow_html=True)
c2.markdown(f"<div class='card'><h3>States</h3><h1>50</h1></div>", unsafe_allow_html=True)
c3.markdown(f"<div class='card'><h3>Bias</h3><h1>{'BULLISH' if ng_index>=55 else 'NEUTRAL'}</h1></div>", unsafe_allow_html=True)

# =====================================================
# 🔥 ANIMATED CHARTS (PLOTLY)
# =====================================================
st.markdown("### 🔥 Animated Energy Demand Charts")

fig1 = px.pie(df, names="Risk", title="Weather Risk Distribution",
              color_discrete_sequence=px.colors.sequential.Inferno)
st.plotly_chart(fig1, use_container_width=True)

fig2 = px.histogram(df, x="Gas Demand Score",
                    title="Gas Demand Intensity (Animated)",
                    animation_frame="Risk",
                    color="Risk")
st.plotly_chart(fig2, use_container_width=True)

# =====================================================
# 📊 MCX / NG FUTURES OVERLAY
# =====================================================
st.markdown("### 📊 Futures Confirmation")

mcx = fetch_futures("NATURALGAS1!", "MCX")
global_ng = fetch_futures("NATURALGAS", "CAPITALCOM")

col1, col2 = st.columns(2)
col1.write("🇮🇳 MCX Natural Gas", mcx.tail(3))
col2.write("🌍 Global Natural Gas", global_ng.tail(3))

# =====================================================
# 🧠 TRADER BIAS + TELEGRAM ALERT
# =====================================================
bias = "STRONG BULLISH" if ng_index >= 70 else "MILD BULLISH" if ng_index >= 55 else "NEUTRAL"

st.success(f"**Trader Bias:** {bias}")

if st.button("📩 Send Telegram Alert"):
    msg = f"""
🛢️ NG Weather Alert

NG Index: {ng_index}/100
Bias: {bias}

MCX NG Close: {mcx['close'].iloc[-1] if not mcx.empty else 'NA'}
"""
    send_telegram(msg)
    st.success("Telegram Alert Sent ✅")
