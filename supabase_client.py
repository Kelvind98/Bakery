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

def get_client() -> Client:
    # IMPORTANT: do NOT cache the client when using auth, otherwise sessions can leak across users.
    url = _get_cfg("SUPABASE_URL")
    anon = _get_cfg("SUPABASE_ANON_KEY")
    return create_client(url, anon)
