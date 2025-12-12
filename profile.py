import streamlit as st
from supabase_client import SupabaseError

ALLERGY_OPTIONS = [
    "gluten","nuts","dairy","eggs","soy","sesame","fish","shellfish","mustard","celery","sulphites","lupin"
]

def friendly_auth_error(resp):
    try:
        j = resp.json()
        code = str(j.get("error_code","") or j.get("code","")).lower()
        msg = str(j.get("msg","") or j.get("message","")).lower()
    except Exception:
        code, msg = "", ""
    if "invalid_credentials" in code or "invalid login credentials" in msg:
        return "Details not recognized. Please check your email and password."
    if resp.status_code == 429:
        return "Too many attempts. Please wait a moment and try again."
    return "Login failed. Please try again."

def ensure_customer_profile(supabase, session):
    """Ensures a customer row exists for the logged-in Supabase Auth user.

    Uses a SECURITY DEFINER RPC on the database to avoid fragile RLS issues.
    SQL for the RPC is included in this patch zip.
    """
    user = session.get("user", {})
    email = user.get("email")
    token = session.get("access_token")
    if not email or not token:
        return None

    supabase.set_auth(token)

    try:
        res = supabase.rpc("ensure_customer_profile", {
            "p_email": email,
            "p_marketing_opt_in": bool(st.session_state.get("pending_marketing_opt_in", False)),
        })
        if isinstance(res, list) and res:
            return res[0]
        if isinstance(res, dict) and res:
            return res
    except SupabaseError as e:
        st.error(f"Profile RPC error: {e}")
    except Exception as e:
        st.error(f"Profile RPC error: {e}")

    return None

def render_customer_dashboard(supabase, customer_row):
    st.subheader("My Account")
    with st.form("account_form"):
        full_name = st.text_input("Full name", value=customer_row.get("full_name","") or "")
        phone = st.text_input("Phone", value=customer_row.get("phone","") or "")
        address = st.text_area("Address", value=customer_row.get("address","") or "", height=120)
        allergies = st.multiselect(
            "Allergies (menu items will be hidden)",
            ALLERGY_OPTIONS,
            default=customer_row.get("allergies") or []
        )
        marketing = st.checkbox("Marketing emails (optional)", value=bool(customer_row.get("marketing_opt_in", False)))
        save = st.form_submit_button("Save changes")

    if save:
        supabase.table("customers").update({
            "full_name": (full_name or "").strip(),
            "phone": (phone or "").strip(),
            "address": (address or "").strip(),
            "allergies": allergies,
            "marketing_opt_in": bool(marketing),
        }).eq("id", customer_row["id"]).execute()
        st.success("Saved")
        st.rerun()

def require_profile_completion(supabase, customer_row):
    missing = []
    for k in ["full_name", "phone", "address"]:
        if not customer_row.get(k):
            missing.append(k)
    if not missing:
        return
    st.warning("Please complete your details to continue.")
    render_customer_dashboard(supabase, customer_row)
    st.stop()
