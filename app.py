import streamlit as st
from auth_client import SupabaseAuth
from supabase_client import SupabaseClient
from profile import ensure_customer_profile, require_profile_completion, render_account_settings
from customer_portal import render_menu_and_checkout, render_order_tracking

st.set_page_config(page_title="Wivey Bakery", page_icon="🥐", layout="wide")

COMPANY_NAME = "Wivey Bakery"

SUPABASE_URL = st.secrets.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON_KEY = st.secrets.get("SUPABASE_ANON_KEY", "")
AUTH_REDIRECT_URL = st.secrets.get("AUTH_REDIRECT_URL", "")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    st.error("Missing SUPABASE_URL or SUPABASE_ANON_KEY in Streamlit secrets.")
    st.stop()

supabase = SupabaseClient(SUPABASE_URL, SUPABASE_ANON_KEY)
auth = SupabaseAuth(SUPABASE_URL, SUPABASE_ANON_KEY)

def get_session():
    return st.session_state.get("auth_session")

def set_session(sess: dict):
    st.session_state["auth_session"] = sess

def clear_session():
    st.session_state.pop("auth_session", None)

def is_logged_in() -> bool:
    sess = get_session()
    return bool(sess and sess.get("access_token"))

with st.container():
    cols = st.columns([3, 2, 2])
    with cols[0]:
        st.markdown(f"## 🥐 {COMPANY_NAME}")
        st.caption("Online ordering • Pick‑up & delivery (Wiveliscombe)")
    with cols[2]:
        if not is_logged_in():
            with st.expander("Log in / Create account", expanded=False):
                t1, t2, t3 = st.tabs(["Log in", "Create account", "Reset password"])

                with t1:
                    email = st.text_input("Email", key="li_email")
                    pw = st.text_input("Password", type="password", key="li_pw")
                    if st.button("Log in", use_container_width=True, key="btn_login"):
                        r = auth.sign_in(email, pw)
                        if r.ok:
                            set_session(r.json())
                            st.success("Logged in")
                            st.rerun()
                        else:
                            st.error(r.text)

                with t2:
                    email2 = st.text_input("Email", key="su_email")
                    pw2 = st.text_input("Password", type="password", key="su_pw")
                    tc = st.checkbox("I agree to the Terms & Conditions", key="su_tc")
                    mk = st.checkbox("Marketing (optional)", key="su_mkt")
                    if st.button("Create account", use_container_width=True, key="btn_signup"):
                        if not tc:
                            st.error("You must accept Terms & Conditions.")
                        else:
                            r = auth.sign_up(email2, pw2)
                            if r.ok:
                                set_session(r.json())
                                st.session_state["pending_marketing_opt_in"] = bool(mk)
                                st.success("Account created. If email confirmation is enabled, check your inbox.")
                                st.rerun()
                            else:
                                st.error(r.text)

                with t3:
                    email3 = st.text_input("Email", key="rp_email")
                    if st.button("Send reset link", use_container_width=True, key="btn_reset"):
                        if not AUTH_REDIRECT_URL:
                            st.error("Missing AUTH_REDIRECT_URL in secrets.")
                        else:
                            r = auth.send_reset_email(email3, AUTH_REDIRECT_URL)
                            if r.ok:
                                st.success("Reset link sent. Check your email.")
                            else:
                                st.error(r.text)

            st.write("")
            if st.button("Continue as guest", use_container_width=True, key="btn_guest"):
                st.session_state["guest_mode"] = True
                st.rerun()
        else:
            sess = get_session()
            email = (sess.get("user") or {}).get("email", "Account")
            st.markdown(f"**Signed in:** {email}")
            if st.button("Log out", use_container_width=True, key="btn_logout"):
                try:
                    auth.sign_out(sess["access_token"])
                except Exception:
                    pass
                clear_session()
                st.rerun()

tabs = st.tabs(["Menu & Checkout", "Track Order", "My Account"])
menu_tab, track_tab, acct_tab = tabs

customer_row = None
if is_logged_in():
    sess = get_session()
    supabase.set_auth(sess["access_token"])
    customer_row = ensure_customer_profile(supabase, sess)
    customer_row = require_profile_completion(supabase, customer_row)

with menu_tab:
    render_menu_and_checkout(supabase, customer_row)

with track_tab:
    render_order_tracking(supabase, customer_row)

with acct_tab:
    if not is_logged_in():
        st.info("Log in to view and edit your account.")
    else:
        render_account_settings(supabase, customer_row)
