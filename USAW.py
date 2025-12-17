import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from tvDatafeed import TvDatafeed, Interval
from datetime import datetime, timedelta
import pytz
import time

# =====================================================
# STREAMLIT CONFIG
# =====================================================
st.set_page_config(page_title="USA Weather → NG Dashboard", layout="wide")

# =====================================================
# AUTO REFRESH (PURE STREAMLIT – NO MODULE)
# =====================================================
REFRESH_MINUTES = 15
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

if time.time() - st.session_state.last_refresh > REFRESH_MINUTES * 60:
    st.session_state.last_refresh = time.time()
    st.experimental_rerun()

# =====================================================
# TIME (IST)
# =====================================================
IST = pytz.timezone("Asia/Kolkata")
now = datetime.now(IST)
now_str = now.strftime("%d-%m-%Y %H:%M:%S IST")
current_hour = now.strftime("%Y-%m-%d %H")

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
HEADERS = {"User-Agent": "ng-weather-dashboard"}
HEATWAVE_TEMP = 35
COLDWAVE_TEMP = -5

tv = TvDatafeed()

# =====================================================
# 50 STATES (CAPITAL, LAT, LON, POP)
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
    return round((f - 32) * 5 / 9, 1)

def gas_score(t):
    if t <= COLDWAVE_TEMP: return 1.5
    if t >= HEATWAVE_TEMP: return 1.1
    return 1.0

def get_temp(lat, lon):
    p = requests.get(f"https://api.weather.gov/points/{lat},{lon}", headers=HEADERS)
    h = requests.get(p.json()["properties"]["forecastHourly"], headers=HEADERS)
    return f_to_c(h.json()["properties"]["periods"][0]["temperature"])

def get_ng_price(symbols, exchange):
    for sym in symbols:
        try:
            df = tv.get_hist(sym, exchange, Interval.in_daily, n_bars=30)
            if df is not None and not df.empty:
                df.index = pd.to_datetime(df.index)
                return df
        except:
            pass
    return pd.DataFrame()

# =====================================================
# WEATHER → NG INDEX
# =====================================================
rows, total_w, pop_sum = [], 0, 0

for state, (_, lat, lon, pop) in US_STATES.items():
    t = get_temp(lat, lon)
    s = gas_score(t)
    total_w += s * pop
    pop_sum += pop
    rows.append({"State": state, "Temp": t, "Score": s})

df_weather = pd.DataFrame(rows)
ng_index = int(min(100, (total_w / pop_sum) * 60))

bias = "STRONG BULLISH" if ng_index >= 70 else "BULLISH" if ng_index >= 55 else "NEUTRAL"

# =====================================================
# MCX PRICE DATA
# =====================================================
mcx_df = get_ng_price(["NATURALGAS1!", "NATURALGAS"], "MCX")

mcx_latest = f"{mcx_df['close'].iloc[-1]:.4f}" if not mcx_df.empty else "NA"

# =====================================================
# 📈 NG INDEX vs MCX PRICE (CORRELATION)
# =====================================================
st.subheader("📈 NG Index vs MCX Natural Gas Price")

if not mcx_df.empty:
    corr_df = mcx_df.tail(10).copy()
    corr_df["NG_Index"] = ng_index  # flat line reference

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=corr_df.index, y=corr_df["close"],
        name="MCX NG Price", yaxis="y1"
    ))
    fig.add_trace(go.Scatter(
        x=corr_df.index, y=corr_df["NG_Index"],
        name="NG Demand Index", yaxis="y2"
    ))

    fig.update_layout(
        yaxis=dict(title="MCX NG Price"),
        yaxis2=dict(title="NG Index", overlaying="y", side="right"),
        height=420
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("MCX price data not available")

# =====================================================
# 🔮 7-DAY NG PROBABILITY FORECAST (WEATHER BASED)
# =====================================================
st.subheader("🔮 7-Day NG Probability Forecast (Weather Driven)")

# Simple probability model
bull_prob = min(80, 40 + ng_index)
neutral_prob = max(10, 100 - bull_prob - 10)
bear_prob = 100 - bull_prob - neutral_prob

prob_df = pd.DataFrame({
    "Outcome →": ["Bullish", "Neutral", "Bearish"],
    "Probability (%)": [bull_prob, neutral_prob, bear_prob]
})

st.plotly_chart(
    px.bar(prob_df, x="Outcome →", y="Probability (%)",
           color="Outcome →", title="NG Price Bias Probability (7 Days)"),
    use_container_width=True
)

st.caption("📌 Derived from NOAA temperature stress → demand pressure → price bias")

# =====================================================
# INFO PANEL (RESTORED EXACT)
# =====================================================
st.info(f"""
**US Natural Gas Demand Index (Next 24h):** **{ng_index} / 100**

• Population-weighted weather impact  
• Cold regions increase NG heating demand  
• Heat adds power & LNG load  

**Futures Symbol Hint:**  
➡️ **Henry Hub Natural Gas (NG1!) / MCX NG (India)**  

**Bias:** {bias}
""")

# =====================================================
# TELEGRAM AUTO ALERT (HOURLY)
# =====================================================
if "last_alert_hour" not in st.session_state:
    st.session_state.last_alert_hour = ""

if st.session_state.last_alert_hour != current_hour:
    msg = f"""
🛢️ NG WEATHER ALERT

NG Index: {ng_index}/100
Bias: {bias}
MCX NG: {mcx_latest}
Time: {now_str}
"""
    send_telegram(msg)
    st.session_state.last_alert_hour = current_hour

# =====================================================
# FOOTER
# =====================================================
st.markdown("""
---
Made with ❤️  
**Gaurav Singh Yadav**  
8003994518
""")
