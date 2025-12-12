import streamlit as st
from auth_client import SupabaseAuth
from supabase_client import SupabaseClient
from profile import ensure_customer_profile

st.set_page_config(page_title="Wivey Bakery", layout="wide")

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]
AUTH_REDIRECT_URL = st.secrets["AUTH_REDIRECT_URL"]

auth = SupabaseAuth(SUPABASE_URL, SUPABASE_ANON_KEY)
supabase = SupabaseClient(SUPABASE_URL, SUPABASE_ANON_KEY)

st.title("Wivey Bakery")

if "auth_session" not in st.session_state:
    st.session_state.auth_session = None

with st.expander("Log in / Create account"):
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Log in"):
            r = auth.sign_in(email, password)
            if r.ok:
                st.session_state.auth_session = r.json()
                st.success("Logged in")
                st.rerun()
            else:
                st.error("Details not recognized. Please check your email and password.")

    with col2:
        if st.button("Create account"):
            r = auth.sign_up(email, password)
            if r.ok:
                st.session_state.auth_session = r.json()
                st.success("Account created. Check your email if confirmation is required.")
                st.rerun()
            else:
                st.error("Unable to create account. Please try again.")

if st.session_state.auth_session:
    customer = ensure_customer_profile(supabase, st.session_state.auth_session)
    if not customer:
        st.error("Could not create customer profile.")
    else:
        st.success(f"Welcome {customer.get('email')}")
