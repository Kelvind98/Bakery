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
    user = session.get("user", {})
    auth_id = user.get("id")
    email = user.get("email")
    token = session.get("access_token")

    if not auth_id or not token:
        return None

    supabase.set_auth(token)

    # 1) select first
    existing = supabase.table("customers").select("*").eq("auth_user_id", auth_id).limit(1).execute()
    if existing:
        return existing[0]

    # 2) link by email if old row exists
    try:
        by_email = supabase.table("customers").select("*").eq("email", email).is_("auth_user_id", None).limit(1).execute()
        if by_email:
            supabase.table("customers").update({"auth_user_id": auth_id}).eq("id", by_email[0]["id"]).execute()
            linked = supabase.table("customers").select("*").eq("id", by_email[0]["id"]).limit(1).execute()
            return linked[0] if linked else None
    except Exception:
        pass

    # 3) create new (handle 409 by fallback select)
    try:
        created = supabase.table("customers").insert({
            "auth_user_id": auth_id,
            "email": email,
            "marketing_opt_in": bool(st.session_state.get("pending_marketing_opt_in", False)),
        }).execute()
        if created:
            return created[0]
    except SupabaseError:
        pass

    existing = supabase.table("customers").select("*").eq("auth_user_id", auth_id).limit(1).execute()
    return existing[0] if existing else None

def render_customer_dashboard(supabase, customer_row):
    st.subheader("My Account")
    with st.form("account_form"):
        full_name = st.text_input("Full name", value=customer_row.get("full_name",""))
        phone = st.text_input("Phone", value=customer_row.get("phone",""))
        address = st.text_area("Address", value=customer_row.get("address",""), height=120)
        allergies = st.multiselect("Allergies (menu items will be hidden)", ALLERGY_OPTIONS, default=customer_row.get("allergies") or [])
        marketing = st.checkbox("Marketing emails (optional)", value=bool(customer_row.get("marketing_opt_in", False)))
        save = st.form_submit_button("Save changes")

    if save:
        supabase.table("customers").update({
            "full_name": full_name.strip(),
            "phone": phone.strip(),
            "address": address.strip(),
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
