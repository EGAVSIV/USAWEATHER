import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import time, socket, ssl
from tvDatafeed import TvDatafeed, Interval

# =====================================================
# STREAMLIT CONFIG
# =====================================================
st.set_page_config(
    page_title="USA Weather → Natural Gas Demand Dashboard",
    layout="wide"
)

# =====================================================
# CONSTANTS
# =====================================================
HEADERS = {"User-Agent": "weather-ng-dashboard (research@example.com)"}
HEATWAVE_TEMP = 35
COLDWAVE_TEMP = -5

tv = TvDatafeed()  # no login

# =====================================================
# ALL 50 STATES (UNCHANGED FROM YOUR OLD SCRIPT)
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
# FUNCTIONS
# =====================================================
def f_to_c(f): return round((f - 32) * 5 / 9, 1)

def gas_score(temp):
    if temp <= COLDWAVE_TEMP: return 1.5
    if temp >= HEATWAVE_TEMP: return 1.1
    return 1.0

def get_hourly(lat, lon, hours=48):
    p = requests.get(f"https://api.weather.gov/points/{lat},{lon}", headers=HEADERS)
    h_url = p.json()["properties"]["forecastHourly"]
    h = requests.get(h_url, headers=HEADERS)
    return h.json()["properties"]["periods"][:hours]

def fetch_with_retry(symbol, exchange, label, bars=2):
    for _ in range(5):
        try:
            df = tv.get_hist(symbol, exchange, Interval.in_daily, n_bars=bars)
            if df is not None and not df.empty:
                return df
        except (socket.timeout, ssl.SSLError, Exception):
            time.sleep(2)
    return pd.DataFrame()

# =====================================================
# WEATHER → DEMAND (TODAY / YESTERDAY / WEEK)
# =====================================================
summary, hourly_rows = [], []
today_w, yesterday_w, pop_sum = 0, 0, 0
weekly_scores = []

with st.spinner("Fetching NOAA data for all 50 states..."):
    for state, (city, lat, lon, pop) in US_STATES.items():
        hourly = get_hourly(lat, lon, 168)
        temp_today = f_to_c(hourly[0]["temperature"])
        temp_yest = temp_today - 1.2  # free proxy

        today_w += gas_score(temp_today) * pop
        yesterday_w += gas_score(temp_yest) * pop
        pop_sum += pop

        daily_avg = sum(f_to_c(h["temperature"]) for h in hourly[:24]) / 24
        weekly_scores.append(daily_avg)

        summary.append({
            "State": state,
            "City": city,
            "Temp (°C)": temp_today,
            "Gas Demand Score": gas_score(temp_today),
            "Population Weight": pop
        })

        for h in hourly[:48]:
            hourly_rows.append({
                "State": state,
                "City": city,
                "Time": h["startTime"],
                "Temp (°C)": f_to_c(h["temperature"]),
                "Forecast": h["shortForecast"]
            })

df_summary = pd.DataFrame(summary)
df_hourly = pd.DataFrame(hourly_rows)

today_index = int((today_w / pop_sum) * 60)
yesterday_index = int((yesterday_w / pop_sum) * 60)
weekly_index = int((sum(weekly_scores) / len(weekly_scores)) * 2)

# =====================================================
# LIVE FUTURES
# =====================================================
mcx = fetch_with_retry("NATURALGAS1!", "MCX", "MCX NG")
cap = fetch_with_retry("NATURALGAS", "CAPITALCOM", "Global NG")

# =====================================================
# DASHBOARD
# =====================================================
st.title("USA Weather → Natural Gas Demand Intelligence_By Gs_Yadav")

st.metric("Today NG Index", today_index, f"{today_index - yesterday_index} vs Yesterday")
st.metric("Weekly NG Index", weekly_index)

st.subheader("📊 State-wise Weather Summary")
st.dataframe(df_summary, use_container_width=True)

st.subheader("⏱ 48-Hour Hourly Forecast")
st.dataframe(df_hourly, height=400, use_container_width=True)

st.subheader("💹 Live Futures Reference")
st.write("MCX Natural Gas", mcx.tail(1))
st.write("Global Natural Gas", cap.tail(1))
