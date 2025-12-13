import streamlit as st
from supabase_client import get_client

def _restore_session(sb):
    tokens = st.session_state.get("sb_tokens")
    if not tokens:
        return
    access = tokens.get("access_token")
    refresh = tokens.get("refresh_token")
    if access and refresh:
        try:
            sb.auth.set_session(access_token=access, refresh_token=refresh)
        except TypeError:
            sb.auth.set_session(access, refresh)
        except Exception:
            st.session_state.sb_tokens = None

def auth_sidebar():
    sb = get_client()
    _restore_session(sb)

    st.sidebar.subheader("Account")

    user = None
    try:
        user = sb.auth.get_user().user
    except Exception:
        user = None

    if user:
        email = getattr(user, "email", None) or "Logged in"
        st.sidebar.success(email)
        if st.sidebar.button("Log out"):
            try:
                sb.auth.sign_out()
            except Exception:
                pass
            st.session_state.sb_tokens = None
            st.rerun()
        return True

    tabs = st.sidebar.tabs(["Log in", "Sign up"])

    with tabs[0]:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Log in", key="login_btn"):
            resp = sb.auth.sign_in_with_password({"email": email, "password": password})
            if resp and resp.session:
                s = resp.session.model_dump()
                st.session_state.sb_tokens = {
                    "access_token": s.get("access_token"),
                    "refresh_token": s.get("refresh_token"),
                }
                st.rerun()
            else:
                st.sidebar.error("Login failed. Check email/password (and email confirmation).")

    with tabs[1]:
        email2 = st.text_input("Email", key="signup_email")
        password2 = st.text_input("Password", type="password", key="signup_password")
        if st.button("Sign up", key="signup_btn"):
            sb.auth.sign_up({"email": email2, "password": password2})
            st.sidebar.info(
                "Account created. If email confirmation is enabled in Supabase, confirm your email before logging in."
            )

    return False
