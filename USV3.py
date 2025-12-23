import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import hashlib
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
    page_title="USA Weather → Natural Gas Intelligence",
    layout="wide"
)

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
    auto_refresh = st.toggle("⏱ Auto Refresh (30 min)", value=False)

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

    if now - last >= 30 * 60:  # 30 minutes
        st.session_state["last_refresh"] = now
        st.cache_data.clear()
        st.rerun()




HEADERS = {"User-Agent": "ng-weather-dashboard"}

HEATWAVE_TEMP = 35
COLDWAVE_TEMP = -5

# =====================================================
# US STATES + POPULATION WEIGHT
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

st.markdown("""
---
**Designed by:-  
Gaurav Singh Yadav**   
🩷💛🩵💙🩶💜🤍🤎💖  Built With Love 🫶  
Energy | Commodity | Quant Intelligence 📶  
📱 +91-8003994518 〽️   
📧 yadav.gauravsingh@gmail.com ™️
""")
