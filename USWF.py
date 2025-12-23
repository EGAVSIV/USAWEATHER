import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from tvDatafeed import TvDatafeed, Interval
import hashlib
import numpy as np

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
st.set_page_config(
    page_title="Natural Gas Weather Intelligence",
    layout="wide",
    page_icon="🔥"
)

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
    r = requests.get(f"https://api.weather.gov/points/{lat},{lon}", headers=HEADERS)
    if r.status_code != 200:
        return []
    hourly_url = r.json()["properties"]["forecastHourly"]
    h = requests.get(hourly_url, headers=HEADERS)
    if h.status_code != 200:
        return []
    return h.json()["properties"]["periods"][:48]

def calc_ng_demand(temp_c):
    hdd = max(18 - temp_c, 0)
    cdd = max(temp_c - 22, 0)
    return hdd * 1.3 + cdd * 0.7

# =====================================================
# FORECAST DEMAND (RAW)
# =====================================================
rows = []

for state, (_, lat, lon, pop) in US_STATES.items():
    forecast = get_hourly_forecast(lat, lon)
    for h in forecast:
        rows.append({
            "DateTime": h.get("startTime"),
            "Demand": calc_ng_demand(f_to_c(h["temperature"])) * pop
        })

df = pd.DataFrame(rows)

# =====================================================
# 🔥 BULLETPROOF DATE HANDLING (FIX)
# =====================================================
df["Date"] = pd.to_datetime(df["DateTime"], errors="coerce").dt.date
df = df.dropna(subset=["Date"])

# =====================================================
# DAILY DEMAND (SAFE)
# =====================================================
df_daily = (
    df.groupby("Date", as_index=False)["Demand"]
      .sum()
)

# =====================================================
# BIAS CALCULATION
# =====================================================
prev = df_daily.iloc[0]["Demand"]
next_ = df_daily.iloc[1]["Demand"]
pct = ((next_ - prev) / prev) * 100

if pct > 5:
    bias = "Bullish"
    color = "#2ecc71"
elif pct > 2:
    bias = "Mild Bullish"
    color = "#f1c40f"
elif pct >= -2:
    bias = "Neutral"
    color = "#95a5a6"
elif pct >= -5:
    bias = "Mild Bearish"
    color = "#e67e22"
else:
    bias = "Bearish"
    color = "#e74c3c"

# =====================================================
# PRICE DATA (DAILY – GAP FREE)
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
# MAIN CHART (WITH FUTURE GAP)
# =====================================================
st.subheader("📈 Natural Gas Demand vs Price")

gap_days = 2
last_hist_date = price["Date"].max()

future_dates = [
    last_hist_date + timedelta(days=gap_days + i)
    for i in range(len(df_daily))
]

fig, ax1 = plt.subplots(figsize=(14, 6))

ax1.plot(
    future_dates,
    df_daily["Demand"],
    linestyle="--",
    linewidth=2,
    label="NG Demand (Forecast)"
)

ax1.set_ylabel("Population Weighted Demand")
ax1.grid(alpha=0.3)

ax2 = ax1.twinx()
ax2.plot(price["Date"], price["Price"], color="black", linewidth=2, label="NG Price")
ax2.set_ylabel("NG Price")

fig.legend(loc="upper left")
plt.xticks(rotation=45)

st.pyplot(fig)

# =====================================================
# BIAS DISPLAY
# =====================================================
st.subheader("🎯 Natural Gas Bias")

st.markdown(
    f"""
    <div style="
        background:{color};
        padding:18px;
        border-radius:12px;
        color:black;
        font-size:26px;
        font-weight:900;
        text-align:center;
        box-shadow:0px 4px 12px rgba(0,0,0,0.3);
    ">
        {bias}
    </div>
    """,
    unsafe_allow_html=True
)

st.success(
    f"Weather-driven demand supports **{bias.upper()} Natural Gas** for the next 24–48 hours."
)

# =====================================================
# DONUT CHARTS
# =====================================================
st.subheader("📊 Demand & Bias Snapshot")

c1, c2 = st.columns(2)

with c1:
    fig1, ax = plt.subplots()
    ax.pie(
        [abs(pct), 100 - abs(pct)],
        labels=["Bias Strength", "Remaining"],
        colors=[color, "#ecf0f1"],
        startangle=90,
        wedgeprops=dict(width=0.4)
    )
    ax.set_title("Bias Strength")
    st.pyplot(fig1)

with c2:
    fig2, ax = plt.subplots()
    ax.pie(
        df_daily["Demand"],
        labels=df_daily["Date"],
        autopct="%1.1f%%",
        startangle=90
    )
    ax.set_title("Forecast Demand Distribution")
    st.pyplot(fig2)

# =====================================================
# TABLE
# =====================================================
st.subheader("📋 Gap-Free Daily Price")
st.dataframe(price.tail(30), use_container_width=True)
