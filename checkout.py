import streamlit as st
from catalog import fetch_products
from cart import cart_totals, cart_set, cart_clear
from supabase_client import get_client

def _products_by_id():
    prods = fetch_products()
    return {int(p["id"]): p for p in prods}

def page_checkout(logged_in: bool = False):
    st.header("🧺 Checkout")

    sb = get_client()
    products_by_id = _products_by_id()

    items, subtotal = cart_totals(products_by_id)

    if not items:
        st.info("Your cart is empty. Go back to Shop to add items.")
        return

    st.subheader("Your cart")
    for it in items:
        c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
        with c1:
            st.write(it["name"])
        with c2:
            st.write(f"£{it['unit_price_ex_vat']:.2f}")
        with c3:
            new_qty = st.number_input("Qty", 0, 50, it["qty"], 1, key=f"cartqty_{it['product_id']}")
        with c4:
            st.write(f"£{it['line_ex_vat']:.2f}")
        if new_qty != it["qty"]:
            cart_set(it["product_id"], int(new_qty))
            st.rerun()

    st.divider()

    st.subheader("Order details")
    order_type = st.radio("Order type", ["pickup", "delivery"], horizontal=True)
    customer_email = st.text_input("Email (for tracking)", placeholder="you@example.com")
    customer_phone = st.text_input("Phone (optional)")
    delivery_address = ""
    if order_type == "delivery":
        delivery_address = st.text_area("Delivery address", height=80)
    notes = st.text_area("Notes (optional)", height=80)

    rpc_items = [{"product_id": i["product_id"], "qty": i["qty"]} for i in items]

    disabled = not customer_email.strip()
    if st.button("Place order", type="primary", disabled=disabled):
        try:
            if logged_in:
                try:
                    sb.rpc("ensure_customer_profile", {
                        "p_full_name": None,
                        "p_phone": customer_phone.strip() or None,
                        "p_marketing_consent": False
                    }).execute()
                except Exception:
                    pass

            payload = {
                "p_items": rpc_items,
                "p_order_type": order_type,
                "p_slot_start": None,
                "p_slot_end": None,
                "p_customer_email": customer_email.strip(),
                "p_customer_phone": customer_phone.strip() or None,
                "p_delivery_address": (delivery_address.strip() or None),
                "p_customer_notes": (notes.strip() or None),
            }
            resp = sb.rpc("guest_create_order", payload).execute()
            data = resp.data
            st.session_state.last_order = data
            cart_clear()
            st.success(f"Order placed! Your tracking code is: {data['order_code']}")
            st.caption("Use Track order in the sidebar to check progress.")
        except Exception as e:
            st.error("Order failed.")
            st.exception(e)

    st.caption("Email is required so we can help you and so you can track your order.")
