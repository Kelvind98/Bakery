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
        sb.auth.set_session(access, refresh)
    except Exception:
        st.session_state.sb_tokens = None


def get_client() -> Client:
    url = _get_cfg("SUPABASE_URL")
    anon = _get_cfg("SUPABASE_ANON_KEY")

    sb = create_client(url, anon)

    # ✅ Critical: restore tokens for EVERY page / rerun
    _restore_session(sb)
    return sb
