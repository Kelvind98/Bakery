import streamlit as st
from catalog import fetch_products
from cart import cart_totals, cart_set, cart_clear
from supabase_client import get_client

def _products_by_id():
    prods = fetch_products()
    return {int(p["id"]): p for p in prods}

def _get_user(sb):
    try:
        return sb.auth.get_user().user
    except Exception:
        return None

def _get_profile(sb, uid):
    # Returns customer row or None
    try:
        rows = sb.table("customers").select("id,full_name,phone,address,email").eq("auth_user_id", uid).limit(1).execute().data
        return rows[0] if rows else None
    except Exception:
        return None

def page_checkout(logged_in: bool = False):
    st.header("🧺 Checkout")

    sb = get_client()
    products_by_id = _products_by_id()

    items, subtotal = cart_totals(products_by_id)
    if not items:
        st.info("Your cart is empty. Go back to Shop to add items.")
        return

    # Logged-in user details for auto-fill
    user = _get_user(sb) if logged_in else None
    uid = getattr(user, "id", None) if user else None
    user_email = getattr(user, "email", None) if user else None
    profile = _get_profile(sb, uid) if uid else None

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

    # Email (tracking)
    if user_email:
        st.text_input("Email (for tracking)", value=user_email, disabled=True)
        customer_email = user_email
    else:
        customer_email = st.text_input("Email (for tracking)", placeholder="you@example.com").strip()

    # Mobile number (required)
    default_phone = (profile.get("phone") if profile else "") or ""
    customer_phone = st.text_input("Mobile number (required)", value=default_phone).strip()

    # Address (delivery required; pickup optional but can be stored in profile)
    default_address = (profile.get("address") if profile else "") or ""
    delivery_address = ""
    if order_type == "delivery":
        delivery_address = st.text_area("Delivery address (required)", value=default_address, height=90).strip()
    else:
        with st.expander("Add/update your address (optional)"):
            st.text_area("Address", value=default_address, height=90, key="pickup_address_optional")

    # Promo code (stored in notes for now)
    promo_code = st.text_input("Promo code (optional)", placeholder="e.g. WIVEY10").strip().upper()

    notes = st.text_area("Notes (optional)", height=80)

    # Build secure payload for RPC
    rpc_items = [{"product_id": i["product_id"], "qty": i["qty"]} for i in items]

    # Validation
    errors = []
    if not customer_email:
        errors.append("Email is required.")
    if not customer_phone:
        errors.append("Mobile number is required.")
    if order_type == "delivery" and not delivery_address:
        errors.append("Delivery address is required for delivery orders.")

    if errors:
        st.warning(" • " + "\n • ".join(errors))

    disabled = bool(errors)
    if st.button("Place order", type="primary", disabled=disabled):
        try:
            # If logged in, ensure profile exists and save phone (and address if provided)
            if uid:
                try:
                    sb.rpc("ensure_customer_profile", {
                        "p_full_name": (profile.get("full_name") if profile else None),
                        "p_phone": customer_phone or None,
                        "p_marketing_consent": False
                    }).execute()
                except Exception:
                    pass

                # Save address into customers table (RLS allows self-update)
                addr_to_save = delivery_address if order_type == "delivery" else (st.session_state.get("pickup_address_optional") or "").strip()
                if addr_to_save:
                    try:
                        sb.table("customers").update({"address": addr_to_save}).eq("auth_user_id", uid).execute()
                    except Exception:
                        pass

            # Store promo code in customer notes for now (DB discount logic can be added later)
            final_notes = (notes or "").strip()
            if promo_code:
                final_notes = (f"[PROMO:{promo_code}] " + final_notes).strip()

            payload = {
                "p_items": rpc_items,
                "p_order_type": order_type,
                "p_slot_start": None,
                "p_slot_end": None,
                "p_customer_email": customer_email,
                "p_customer_phone": customer_phone,
                "p_delivery_address": (delivery_address or None),
                "p_customer_notes": (final_notes or None),
            }
            resp = sb.rpc("guest_create_order", payload).execute()
            data = resp.data
            st.session_state.last_order = data
            cart_clear()
            st.success(f"Order placed! Your tracking code is: {data['order_code']}")
            if promo_code:
                st.info("Promo code saved with your order. (Automatic discount calculation can be enabled next.)")
            st.caption("Use Track order in the sidebar to check progress.")
        except Exception as e:
            st.error("Order failed.")
            st.exception(e)

    st.caption("If you're logged in, you can edit your profile (name, phone, address) from the Profile page.")
