import streamlit as st
from utils.supabase_client import get_client

def get_public_settings():
    sb = get_client()
    try:
        resp = sb.rpc("get_public_settings", {}).execute()
        return resp.data or {}
    except Exception:
        # If RPC not created yet, fail closed (maintenance off, contact fallback)
        return {"maintenance": {"enabled": False}, "contact": {"email": "wiveybakery@outlook.com"}}

def maintenance_enabled() -> bool:
    s = get_public_settings()
    enabled = bool((s.get("maintenance") or {}).get("enabled", False))
    return enabled

def contact_email() -> str:
    s = get_public_settings()
    return str((s.get("contact") or {}).get("email", "wiveybakery@outlook.com"))
