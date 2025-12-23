import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from tvDatafeed import TvDatafeed, Interval
import hashlib

# =====================================================
# LOGIN
# =====================================================
def hash_pwd(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

USERS = st.secrets["users"]

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔐 Login Required")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Login"):
        if u in USERS and hash_pwd(p) == USERS[u]:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Invalid credentials")
    st.stop()

# =====================================================
# CONFIG
# =====================================================
st.set_page_config(page_title="NG Demand vs Price Intelligence", layout="wide")
HEADERS = {"User-Agent": "ng-weather-dashboard"}

# =====================================================
# STATES (Population Weighted)
# =====================================================
US_STATES = {
    "Texas": ("Austin", 30.2672, -97.7431, 29.1),
    "California": ("Sacramento", 38.5816, -121.4944, 39.0),
    "Florida": ("Tallahassee", 30.4383, -84.2807, 22.6),
    "New York": ("Albany", 42.6526, -73.7562, 19.6),
    "Pennsylvania": ("Harrisburg", 40.2732, -76.8867, 12.9),
}

# =====================================================
# WEATHER FUNCTIONS
# =====================================================
def f_to_c(f):
    return (f - 32) * 5 / 9

def get_hourly_forecast(lat, lon):
    p = requests.get(f"https://api.weather.gov/points/{lat},{lon}", headers=HEADERS)
    if p.status_code != 200:
        return []
    url = p.json()["properties"]["forecastHourly"]
    h = requests.get(url, headers=HEADERS)
    if h.status_code != 200:
        return []
    return h.json()["properties"]["periods"][:48]

def calc_ng_demand(temp_c):
    hdd = max(18 - temp_c, 0)
    cdd = max(temp_c - 22, 0)
    return hdd * 1.3 + cdd * 0.7

# =====================================================
# FUTURE DEMAND (FORECAST)
# =====================================================
fut_rows = []

for state, (_, lat, lon, pop) in US_STATES.items():
    fc = get_hourly_forecast(lat, lon)
    for h in fc:
        fut_rows.append({
            "Time": pd.to_datetime(h["startTime"]),
            "Demand": calc_ng_demand(f_to_c(h["temperature"])),
            "Population": pop
        })

df_fut = pd.DataFrame(fut_rows)

df_fut["Weighted"] = df_fut["Demand"] * df_fut["Population"]

hourly_weighted = (
    df_fut.groupby("Time")["Weighted"]
    .sum()
    .reset_index()
)

# =====================================================
# BIAS CALCULATION (🔥 MISSING PART — FIXED)
# =====================================================
now = hourly_weighted["Time"].min()

prev_24 = hourly_weighted[
    (hourly_weighted["Time"] >= now) &
    (hourly_weighted["Time"] < now + pd.Timedelta(hours=24))
]

next_24 = hourly_weighted[
    (hourly_weighted["Time"] >= now + pd.Timedelta(hours=24)) &
    (hourly_weighted["Time"] < now + pd.Timedelta(hours=48))
]

prev_mean = prev_24["Weighted"].mean()
next_mean = next_24["Weighted"].mean()

pct_change = ((next_mean - prev_mean) / prev_mean) * 100

if pct_change > 5:
    bias = "🟢 Bullish Natural Gas"
elif pct_change > 2:
    bias = "🟡 Mild Bullish"
elif pct_change >= -2:
    bias = "⚪ Neutral"
elif pct_change >= -5:
    bias = "🟠 Mild Bearish"
else:
    bias = "🔴 Bearish Natural Gas"

# =====================================================
# PRICE DATA (DAILY, GAP-FREE)
# =====================================================
tv = TvDatafeed()
price = tv.get_hist(
    symbol="NATURALGAS",
    exchange="CAPITALCOM",
    interval=Interval.in_daily,
    n_bars=90
)

price = price.reset_index()[["datetime", "close"]]
price["Date"] = pd.to_datetime(price["datetime"]).dt.date
price.rename(columns={"close": "Price"}, inplace=True)

all_days = pd.date_range(price["Date"].min(), price["Date"].max(), freq="D")

price = (
    price.set_index("Date")
    .reindex(all_days)
    .rename_axis("Date")
    .reset_index()
)

price["Price"] = price["Price"].ffill()

# =====================================================
# CHART
# =====================================================
fig, ax1 = plt.subplots(figsize=(13, 6))

ax1.plot(hourly_weighted["Time"], hourly_weighted["Weighted"],
         label="NG Demand (Forecast)", linestyle="--", linewidth=2)

ax1.set_ylabel("Population Weighted Demand")
ax1.grid(alpha=0.3)

ax2 = ax1.twinx()
ax2.plot(price["Date"], price["Price"], color="black", linewidth=2, label="NG Price")
ax2.set_ylabel("NG Price")

fig.legend(loc="upper left")
st.pyplot(fig)

# =====================================================
# COLOR-WISE BIAS DISPLAY
# =====================================================
st.subheader("🎯 Natural Gas Bias Indicator")

bias_color_map = {
    "🟢 Bullish Natural Gas": ("Bullish", "🟢", "#d4f8d4"),
    "🟡 Mild Bullish": ("Mild Bullish", "🟡", "#fff3cd"),
    "⚪ Neutral": ("Neutral", "⚪", "#e2e3e5"),
    "🟠 Mild Bearish": ("Mild Bearish", "🟠", "#ffe5d0"),
    "🔴 Bearish Natural Gas": ("Bearish", "🔴", "#f8d7da"),
}

label, emoji, bg = bias_color_map[bias]

st.markdown(
    f"""
    <div style="padding:20px;border-radius:10px;
    background-color:{bg};text-align:center;
    font-size:22px;font-weight:bold;">
    {emoji} {label}
    </div>
    """,
    unsafe_allow_html=True
)

# =====================================================
# VERDICT
# =====================================================
if "Bullish" in label:
    verdict = "📈 Weather-driven demand supports **bullish Natural Gas** in the next 24–48 hours."
elif "Bearish" in label:
    verdict = "📉 Weather-driven demand weakens — **downside risk** for Natural Gas."
else:
    verdict = "⚖️ Weather-driven demand stable — Natural Gas likely **range-bound**."

st.success(verdict)

# =====================================================
# TABLE
# =====================================================
st.subheader("📊 Gap-Free Daily Price")
st.dataframe(price.tail(30), use_container_width=True)
