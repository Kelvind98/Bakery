from datetime import datetime
from dateutil import tz
import streamlit as st

def get_local_now():
    return datetime.now(tz=tz.gettz("Europe/London"))

def get_current_customer():
    return st.session_state.get("customer")

def set_current_customer(customer_dict):
    st.session_state["customer"] = customer_dict

def logout_customer():
    if "customer" in st.session_state:
        del st.session_state["customer"]
