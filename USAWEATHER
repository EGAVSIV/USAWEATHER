import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# =====================================================
# CONFIG
# =====================================================
st.set_page_config(page_title="USA Weather Intelligence Dashboard", layout="wide")

HEADERS = {
    "User-Agent": "weather-dashboard (contact: research@example.com)"
}

# Heat / Cold thresholds (°C)
HEATWAVE_TEMP = 35
COLDWAVE_TEMP = -5

# =====================================================
# ALL 50 STATES (CAPITAL + LAT/LON)
# =====================================================
US_STATES = {
    "Alabama": ("Montgomery", 32.3668, -86.3000),
    "Alaska": ("Juneau", 58.3019, -134.4197),
    "Arizona": ("Phoenix", 33.4484, -112.0740),
    "Arkansas": ("Little Rock", 34.7465, -92.2896),
    "California": ("Sacramento", 38.5816, -121.4944),
    "Colorado": ("Denver", 39.7392, -104.9903),
    "Connecticut": ("Hartford", 41.7658, -72.6734),
    "Delaware": ("Dover", 39.1582, -75.5244),
    "Florida": ("Tallahassee", 30.4383, -84.2807),
    "Georgia": ("Atlanta", 33.7490, -84.3880),
    "Hawaii": ("Honolulu", 21.3069, -157.8583),
    "Idaho": ("Boise", 43.6150, -116.2023),
    "Illinois": ("Springfield", 39.7817, -89.6501),
    "Indiana": ("Indianapolis", 39.7684, -86.1581),
    "Iowa": ("Des Moines", 41.5868, -93.6250),
    "Kansas": ("Topeka", 39.0558, -95.6890),
    "Kentucky": ("Frankfort", 38.2009, -84.8733),
    "Louisiana": ("Baton Rouge", 30.4515, -91.1871),
    "Maine": ("Augusta", 44.3106, -69.7795),
    "Maryland": ("Annapolis", 38.9784, -76.4922),
    "Massachusetts": ("Boston", 42.3601, -71.0589),
    "Michigan": ("Lansing", 42.7325, -84.5555),
    "Minnesota": ("Saint Paul", 44.9537, -93.0900),
    "Mississippi": ("Jackson", 32.2988, -90.1848),
    "Missouri": ("Jefferson City", 38.5767, -92.1735),
    "Montana": ("Helena", 46.5891, -112.0391),
    "Nebraska": ("Lincoln", 40.8136, -96.7026),
    "Nevada": ("Carson City", 39.1638, -119.7674),
    "New Hampshire": ("Concord", 43.2081, -71.5376),
    "New Jersey": ("Trenton", 40.2204, -74.7643),
    "New Mexico": ("Santa Fe", 35.6870, -105.9378),
    "New York": ("Albany", 42.6526, -73.7562),
    "North Carolina": ("Raleigh", 35.7796, -78.6382),
    "North Dakota": ("Bismarck", 46.8083, -100.7837),
    "Ohio": ("Columbus", 39.9612, -82.9988),
    "Oklahoma": ("Oklahoma City", 35.4676, -97.5164),
    "Oregon": ("Salem", 44.9429, -123.0351),
    "Pennsylvania": ("Harrisburg", 40.2732, -76.8867),
    "Rhode Island": ("Providence", 41.8240, -71.4128),
    "South Carolina": ("Columbia", 34.0007, -81.0348),
    "South Dakota": ("Pierre", 44.3683, -100.3509),
    "Tennessee": ("Nashville", 36.1627, -86.7816),
    "Texas": ("Austin", 30.2672, -97.7431),
    "Utah": ("Salt Lake City", 40.7608, -111.8910),
    "Vermont": ("Montpelier", 44.2601, -72.5754),
    "Virginia": ("Richmond", 37.5407, -77.4360),
    "Washington": ("Olympia", 47.0379, -122.9007),
    "West Virginia": ("Charleston", 38.3498, -81.6326),
    "Wisconsin": ("Madison", 43.0731, -89.4012),
    "Wyoming": ("Cheyenne", 41.1400, -104.8202),
}

# =====================================================
# FUNCTIONS
# =====================================================
def f_to_c(f):
    return round((f - 32) * 5 / 9, 1)

def get_hourly_forecast(lat, lon):
    p = requests.get(f"https://api.weather.gov/points/{lat},{lon}", headers=HEADERS)
    if p.status_code != 200:
        return None

    hourly_url = p.json()["properties"]["forecastHourly"]
    h = requests.get(hourly_url, headers=HEADERS)
    if h.status_code != 200:
        return None

    return h.json()["properties"]["periods"][:48]

def classify_weather(temp_c):
    if temp_c >= HEATWAVE_TEMP:
        return "🔥 Heatwave Risk"
    elif temp_c <= COLDWAVE_TEMP:
        return "❄️ Coldwave Risk"
    return "Normal"

def commodity_impact(temp_c):
    if temp_c >= HEATWAVE_TEMP:
        return "↑ Power demand | ↑ Natural Gas | Stress on crops"
    if temp_c <= COLDWAVE_TEMP:
        return "↑ Heating demand | ↑ Gas | Transport disruption"
    return "Neutral impact"

# =====================================================
# STREAMLIT UI
# =====================================================
st.title("🇺🇸 USA Weather Intelligence Dashboard (FREE NOAA DATA)")
st.caption("48-Hour Hourly Forecast | Heatwave/Coldwave | Energy & Commodity Impact")

rows = []
hourly_rows = []

with st.spinner("Fetching NOAA data for all 50 states..."):
    for state, (city, lat, lon) in US_STATES.items():
        hourly = get_hourly_forecast(lat, lon)
        if not hourly:
            continue

        current_temp = f_to_c(hourly[0]["temperature"])
        flag = classify_weather(current_temp)

        rows.append({
            "State": state,
            "City": city,
            "Current Temp (°C)": current_temp,
            "Condition": hourly[0]["shortForecast"],
            "Risk Flag": flag,
            "Energy / Commodity Impact": commodity_impact(current_temp)
        })

        for h in hourly:
            hourly_rows.append({
                "State": state,
                "City": city,
                "Time": h["startTime"],
                "Temp (°C)": f_to_c(h["temperature"]),
                "Forecast": h["shortForecast"]
            })

df_summary = pd.DataFrame(rows)
df_hourly = pd.DataFrame(hourly_rows)

# =====================================================
# DISPLAY
# =====================================================
st.subheader("📊 State-wise Weather Summary")
st.dataframe(df_summary, use_container_width=True)

st.subheader("⏱ 48-Hour Hourly Forecast (All States)")
st.dataframe(df_hourly, height=400, use_container_width=True)

# =====================================================
# EXPORT
# =====================================================
st.subheader("⬇️ Export Data")

csv1 = df_summary.to_csv(index=False).encode()
csv2 = df_hourly.to_csv(index=False).encode()

st.download_button("Download Summary CSV", csv1, "usa_weather_summary.csv")
st.download_button("Download Hourly Forecast CSV", csv2, "usa_weather_hourly_48h.csv")

excel_file = "usa_weather_full.xlsx"
with pd.ExcelWriter(excel_file, engine="openpyxl") as writer:
    df_summary.to_excel(writer, sheet_name="Summary", index=False)
    df_hourly.to_excel(writer, sheet_name="Hourly_48h", index=False)

with open(excel_file, "rb") as f:
    st.download_button("Download Excel", f, excel_file)
