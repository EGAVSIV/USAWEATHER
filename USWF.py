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
