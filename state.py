import streamlit as st

def init_state():
    if "cart" not in st.session_state:
        st.session_state.cart = {}
    if "last_order" not in st.session_state:
        st.session_state.last_order = None
    if "sb_tokens" not in st.session_state:
        st.session_state.sb_tokens = None
