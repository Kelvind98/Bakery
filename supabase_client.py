from __future__ import annotations
import os
import streamlit as st
from supabase import create_client, Client


def _cfg(key: str) -> str:
    if key in st.secrets:
        return str(st.secrets[key])
    v = os.getenv(key)
    if not v:
        raise RuntimeError(f"Missing config: {key}")
    return v


def _restore_session(sb: Client) -> None:
    """
    Restore Supabase auth session on EVERY rerun.
    This is the critical missing piece.
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
        sb.auth.set_session(access, refresh)
    except Exception:
        # Tokens invalid/expired
        st.session_state.sb_tokens = None


def get_client() -> Client:
    sb = create_client(
        _cfg("SUPABASE_URL"),
        _cfg("SUPABASE_ANON_KEY"),
    )

    # 🔥 THIS is what fixes Loyalty/Profile
    _restore_session(sb)

    return sb
