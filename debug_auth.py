import streamlit as st
from supabase_client import get_client


def page_debug_auth():
    st.header("🛠️ Debug Auth (temporary)")

    sb = get_client()

    st.subheader("Session tokens in Streamlit")
    st.write("sb_tokens present:", bool(st.session_state.get("sb_tokens")))
    st.write(st.session_state.get("sb_tokens") or {})

    st.subheader("Supabase get_user()")
    try:
        u = sb.auth.get_user().user
        st.success("get_user() works ✅")
        st.write("id:", getattr(u, "id", None))
        st.write("email:", getattr(u, "email", None))
    except Exception as e:
        st.error("get_user() failed ❌")
        st.exception(e)

    st.subheader("auth.uid() via RPC (whoami)")
    try:
        uid = sb.rpc("whoami", {}).execute().data
        st.write("whoami() returned:", uid)
    except Exception as e:
        st.error("whoami RPC failed ❌")
        st.exception(e)

    st.subheader("Customer profile row")
    try:
        # If logged in, this should find your row
        uid = sb.rpc("whoami", {}).execute().data
        if uid:
            rows = (
                sb.table("customers")
                .select("id, auth_user_id, email, full_name")
                .eq("auth_user_id", uid)
                .limit(1)
                .execute()
                .data
            )
            st.write(rows)
        else:
            st.warning("No UID → you're not authenticated in this client.")
    except Exception as e:
        st.error("Customer lookup failed ❌")
        st.exception(e)
