import streamlit as st
import hashlib
import sys
import os

# 🔑 Path fix (keep this)
sys.path.append(os.path.dirname(__file__))

from USAW import run as run_usaw
from USV1 import run as run_usv1
from USV2 import run as run_usv2
from USV3 import run as run_usv3
from USWF import run as run_uswf


st.set_page_config(
    page_title="USA Intelligence Platform",
    layout="wide",
    page_icon="🇺🇸"
)

# ========= LOGIN =========
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

# ========= TABS =========
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 USV1",
    "📈 USV2",
    "🧠 USV3",
    "🌦 US Weather",
    "🇺🇸 USA Analytics"
])

with tab1:
    run_usv1()

with tab2:
    run_usv2()

with tab3:
    run_usv3()

with tab4:
    run_uswf()

with tab5:
    run_usaw()
