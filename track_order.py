import streamlit as st
from utils.supabase_client import get_client

def page_track_order():
    st.header("🔎 Track your order")

    sb = get_client()
    code = st.text_input("Enter your order code", placeholder="WB-YYYYMMDD-001").strip()

    if st.button("Track order", disabled=not code):
        try:
            resp = sb.rpc("track_order_by_code", {"p_order_code": code}).execute()
            data = resp.data
            if not data:
                st.warning("No order found for that code.")
                return

            order = data.get("order") or {}
            items = data.get("items") or []

            st.subheader(f"Status: {order.get('status', 'unknown')}")
            st.write(f"Order type: {order.get('order_type', '')}")
            st.write(f"Placed: {order.get('created_at', '')}")
            st.write(f"Total (inc VAT): £{float(order.get('total_inc_vat', 0) or 0):.2f}")

            st.divider()
            st.subheader("Items")
            for it in items:
                st.write(f"- {it.get('qty')} × {it.get('product_name_snapshot')} (£{float(it.get('line_total_inc_vat',0) or 0):.2f})")

        except Exception as e:
            st.error("Tracking failed.")
            st.exception(e)
