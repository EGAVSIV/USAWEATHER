import streamlit as st
import hashlib
import sys
import os

# 🔑 Ensure same-folder imports work on Streamlit Cloud
sys.path.append(os.path.dirname(__file__))

# 🔥 TEMPORARY TEST IMPORT
from test import run as run_test

# =====================================================
# PAGE CONFIG (ONLY ONCE)
# =====================================================
st.set_page_config(
    page_title="USA Intelligence Platform",
    layout="wide",
    page_icon="🇺🇸"
)

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
# TABS (TEST MODE)
# =====================================================
tab1 = st.tabs(["🧪 Test Tab"])[0]

with tab1:
    run_test()
