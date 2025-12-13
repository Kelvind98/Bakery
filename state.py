import streamlit as st

def init_state():
    if "cart" not in st.session_state:
        st.session_state.cart = {}  # product_id -> qty
    if "last_order" not in st.session_state:
        st.session_state.last_order = None  # dict with order_code etc
