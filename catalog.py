import streamlit as st
from utils.supabase_client import get_client

@st.cache_data(ttl=60, show_spinner=False)
def fetch_categories():
    sb = get_client()
    resp = sb.table("categories").select("id,name,description,is_active").eq("is_active", True).order("name").execute()
    return resp.data or []

@st.cache_data(ttl=60, show_spinner=False)
def fetch_products(category_id=None, search=None):
    sb = get_client()
    q = sb.table("products").select(
        "id,category_id,name,description,image_url,is_active,pricing_mode,manual_price_ex_vat,recommended_price_ex_vat,base_price,apply_vat,custom_vat_rate"
    ).eq("is_active", True)
    if category_id:
        q = q.eq("category_id", category_id)
    if search:
        # Supabase "ilike" is supported via .ilike
        q = q.ilike("name", f"%{search}%")
    resp = q.order("name").execute()
    return resp.data or []

def display_price_ex_vat(p: dict) -> float:
    # Mirrors DB pricing choice used in guest_create_order
    mode = (p.get("pricing_mode") or "auto")
    if mode == "manual" and p.get("manual_price_ex_vat") is not None:
        return float(p["manual_price_ex_vat"])
    if p.get("recommended_price_ex_vat") is not None:
        return float(p["recommended_price_ex_vat"])
    if p.get("base_price") is not None:
        return float(p["base_price"])
    return 0.0
