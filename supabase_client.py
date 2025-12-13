from __future__ import annotations
import os
import streamlit as st
from supabase import create_client, Client


def _get_cfg(key: str) -> str:
    if key in st.secrets:
        return str(st.secrets[key])
    v = os.getenv(key)
    if not v:
        raise RuntimeError(f"Missing config: {key}. Add it to Streamlit secrets or env vars.")
    return v


def _restore_session(sb: Client) -> None:
    """
    Restores the logged-in session for THIS rerun so sb.auth.get_user()
    works on every page (loyalty/profile/checkout).
    """
    tokens = st.session_state.get("sb_tokens")
    if not tokens:
        return

    access = tokens.get("access_token")
    refresh = tokens.get("refresh_token")
    if not access or not refresh:
        return

    try:
        # Newer signature
        sb.auth.set_session(access_token=access, refresh_token=refresh)
    except TypeError:
        # Older signature
        sb.auth.set_session(access, refresh)
    except Exception:
        # Tokens expired / invalid
        st.session_state.sb_tokens = None


def get_client() -> Client:
    # IMPORTANT: do not cache this client when using auth (prevents cross-user/session issues)
    url = _get_cfg("SUPABASE_URL")
    anon = _get_cfg("SUPABASE_ANON_KEY")
    sb = create_client(url, anon)

    # ✅ this is what fixes loyalty/profile saying you're not logged in
    _restore_session(sb)
    return sb
