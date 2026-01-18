import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from tvDatafeed import TvDatafeed, Interval
import hashlib
import numpy as np
import time

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
    page_title="4️⃣ Natural Gas Weather Intelligence",
    layout="wide",
    page_icon="🔥"
)
col_logo, col_ticker = st.columns([0.22, 0.78]) 
with col_logo: 
    st.image("Assets/sgy1.png", width=220)

# =====================================================
# 🔄 MANUAL + AUTO REFRESH (STABLE VERSION)
# =====================================================


c1, c2, c3 = st.columns([1.2, 1.8, 6])

with c1:
    if st.button("🔄 Refresh Now"):
        st.session_state["last_refresh"] = time.time()
        st.cache_data.clear()
        st.rerun()

with c2:
    auto_refresh = st.toggle("⏱ Auto Refresh (5 min)", value=False)

with c3:
    st.caption("Manual refresh forces fresh NOAA weather + NG demand recalculation")


# =====================================================
# AUTO REFRESH ENGINE (SAFE & TIMED)
# =====================================================
# =====================================================
# AUTO REFRESH TIMER (NO LIBRARY, NO LOOP)
# =====================================================
if auto_refresh:
    now = time.time()
    last = st.session_state.get("last_refresh", 0)

    if now - last >= 5 * 60:  # 30 minutes
        st.session_state["last_refresh"] = now
        st.cache_data.clear()
        st.rerun()



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
# 🔥 ABSOLUTE SAFE DATE CONVERSION (NO .dt ANYWHERE)
# =====================================================
df["Date"] = df["DateTime"].apply(
    lambda x: pd.to_datetime(x, errors="coerce").date()
    if pd.notna(x) else None
)

df = df.dropna(subset=["Date"])

# =====================================================
# DAILY DEMAND
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
price.rename(columns={"datetime": "Date", "close": "Price"}, inplace=True)

price["Date"] = price["Date"].apply(
    lambda x: pd.to_datetime(x, errors="coerce").date()
)

all_days = pd.date_range(min(price["Date"]), max(price["Date"]), freq="D")

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
# SAFE BIAS STRENGTH (0–100 ONLY)
# =====================================================
bias_strength = min(abs(pct), 100)
remaining_strength = 100 - bias_strength

# =====================================================
# DONUT CHARTS
# =====================================================
st.subheader("📊 Demand & Bias Snapshot")

c1, c2 = st.columns(2)

with c1:
    fig1, ax = plt.subplots()
    ax.pie(
        [bias_strength, remaining_strength],
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


st.markdown("""
---
**Designed by:-  
Gaurav Singh Yadav**   
🩷💛🩵💙🩶💜🤍🤎💖  Built With Love 🫶  
Energy | Commodity | Quant Intelligence 📶  
📱 +91-8003994518 〽️   
📧 yadav.gauravsingh@gmail.com ™️
""")
