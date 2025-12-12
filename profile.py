import streamlit as st

def ensure_customer_profile(supabase, session):
    user = session.get("user", {})
    auth_id = user.get("id")
    email = user.get("email")

    if not auth_id:
        return None

    supabase.set_auth(session["access_token"])

    existing = supabase.table("customers").select("*").eq("auth_user_id", auth_id).limit(1).execute()
    if existing:
        return existing[0]

    by_email = supabase.table("customers").select("*").eq("email", email).is_("auth_user_id", None).limit(1).execute()
    if by_email:
        supabase.table("customers").update({"auth_user_id": auth_id}).eq("id", by_email[0]["id"]).execute()
        linked = supabase.table("customers").select("*").eq("id", by_email[0]["id"]).limit(1).execute()
        return linked[0]

    created = supabase.table("customers").insert({
        "auth_user_id": auth_id,
        "email": email
    }).execute()
    return created[0] if created else None
