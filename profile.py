import streamlit as st
from supabase_client import get_client

def _get_user(sb):
    try:
        return sb.auth.get_user().user
    except Exception:
        return None

def page_profile():
    st.header("👤 Profile")

    sb = get_client()
    user = _get_user(sb)
    if not user:
        st.info("Log in to view and edit your profile.")
        return

    uid = getattr(user, "id", None)
    email = getattr(user, "email", "")

    # Load profile row
    rows = sb.table("customers").select("id,full_name,phone,address,marketing_consent,allergies").eq("auth_user_id", uid).limit(1).execute().data
    cust = rows[0] if rows else None

    st.write(f"**Account email:** {email}")

    full_name = st.text_input("Full name", value=(cust.get("full_name") if cust else "") or "")
    phone = st.text_input("Mobile number", value=(cust.get("phone") if cust else "") or "")
    address = st.text_area("Address", value=(cust.get("address") if cust else "") or "", height=100)
    marketing = st.checkbox("I want to receive offers and marketing emails", value=bool((cust.get("marketing_consent") if cust else False) or False))

    allergies_raw = (cust.get("allergies") if cust else None) or []
    if isinstance(allergies_raw, list):
        allergies_text = ", ".join([str(x) for x in allergies_raw if x])
    else:
        allergies_text = str(allergies_raw)

    allergies_text = st.text_input("Allergies (comma separated)", value=allergies_text)

    if st.button("Save profile", type="primary"):
        # Ensure profile exists and save core fields via RPC
        sb.rpc("ensure_customer_profile", {
            "p_full_name": full_name.strip() or None,
            "p_phone": phone.strip() or None,
            "p_marketing_consent": marketing
        }).execute()

        # Save extra fields directly (RLS allows self-update)
        allergies_list = [a.strip() for a in allergies_text.split(",") if a.strip()]
        sb.table("customers").update({
            "address": address.strip() or None,
            "allergies": allergies_list if allergies_list else None
        }).eq("auth_user_id", uid).execute()

        st.success("Profile saved.")
