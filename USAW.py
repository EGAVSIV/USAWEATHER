import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from tvDatafeed import TvDatafeed, Interval
from datetime import datetime
import pytz
from streamlit_autorefresh import st_autorefresh

# ================= AUTO REFRESH =================
st_autorefresh(interval=15 * 60 * 1000, key="ng_refresh")  # 15 min

# ================= STREAMLIT CONFIG =================
st.set_page_config(page_title="USA Weather → NG Dashboard", layout="wide")

# ================= TIME =================
IST = pytz.timezone("Asia/Kolkata")
now = datetime.now(IST)
now_str = now.strftime("%d-%m-%Y %H:%M IST")
current_hour = now.strftime("%Y-%m-%d %H")

# ================= TELEGRAM =================
BOT_TOKEN = '8268990134:AAGJJQrPzbi_3ROJWlDzF1sOl1RJLWP1t50'
CHAT_IDS = ['5332984891']

def send_telegram(msg):
    for cid in CHAT_IDS:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": cid, "text": msg})

# ================= CONSTANTS =================
HEADERS = {"User-Agent": "ng-dashboard"}
HEATWAVE_TEMP = 35
COLDWAVE_TEMP = -5
tv = TvDatafeed()

# ================= STATES (50) =================
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
    # remaining smaller states combined weight
    "Alabama": ("Montgomery", 32.36, -86.30, 5.1),
    "Arizona": ("Phoenix", 33.44, -112.07, 7.4),
    "New Jersey": ("Trenton", 40.22, -74.76, 9.3),
    "Virginia": ("Richmond", 37.54, -77.43, 8.7),
    "Washington": ("Olympia", 47.03, -122.90, 7.8),
    "Tennessee": ("Nashville", 36.16, -86.78, 7.0),
    "Massachusetts": ("Boston", 42.36, -71.05, 7.0),
    "Indiana": ("Indianapolis", 39.76, -86.15, 6.8),
    "Missouri": ("Jefferson City", 38.57, -92.17, 6.2),
    "Maryland": ("Annapolis", 38.97, -76.49, 6.2),
    "Wisconsin": ("Madison", 43.07, -89.40, 5.9),
    "Colorado": ("Denver", 39.73, -104.99, 5.8),
    "Minnesota": ("Saint Paul", 44.95, -93.09, 5.7),
    "South Carolina": ("Columbia", 34.00, -81.03, 5.3),
    "Alaska": ("Juneau", 58.30, -134.41, 0.7),
}

# ================= FUNCTIONS =================
def f_to_c(f): return (f - 32) * 5 / 9

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
            df = tv.get_hist(sym, exchange, Interval.in_daily, n_bars=1)
            if df is not None and not df.empty:
                return f"{df['close'].iloc[-1]:.4f}"
        except:
            pass
    return "NA"

# ================= DATA BUILD =================
rows, total_w, pop_sum = [], 0, 0

for s, (_, lat, lon, pop) in US_STATES.items():
    t = round(get_temp(lat, lon), 1)
    score = gas_score(t)
    total_w += score * pop
    pop_sum += pop
    rows.append({"State": s, "Temp °C": t, "Gas Score": score, "Weighted": score * pop})

df = pd.DataFrame(rows)
ng_index = int(min(100, (total_w / pop_sum) * 60))

bias = "STRONG BULLISH" if ng_index >= 70 else "BULLISH" if ng_index >= 55 else "NEUTRAL"

# ================= PRICES =================
mcx_price = get_ng_price(["NATURALGAS1!", "NATURALGAS"], "MCX")
global_price = get_ng_price(["NATURALGAS"], "CAPITALCOM")

# ================= DASHBOARD =================
st.title("🇺🇸 USA Weather → Natural Gas Demand Intelligence")
st.caption(f"🕒 Data as of: {now_str}")

st.metric("NG Index", f"{ng_index}/100", bias)
st.metric("MCX NG", mcx_price)
st.metric("Global NG", global_price)

st.dataframe(df.sort_values("Weighted", ascending=False), use_container_width=True)

st.plotly_chart(px.pie(df, names="Gas Score", title="Gas Demand Distribution"), use_container_width=True)

# ================= INFO PANEL (RESTORED) =================
st.info(f"""
**US Natural Gas Demand Index (Next 24h):** **{ng_index} / 100**

• Population-weighted weather impact  
• Cold regions increase NG heating demand  
• Heat adds power & LNG load  

**Futures Symbol Hint:**  
➡️ **Henry Hub Natural Gas (NG1!) / MCX NG (India)**  

**Bias:** {bias}
""")

# ================= TELEGRAM AUTO ALERT =================
if "last_alert_hour" not in st.session_state:
    st.session_state.last_alert_hour = ""

if st.session_state.last_alert_hour != current_hour:
    msg = f"""
🛢️ NG Weather Alert

NG Index: {ng_index}/100
Bias: {bias}
MCX NG: {mcx_price}
Global NG: {global_price}
Time: {now_str}
"""
    send_telegram(msg)
    st.session_state.last_alert_hour = current_hour

# ================= FOOTER =================
st.markdown("""
---
Made with ❤️  
**Gaurav Singh Yadav**  
8003994518
""")
