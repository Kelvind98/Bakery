import streamlit as st

from state import init_state
from settings import maintenance_enabled, contact_email
from auth_ui import auth_sidebar
from home import page_home
from checkout import page_checkout
from track_order import page_track_order


def _maintenance_overlay():
    st.markdown(
        """
        <style>
          .maintenance-wrap {max-width: 760px; margin: 5vh auto; padding: 32px; border-radius: 18px;
            border: 1px solid rgba(255,255,255,0.15); background: rgba(255,255,255,0.04);}
          .maintenance-title {font-size: 40px; font-weight: 800; margin: 0 0 6px 0;}
          .maintenance-sub {font-size: 18px; opacity: 0.85; margin: 0 0 16px 0;}
        </style>
        """, unsafe_allow_html=True
    )

    st.markdown('<div class="maintenance-wrap">', unsafe_allow_html=True)
    st.markdown('<div class="maintenance-title">Website under maintenance</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="maintenance-sub">Please try again later. If you need help, email <b>{contact_email()}</b>.</div>',
        unsafe_allow_html=True
    )

    with st.expander("Admin unlock"):
        pin = st.text_input("Admin PIN", type="password")
        if st.button("Unlock for this session"):
            expected = st.secrets.get("CUSTOMER_MAINTENANCE_PIN", "")
            if expected and pin == expected:
                st.session_state._maintenance_unlocked = True
                st.success("Unlocked for this session.")
            else:
                st.error("Wrong PIN.")

    st.markdown("</div>", unsafe_allow_html=True)


def run_app():
    init_state()

    logged_in = auth_sidebar()

    unlocked = bool(st.session_state.get("_maintenance_unlocked", False))
    if maintenance_enabled() and not unlocked:
        _maintenance_overlay()
        st.stop()

    st.sidebar.title("Wivey Bakery")
    page = st.sidebar.radio("Menu", ["Shop", "Checkout", "Track order"], index=0)

    if page == "Shop":
        page_home()
    elif page == "Checkout":
        page_checkout(logged_in=logged_in)
    else:
        page_track_order()
