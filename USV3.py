import streamlit as st
import requests
import pandas as pd
from datetime import datetime
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
st.set_page_config(
    page_title="USA Weather → Natural Gas Intelligence",
    layout="wide"
)

HEADERS = {"User-Agent": "ng-weather-dashboard"}

HEATWAVE_TEMP = 35
COLDWAVE_TEMP = -5

# =====================================================
# US STATES + POPULATION WEIGHT
# =====================================================
US_STATES = {
    "Texas": ("Austin", 30.2672, -97.7431, 29.1),
    "California": ("Sacramento", 38.5816, -121.4944, 39.0),
    "Florida": ("Tallahassee", 30.4383, -84.2807, 22.6),
    "New York": ("Albany", 42.6526, -73.7562, 19.6),
    "Pennsylvania": ("Harrisburg", 40.2732, -76.8867, 12.9),
    "Illinois": ("Springfield", 39.7817, -89.6501, 12.6),
    "Ohio": ("Columbus", 39.9612, -82.9988, 11.8),
    "Georgia": ("Atlanta", 33.7490, -84.3880, 10.9),
    "North Carolina": ("Raleigh", 35.7796, -78.6382, 10.8),
    "Michigan": ("Lansing", 42.7325, -84.5555, 10.0),
}

TOTAL_POP = sum(v[3] for v in US_STATES.values())

# =====================================================
# FUNCTIONS
# =====================================================
def f_to_c(f):
    return round((f - 32) * 5 / 9, 2)

def get_hourly_forecast(lat, lon):
    p = requests.get(f"https://api.weather.gov/points/{lat},{lon}", headers=HEADERS)
    if p.status_code != 200:
        return []
    url = p.json()["properties"]["forecastHourly"]
    h = requests.get(url, headers=HEADERS)
    if h.status_code != 200:
        return []
    return h.json()["properties"]["periods"][:48]

def classify_weather(temp):
    if temp >= HEATWAVE_TEMP:
        return "🔥 Heatwave"
    elif temp <= COLDWAVE_TEMP:
        return "❄️ Coldwave"
    return "Normal"

# =====================================================
# DATA COLLECTION
# =====================================================
st.title("🇺🇸 USA Weather → Natural Gas Intelligence")
st.caption("Population-Weighted | Forecast-Driven | Trader Ready")

summary_rows = []
hourly_rows = []

with st.spinner("Fetching NOAA forecast for key US states..."):
    for state, (city, lat, lon, pop) in US_STATES.items():
        forecast = get_hourly_forecast(lat, lon)
        for h in forecast:
            temp_c = f_to_c(h["temperature"])
            hourly_rows.append({
                "State": state,
                "City": city,
                "Time": h["startTime"],
                "Temp (°C)": temp_c,
                "Population": pop
            })

df_hourly = pd.DataFrame(hourly_rows)
df_hourly["Time"] = pd.to_datetime(df_hourly["Time"])

# =====================================================
# POPULATION-WEIGHTED NG DEMAND
# =====================================================
df_hourly["HDD"] = (18 - df_hourly["Temp (°C)"]).clip(lower=0)
df_hourly["CDD"] = (df_hourly["Temp (°C)"] - 22).clip(lower=0)

df_hourly["NG_Demand"] = (
    df_hourly["HDD"] * 1.3 +
    df_hourly["CDD"] * 0.7
)

df_hourly["Weighted_Demand"] = (
    df_hourly["NG_Demand"] * df_hourly["Population"]
)

hourly_weighted = (
    df_hourly.groupby("Time")["Weighted_Demand"]
    .sum()
    .reset_index()
)

# =====================================================
# FORECAST-BASED NG TRADER BIAS
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

prev_mean = prev_24["Weighted_Demand"].mean()
next_mean = next_24["Weighted_Demand"].mean()
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
# DISPLAY
# =====================================================
st.subheader("🔥 Forecast-Based Natural Gas Trader Bias")

c1, c2, c3 = st.columns(3)
c1.metric("Prev 24h Demand", f"{prev_mean:.2f}")
c2.metric("Next 24h Demand", f"{next_mean:.2f}", f"{pct_change:.2f}%")
c3.metric("NG Bias", bias)

st.subheader("📊 Hourly Population-Weighted NG Demand")
st.dataframe(
    hourly_weighted.rename(columns={"Weighted_Demand": "NG Demand"}),
    use_container_width=True
)

# =====================================================
# EXPORT
# =====================================================
st.subheader("⬇️ Export")
csv = hourly_weighted.to_csv(index=False).encode()
st.download_button(
    "Download Forecast NG Demand CSV",
    csv,
    "ng_forecast_demand.csv"
)
