import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import hashlib
import time

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
# STREAMLIT CONFIG
# =====================================================
st.set_page_config(
    page_title="USA Weather → Natural Gas Demand Dashboard",
    layout="wide",
    page_icon="🔥"
)

# =====================================================
# 🔄 MANUAL + AUTO REFRESH (NO EXTERNAL LIB)
# =====================================================
c1, c2, c3 = st.columns([1.2, 1.8, 6])

with c1:
    if st.button("🔄 Refresh Now"):
        st.cache_data.clear()
        st.rerun()

with c2:
    auto_refresh = st.toggle("⏱ Auto Refresh (30 min)", value=False)

with c3:
    st.caption("Manual refresh forces fresh NOAA weather + NG demand recalculation")
# =====================================================
# AUTO REFRESH TIMER (SAFE)
# =====================================================
if auto_refresh:
    now = time.time()
    last = st.session_state.get("last_refresh", 0)

    if now - last > 30 * 60:  # 30 minutes
        st.session_state["last_refresh"] = now
        st.cache_data.clear()
        st.rerun()

# =====================================================
# CONSTANTS
# =====================================================
HEADERS = {"User-Agent": "weather-ng-dashboard (research@example.com)"}

HEATWAVE_TEMP = 35     # °C
COLDWAVE_TEMP = -5    # °C

# =====================================================
# STATE DATA (CAPITAL + LAT/LON + POPULATION WEIGHT)
# population ≈ state population (millions) for weighting
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
# FUNCTIONS
# =====================================================
def f_to_c(f):
    return round((f - 32) * 5 / 9, 1)

def get_hourly(lat, lon):
    p = requests.get(f"https://api.weather.gov/points/{lat},{lon}", headers=HEADERS)
    if p.status_code != 200:
        return None
    h_url = p.json()["properties"]["forecastHourly"]
    h = requests.get(h_url, headers=HEADERS)
    if h.status_code != 200:
        return None
    return h.json()["properties"]["periods"][:48]

def risk_flag(temp):
    if temp >= HEATWAVE_TEMP:
        return "🔥 Heatwave"
    if temp <= COLDWAVE_TEMP:
        return "❄️ Coldwave"
    return "Normal"

def gas_score(temp):
    if temp <= COLDWAVE_TEMP:
        return 1.5
    if temp >= HEATWAVE_TEMP:
        return 1.1
    return 1.0

# =====================================================
# DATA FETCH
# =====================================================
summary = []
hourly_rows = []
total_weighted_demand = 0
total_population = 0

with st.spinner("Fetching NOAA data (All 50 States)..."):
    for state, (city, lat, lon, pop) in US_STATES.items():
        hourly = get_hourly(lat, lon)
        if not hourly:
            continue

        temp_c = f_to_c(hourly[0]["temperature"])
        score = gas_score(temp_c)

        weighted = score * pop
        total_weighted_demand += weighted
        total_population += pop

        summary.append({
            "State": state,
            "City": city,
            "Temp (°C)": temp_c,
            "Risk": risk_flag(temp_c),
            "Population Weight": pop,
            "Gas Demand Score": round(score, 2),
            "Weighted Demand": round(weighted, 2)
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

# =====================================================
# NG DEMAND INDEX (0–100)
# =====================================================
ng_index = int(min(100, (total_weighted_demand / total_population) * 60))

# =====================================================
# DASHBOARD
# =====================================================
st.title("USA Weather → Natural Gas Demand Intelligence_By Gs_Yadav")
st.caption("NOAA Free Data | Trader-grade Energy & Commodity Bias")

st.subheader("📊 State-wise Weather Summary")
st.dataframe(df_summary, use_container_width=True)

st.subheader("⏱ 48-Hour Hourly Forecast")
st.dataframe(df_hourly, height=420, use_container_width=True)

# =====================================================
# PIE CHARTS
# =====================================================
st.markdown("---")
st.subheader("🛢️ Energy Demand Analytics (Next 24 Hours)")

col1, col2 = st.columns(2)

with col1:
    risk_counts = df_summary["Risk"].value_counts()
    fig1, ax1 = plt.subplots()
    ax1.pie(risk_counts, labels=risk_counts.index, autopct="%1.0f%%")
    ax1.set_title("Weather Risk Distribution")
    st.pyplot(fig1)

with col2:
    gas_bins = pd.cut(
        df_summary["Gas Demand Score"],
        bins=[0, 1.05, 1.3, 2],
        labels=["Normal", "High", "Very High"]
    ).value_counts()

    fig2, ax2 = plt.subplots()
    ax2.pie(gas_bins, labels=gas_bins.index, autopct="%1.0f%%")
    ax2.set_title("Natural Gas Demand Outlook")
    st.pyplot(fig2)

# =====================================================
# TRADER PANEL
# =====================================================
st.markdown("### 🧠 Trader Summary (NG Futures)")

if ng_index >= 70:
    bias = "📈 STRONG BULLISH Natural Gas (Heating Dominant)"
elif ng_index >= 55:
    bias = "📈 Mild Bullish Natural Gas"
else:
    bias = "⚖️ Neutral / Range-Bound"

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
# EXPORT
# =====================================================
st.markdown("---")
st.subheader("⬇️ Download Data")

st.download_button(
    "Download Summary CSV",
    df_summary.to_csv(index=False).encode(),
    "usa_weather_ng_summary.csv"
)

st.download_button(
    "Download Hourly CSV",
    df_hourly.to_csv(index=False).encode(),
    "usa_weather_hourly_48h.csv"
)

with pd.ExcelWriter("usa_weather_full.xlsx", engine="openpyxl") as writer:
    df_summary.to_excel(writer, sheet_name="Summary", index=False)
    df_hourly.to_excel(writer, sheet_name="Hourly_48h", index=False)

with open("usa_weather_full.xlsx", "rb") as f:
    st.download_button("Download Excel", f, "usa_weather_full.xlsx")

# =====================================================
# FOOTER
# =====================================================
st.markdown("""
---
**Designed by:-  
Gaurav Singh Yadav**   
🩷💛🩵💙🩶💜🤍🤎💖  Built With Love 🫶  
Energy | Commodity | Quant Intelligence 📶  
📱 +91-8003994518 〽️   
📧 yadav.gauravsingh@gmail.com ™️
""")
