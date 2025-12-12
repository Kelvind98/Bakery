import streamlit as st

def customer_maintenance_gate():
    """Blocks the customer app when CUSTOMER_MAINTENANCE_MODE is true.

    Configure in Streamlit Cloud (Settings -> Secrets):
      CUSTOMER_MAINTENANCE_MODE = true/false
      CUSTOMER_MAINTENANCE_PIN = "1234"
      CUSTOMER_MAINTENANCE_EMAIL = "wiveybakery@outlook.com"
    """
    if not st.secrets.get("CUSTOMER_MAINTENANCE_MODE", False):
        return

    pin_required = str(st.secrets.get("CUSTOMER_MAINTENANCE_PIN", ""))
    email = st.secrets.get("CUSTOMER_MAINTENANCE_EMAIL", "wiveybakery@outlook.com")

    st.set_page_config(page_title="Wivey Bakery", layout="centered")

    st.markdown("## 🛠 Website under maintenance")
    st.write("Please try again later.")
    st.write(f"Or email **{email}**")

    if "customer_maintenance_ok" not in st.session_state:
        st.session_state.customer_maintenance_ok = False

    with st.expander("Admin access"):
        pin = st.text_input("Admin PIN", type="password")
        if st.button("Unlock"):
            if pin == pin_required:
                st.session_state.customer_maintenance_ok = True
                st.success("Customer site unlocked.")
                st.rerun()
            else:
                st.error("Incorrect PIN")

    if not st.session_state.customer_maintenance_ok:
        st.stop()
