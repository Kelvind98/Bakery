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
    Make auth work across pages by restoring the saved tokens
    into the Supabase client on every rerun.
    """
    tokens = st.session_state.get("sb_tokens")
    if not tokens:
        return
    access = tokens.get("access_token")
    refresh = tokens.get("refresh_token")
    if not access or not refresh:
        return

    try:
        sb.auth.set_session(access_token=access, refresh_token=refresh)
    except TypeError:
        # Some versions use positional args
        sb.auth.set_session(access, refresh)
    except Exception:
        # If refresh failed/expired, clear tokens
        st.session_state.sb_tokens = None

def get_client() -> Client:
    # Do NOT cache the client when using auth (avoid cross-user session issues)
    url = _get_cfg("SUPABASE_URL")
    anon = _get_cfg("SUPABASE_ANON_KEY")
    sb = create_client(url, anon)

    # ✅ THIS is the important bit
    _restore_session(sb)
    return sb
