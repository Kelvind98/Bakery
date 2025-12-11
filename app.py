import streamlit as st
import hashlib

from supabase_client import get_supabase_client
import customer_portal
from utils import get_current_customer, set_current_customer, logout_customer

st.set_page_config(page_title="Bakery – Order Online", layout="wide")

supabase = get_supabase_client()

if "customer" not in st.session_state:
    st.session_state["customer"] = None

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def _parse_allergies_input(raw: str):
    if not raw:
        return []
    parts = [p.strip() for p in raw.replace(";", ",").split(",")]
    return [p for p in parts if p]

def handle_auth():
    st.markdown("### Customer account")
    current = get_current_customer()

    # If logged in: show profile + orders + logout (NO login/signup/guest)
    if current:
        st.success(f"Signed in as {current['email']}")

        st.subheader("Your profile")

        # Extra info: address + allergies
        address_val = current.get("address", "") or ""
        allergies_list = current.get("allergies") or []

        col1, col2 = st.columns(2)
        with col1:
            new_name = st.text_input("Full name", value=current.get("full_name", ""), key="profile_full_name")
            new_email = st.text_input("Email", value=current.get("email", ""), key="profile_email")
            new_phone = st.text_input("Phone number", value=current.get("phone", ""), key="profile_phone")
            new_address = st.text_area(
                "Main address (used for deliveries)",
                value=address_val,
                help="Include house name/number, street, town and postcode.",
                key="profile_address",
            )
        with col2:
            st.markdown("#### Allergies")
            existing_allergy_text = ", ".join(allergies_list) if allergies_list else ""
            allergies_text = st.text_area(
                "List your allergies (comma-separated)",
                value=existing_allergy_text,
                help="Example: nuts, gluten, milk",
                key="profile_allergies",
            )
            st.info(
                "We will automatically hide menu items that list any of these allergens in their allergen information."
            )

            st.markdown("#### Change password")
            pw1 = st.text_input("New password", type="password", key="profile_pw1")
            pw2 = st.text_input("Confirm new password", type="password", key="profile_pw2")
            if st.button("Update password", key="profile_update_password"):
                if not pw1 or not pw2:
                    st.error("Please enter and confirm your new password.")
                elif pw1 != pw2:
                    st.error("Passwords do not match.")
                else:
                    pw_hash = hash_password(pw1)
                    supabase.table("customers").update({"password_hash": pw_hash}).eq(
                        "id", current["id"]
                    ).execute()
                    st.success("Password updated.")

        profile_incomplete = (not new_address) or (not allergies_text.strip())
        if profile_incomplete:
            st.warning(
                "Your profile is incomplete. Please provide an address and list any allergies so we can keep you safe and speed up checkout."
            )

        if st.button("Save profile details", key="profile_save"):
            allergies_parsed = _parse_allergies_input(allergies_text)
            update_payload = {
                "full_name": new_name,
                "email": new_email,
                "phone": new_phone,
                "address": new_address,
                "allergies": allergies_parsed,
            }
            supabase.table("customers").update(update_payload).eq("id", current["id"]).execute()
            set_current_customer(
                {
                    "id": current["id"],
                    "email": new_email,
                    "full_name": new_name,
                    "phone": new_phone,
                    "address": new_address,
                    "allergies": allergies_parsed,
                }
            )
            st.success("Profile updated.")
            if profile_incomplete:
                st.info("Once your profile is fully completed we can personalise your menu and orders.")

        st.markdown("---")
        st.subheader("My recent orders")
        try:
            orders_res = (
                supabase.table("orders")
                .select("*")
                .eq("customer_id", current["id"])
                .order("created_at", desc=True)
                .limit(20)
                .execute()
            )
            orders = orders_res.data or []
        except Exception:
            st.error("Unable to load your orders. Please try again later.")
            orders = []

        if not orders:
            st.info("You have no recent orders yet.")
        else:
            for o in orders:
                with st.expander(f"{o['order_code']} – {o['status']} – £{o['total_inc_vat']:.2f}"):
                    st.write(f"Placed: {o.get('created_at', '')}")
                    st.write(f"Type: {o.get('order_type', '')}")
                    st.write(f"Slot: {o.get('slot_start', '')} → {o.get('slot_end', '')}")
                    st.write(f"Payment method: {o.get('payment_method', '')}")
                    notes = o.get("customer_notes") or ""
                    if notes:
                        st.write(f"Notes: {notes}")

        st.markdown("---")
        if st.button("Log out", key="profile_logout"):
            logout_customer()
            st.success("You have been logged out.")
            st.rerun()

        return

    # Not logged in: show login / signup / guest options
    st.info("You are currently browsing as a guest. You can create an account to save your details and view order history.")
    tab_login, tab_signup, tab_guest = st.tabs(["Log in", "Create account", "Continue as guest"])

    # Log in tab
    with tab_login:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Log in", key="login_btn"):
            if not email or not password:
                st.error("Please enter email and password.")
            else:
                res = supabase.table("customers").select("*").eq("email", email).execute()
                if not res.data:
                    st.error("No account found with that email.")
                else:
                    cust = res.data[0]
                    stored_hash = cust.get("password_hash") or cust.get("password") or ""
                    if not stored_hash:
                        st.error("This account does not have a password set.")
                    else:
                        if hash_password(password) == stored_hash:
                            set_current_customer(
                                {
                                    "id": cust["id"],
                                    "email": cust["email"],
                                    "full_name": cust.get("full_name") or "",
                                    "phone": cust.get("phone") or "",
                                    "address": cust.get("address") or "",
                                    "allergies": cust.get("allergies") or [],
                                }
                            )
                            st.success("Logged in successfully.")
                            st.rerun()
                        else:
                            st.error("Incorrect password.")

    # Sign up tab
    with tab_signup:
        full_name = st.text_input("Full name", key="signup_name")
        email = st.text_input("Email", key="signup_email")
        phone = st.text_input("Phone number", key="signup_phone")
        password = st.text_input("Password", type="password", key="signup_password")
        confirm = st.text_input("Confirm password", type="password", key="signup_confirm")
        if st.button("Create account", key="signup_btn"):
            if not full_name or not email or not password:
                st.error("Name, email and password are required.")
            elif password != confirm:
                st.error("Passwords do not match.")
            else:
                existing = supabase.table("customers").select("*").eq("email", email).execute()
                if existing.data:
                    st.error("An account with that email already exists.")
                else:
                    pw_hash = hash_password(password)
                    payload = {
                        "full_name": full_name,
                        "email": email,
                        "phone": phone,
                        "password_hash": pw_hash,
                        "address": "",
                        "allergies": [],
                    }
                    created = supabase.table("customers").insert(payload).execute()
                    cust = created.data[0]
                    set_current_customer(
                        {
                            "id": cust["id"],
                            "email": cust["email"],
                            "full_name": cust.get("full_name") or "",
                            "phone": cust.get("phone") or "",
                            "address": cust.get("address") or "",
                            "allergies": cust.get("allergies") or [],
                        }
                    )
                    st.success("Account created and logged in. Please complete your address and allergy details below.")
                    st.rerun()

    # Guest tab
    with tab_guest:
        st.info("You can continue as a guest without creating an account.")
        if st.button("Continue as guest", key="guest_btn"):
            logout_customer()
            st.success("You are continuing as a guest.")
            st.rerun()

st.title("Bakery – Order Online")
st.caption("Place your order and choose a collection or delivery time.")

handle_auth()

tabs = st.tabs(["Place an order", "Track an order"])

with tabs[0]:
    customer_portal.render_customer_portal(supabase)

with tabs[1]:
    customer_portal.render_order_tracking(supabase)
