from __future__ import annotations
import os
import streamlit as st
from supabase import create_client, Client

def _get_secret(key: str) -> str:
    # Streamlit Cloud uses st.secrets; locally you can set env vars
    if key in st.secrets:
        return str(st.secrets[key])
    v = os.getenv(key)
    if not v:
        raise RuntimeError(f"Missing config: {key}. Add it to Streamlit secrets or environment variables.")
    return v

@st.cache_resource(show_spinner=False)
def get_client() -> Client:
    url = _get_secret("SUPABASE_URL")
    anon = _get_secret("SUPABASE_ANON_KEY")
    return create_client(url, anon)
