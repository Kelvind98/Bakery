import streamlit as st
from auth_client import SupabaseAuth
from supabase_client import SupabaseClient
from profile import ensure_customer_profile, friendly_auth_error, require_profile_completion, render_customer_dashboard
import customer_portal
import maintenance_gate
maintenance_gate.customer_maintenance_gate()

st.set_page_config(page_title="Wivey Bakery", layout="wide")

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]
AUTH_REDIRECT_URL = st.secrets.get("AUTH_REDIRECT_URL", "")

auth = SupabaseAuth(SUPABASE_URL, SUPABASE_ANON_KEY)
supabase = SupabaseClient(SUPABASE_URL, SUPABASE_ANON_KEY)

if "auth_session" not in st.session_state:
    st.session_state["auth_session"] = None
if "pending_marketing_opt_in" not in st.session_state:
    st.session_state["pending_marketing_opt_in"] = False

st.markdown("# Wivey Bakery")

customer_portal.render_cart_sidebar(supabase)

def render_login_panel():
    sess = st.session_state.get("auth_session")
    if sess and sess.get("access_token"):
        colA, colB = st.columns([4, 1])
        with colA:
            st.caption(f"Logged in as {sess.get('user',{}).get('email','')}")
        with colB:
            if st.button("Log out", use_container_width=True):
                try:
                    auth.sign_out(sess["access_token"])
                except Exception:
                    pass
                st.session_state["auth_session"] = None
                supabase.set_auth(None)
                st.rerun()
        return True

    with st.expander("Log in / Create account", expanded=False):
        tab1, tab2, tab3 = st.tabs(["Log in", "Create account", "Reset password"])

        with tab1:
            email = st.text_input("Email", key="li_email")
            pw = st.text_input("Password", type="password", key="li_pw")
            if st.button("Log in", use_container_width=True):
                r = auth.sign_in(email, pw)
                if r.ok:
                    st.session_state["auth_session"] = r.json()
                    st.success("Logged in")
                    st.rerun()
                else:
                    st.error(friendly_auth_error(r))

        with tab2:
            email = st.text_input("Email", key="su_email")
            pw = st.text_input("Password", type="password", key="su_pw")
            tc = st.checkbox("I agree to the Terms & Conditions", key="su_tc")
            marketing = st.checkbox("Marketing (optional)", key="su_mkt")
            if st.button("Create account", use_container_width=True):
                if not tc:
                    st.error("You must accept Terms & Conditions.")
                else:
                    r = auth.sign_up(email, pw)
                    if r.ok:
                        st.session_state["pending_marketing_opt_in"] = bool(marketing)
                        st.session_state["auth_session"] = r.json()
                        st.success("Account created. Check your email if confirmation is required.")
                        st.rerun()
                    else:
                        st.error("Unable to create account. Please try again.")

        with tab3:
            email = st.text_input("Email", key="rp_email")
            if st.button("Send reset link", use_container_width=True):
                if not AUTH_REDIRECT_URL:
                    st.error("AUTH_REDIRECT_URL is missing in Streamlit secrets.")
                else:
                    r = auth.send_reset(email, AUTH_REDIRECT_URL)
                    if r.ok:
                        st.success("Reset link sent. Check your email.")
                    else:
                        st.error("Could not send reset link. Please try again.")

    if st.button("Continue as guest", use_container_width=True):
        st.session_state["auth_session"] = None
        supabase.set_auth(None)
        st.rerun()

    return False

logged_in = render_login_panel()
session = st.session_state.get("auth_session") if logged_in else None
customer = None

if session and session.get("access_token"):
    supabase.set_auth(session["access_token"])
    customer = ensure_customer_profile(supabase, session)
    if not customer:
        st.error("Could not create customer profile.")
        st.stop()
    require_profile_completion(supabase, customer)

page = st.radio("Pages", ["Menu", "Checkout", "Tracking"] + (["My Orders", "My Account"] if logged_in else []), horizontal=True)

if page == "Menu":
    customer_portal.render_menu(supabase, customer)
elif page == "Checkout":
    customer_portal.render_checkout(supabase, customer, session)
elif page == "Tracking":
    customer_portal.render_tracking(supabase)
elif page == "My Orders":
    customer_portal.render_my_orders(supabase, session)
elif page == "My Account":
    render_customer_dashboard(supabase, customer)
