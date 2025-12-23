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
# STATES (Population Weighted – SAME AS BEFORE)
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

def get_hourly_observed(lat, lon, days=7):
    """Past observed hourly temps"""
    end = datetime.utcnow()
    start = end - timedelta(days=days)

    url = f"https://api.weather.gov/points/{lat},{lon}"
    p = requests.get(url, headers=HEADERS)
    if p.status_code != 200:
        return []

    stations_url = p.json()["properties"]["observationStations"]
    s = requests.get(stations_url, headers=HEADERS).json()
    station = s["features"][0]["id"]

    obs_url = f"{station}/observations"
    params = {
        "start": start.isoformat() + "Z",
        "end": end.isoformat() + "Z"
    }
    r = requests.get(obs_url, headers=HEADERS, params=params)
    if r.status_code != 200:
        return []

    return r.json()["features"]

def get_hourly_forecast(lat, lon):
    p = requests.get(f"https://api.weather.gov/points/{lat},{lon}", headers=HEADERS)
    if p.status_code != 200:
        return []
    url = p.json()["properties"]["forecastHourly"]
    h = requests.get(url, headers=HEADERS)
    return h.json()["properties"]["periods"][:48]

# =====================================================
# BUILD DEMAND (SAME FORMULA)
# =====================================================
def calc_ng_demand(temp_c):
    hdd = max(18 - temp_c, 0)
    cdd = max(temp_c - 22, 0)
    return hdd * 1.3 + cdd * 0.7

# =====================================================
# HISTORICAL DEMAND (OBSERVED)
# =====================================================
st.title("📈 Natural Gas Demand vs Price (Historical + Forecast)")

hist_rows = []

with st.spinner("Fetching historical observed temperatures..."):
    for state, (_, lat, lon, pop) in US_STATES.items():
        obs = get_hourly_observed(lat, lon, days=7)
        for o in obs:
            t = o["properties"]["temperature"]["value"]
            if t is None:
                continue
            hist_rows.append({
                "Date": pd.to_datetime(o["properties"]["timestamp"]).date(),
                "Demand": calc_ng_demand(t),
                "Population": pop
            })

df_hist = pd.DataFrame(hist_rows)

hist_daily = (
    df_hist.assign(Weighted=lambda x: x["Demand"] * x["Population"])
    .groupby("Date")["Weighted"]
    .sum()
    .reset_index(name="NG_Demand")
)

# =====================================================
# FUTURE DEMAND (FORECAST)
# =====================================================
fut_rows = []

for state, (_, lat, lon, pop) in US_STATES.items():
    fc = get_hourly_forecast(lat, lon)
    for h in fc:
        fut_rows.append({
            "Date": pd.to_datetime(h["startTime"]).date(),
            "Demand": calc_ng_demand(f_to_c(h["temperature"])),
            "Population": pop
        })

df_fut = pd.DataFrame(fut_rows)

fut_daily = (
    df_fut.assign(Weighted=lambda x: x["Demand"] * x["Population"])
    .groupby("Date")["Weighted"]
    .sum()
    .reset_index(name="NG_Demand")
)

# =====================================================
# PRICE DATA (TV DATAFEED)
# =====================================================
tv = TvDatafeed()
price = tv.get_hist(
    symbol="NATURALGAS",
    exchange="CAPITALCOM",
    interval=Interval.in_daily,
    n_bars=30
)

price = price.reset_index()[["datetime", "close"]]
price["Date"] = price["datetime"].dt.date
price.rename(columns={"close": "NG_Price"}, inplace=True)

# =====================================================
# PLOT
# =====================================================
fig, ax1 = plt.subplots(figsize=(13, 6))

# Historical
ax1.plot(hist_daily["Date"], hist_daily["NG_Demand"],
         label="NG Demand (Observed)", linewidth=2)

# Forecast (dotted)
ax1.plot(fut_daily["Date"], fut_daily["NG_Demand"],
         linestyle="--", label="NG Demand (Forecast)", linewidth=2)

ax1.set_ylabel("NG Demand (Weighted Index)")
ax1.grid(alpha=0.3)

ax2 = ax1.twinx()

ax2.plot(price["Date"], price["NG_Price"],
         color="black", linewidth=2, label="NG Price")

# Price projection placeholder (dotted)
ax2.plot(
    [price["Date"].iloc[-1], fut_daily["Date"].iloc[-1]],
    [price["NG_Price"].iloc[-1], price["NG_Price"].iloc[-1]],
    linestyle="--",
    color="black",
    label="Price Projection (Model)"
)

ax2.set_ylabel("NG Price")

fig.legend(loc="upper left")
st.pyplot(fig)

# =====================================================
# TABLE
# =====================================================
st.subheader("📊 Historical NG Demand")
st.dataframe(hist_daily, use_container_width=True)

st.subheader("🔮 Forecast NG Demand")
st.dataframe(fut_daily, use_container_width=True)
