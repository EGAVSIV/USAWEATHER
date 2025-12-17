import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt

# =====================================================
# STREAMLIT CONFIG
# =====================================================
st.set_page_config(
    page_title="USA Weather → Natural Gas Demand Dashboard",
    layout="wide"
)

# =====================================================
# CUSTOM CSS (ENERGY THEME)
# =====================================================
st.markdown("""
<style>
.main {background-color:#0e1117;}
h1, h2, h3 {color:#f5c542;}
[data-testid="stMetricValue"] {font-size:28px;color:#00ffcc;}
[data-testid="stMetricDelta"] {font-size:18px;}
.block-container {padding-top:1rem;}
hr {border:1px solid #333;}
</style>
""", unsafe_allow_html=True)

# =====================================================
# CONSTANTS
# =====================================================
HEADERS = {"User-Agent": "weather-ng-dashboard (research@example.com)"}
HEATWAVE_TEMP = 35
COLDWAVE_TEMP = -5

# =====================================================
# STATE DATA (UNCHANGED)
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
# FUNCTIONS (UNCHANGED)
# =====================================================
def f_to_c(f): return round((f - 32) * 5 / 9, 1)

def get_hourly(lat, lon):
    p = requests.get(f"https://api.weather.gov/points/{lat},{lon}", headers=HEADERS)
    h = requests.get(p.json()["properties"]["forecastHourly"], headers=HEADERS)
    return h.json()["properties"]["periods"][:48]

def risk_flag(temp):
    if temp >= HEATWAVE_TEMP: return "🔥 Heatwave"
    if temp <= COLDWAVE_TEMP: return "❄️ Coldwave"
    return "Normal"

def gas_score(temp):
    if temp <= COLDWAVE_TEMP: return 1.5
    if temp >= HEATWAVE_TEMP: return 1.1
    return 1.0

# =====================================================
# DATA FETCH (UNCHANGED)
# =====================================================
summary, hourly_rows = [], []
tw, tp = 0, 0

with st.spinner("⚡ Fetching NOAA Energy Data (50 States)..."):
    for state, (city, lat, lon, pop) in US_STATES.items():
        hourly = get_hourly(lat, lon)
        t = f_to_c(hourly[0]["temperature"])
        w = gas_score(t) * pop
        tw += w
        tp += pop

        summary.append({
            "State": state,
            "City": city,
            "Temp (°C)": t,
            "Risk": risk_flag(t),
            "Population Weight": pop,
            "Gas Demand Score": round(gas_score(t), 2),
            "Weighted Demand": round(w, 2)
        })

        for h in hourly:
            hourly_rows.append({
                "State": state,
                "City": city,
                "Time": h["startTime"],
                "Temp (°C)": f_to_c(h["temperature"]),
                "Forecast": h["shortForecast"]
            })

df_summary = pd.DataFrame(summary)
df_hourly = pd.DataFrame(hourly_rows)
ng_index = int(min(100, (tw / tp) * 60))

# =====================================================
# DASHBOARD
# =====================================================
st.title("🛢️ USA Weather → Natural Gas Demand Intelligence")
st.caption("NOAA Free Data | Energy Traders Dashboard")

colA, colB, colC = st.columns(3)
colA.metric("🔥 Heat / ❄️ Cold Index", ng_index)
colB.metric("📊 States Covered", 50)
colC.metric("⚡ Data Source", "NOAA")

st.subheader("📊 State-wise Weather Summary")
st.dataframe(df_summary, use_container_width=True)

st.subheader("⏱ 48-Hour Hourly Forecast")
st.dataframe(df_hourly, height=420, use_container_width=True)

st.markdown("---")
st.subheader("🛢️ Energy Demand Analytics (Next 24 Hours)")

col1, col2 = st.columns(2)

with col1:
    rc = df_summary["Risk"].value_counts()
    fig, ax = plt.subplots()
    ax.pie(rc, labels=rc.index, autopct="%1.0f%%")
    st.pyplot(fig)

with col2:
    gb = pd.cut(df_summary["Gas Demand Score"], [0,1.05,1.3,2],
                labels=["Normal","High","Very High"]).value_counts()
    fig2, ax2 = plt.subplots()
    ax2.pie(gb, labels=gb.index, autopct="%1.0f%%")
    st.pyplot(fig2)

st.markdown("### 🧠 Trader Bias")
bias = "STRONG BULLISH" if ng_index>=70 else "MILD BULLISH" if ng_index>=55 else "NEUTRAL"
st.success(f"**NG Bias:** {bias}  |  **Index:** {ng_index}/100")

st.markdown("---")
st.download_button("⬇️ Download Summary CSV",
                   df_summary.to_csv(index=False).encode(),
                   "usa_weather_ng_summary.csv")
