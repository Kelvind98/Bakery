import streamlit as st
from ui_text import TERMS_AND_CONDITIONS, STATUS_HELP

def _hide_allergenic_products(products, allergies):
    if not allergies:
        return products
    allergies = set(a.lower() for a in allergies)
    filtered = []
    for p in products:
        pa = p.get("allergens") or []
        pa = set(a.lower() for a in pa)
        if pa.intersection(allergies):
            continue
        filtered.append(p)
    return filtered

def _cart():
    return st.session_state.setdefault("cart", {})  # {product_id: qty}

def clear_cart():
    st.session_state["cart"] = {}

def render_terms_checkbox(key="terms_ok"):
    st.markdown(TERMS_AND_CONDITIONS)
    return st.checkbox("I agree to the Terms & Conditions", key=key)

def render_menu(supabase, customer_row=None):
    st.subheader("Menu")
    q = st.text_input("Search", placeholder="Search cakes, bread, pastries...")
    products_q = supabase.table("products").select("*").eq("is_active", True).order("name").limit(500)
    if q.strip():
        products_q = products_q.ilike("name", f"*{q.strip()}*")
    products = products_q.execute()

    allergies = (customer_row or {}).get("allergies") if customer_row else None
    products = _hide_allergenic_products(products, allergies)

    if not products:
        st.info("No items available.")
        return

    cart = _cart()

    for p in products:
        pid = str(p["id"])
        with st.container(border=True):
            cols = st.columns([3,1])
            with cols[0]:
                st.markdown(f"**{p.get('name','Item')}**")
                if p.get("description"):
                    st.caption(p["description"])
                if p.get("image_url"):
                    st.image(p["image_url"], use_container_width=True)
                if p.get("allergens"):
                    st.caption("Allergens: " + ", ".join(p["allergens"]))
            with cols[1]:
                price = p.get("recommended_price_inc_vat") or p.get("price_inc_vat") or p.get("price") or 0
                st.markdown(f"**£{float(price):.2f}**")
                qty = st.number_input("Qty", min_value=0, max_value=50, value=int(cart.get(pid, 0)), key=f"qty_{pid}")
                if qty <= 0:
                    cart.pop(pid, None)
                else:
                    cart[pid] = int(qty)
    st.session_state["cart"] = cart

def render_cart_sidebar(supabase):
    with st.sidebar:
        st.markdown("## Cart")
        cart = _cart()
        if not cart:
            st.caption("Your cart is empty.")
            return

        products = supabase.table("products").select("id,name,recommended_price_inc_vat").limit(500).execute()
        prod_map = {str(p["id"]): p for p in products}
        total = 0.0
        for pid, qty in cart.items():
            p = prod_map.get(pid)
            if not p:
                continue
            price = float(p.get("recommended_price_inc_vat") or 0)
            total += price * qty
            st.write(f"{qty} × {p.get('name','Item')} — £{price*qty:.2f}")
        st.markdown(f"### Total: £{total:.2f}")
        if st.button("Clear cart", use_container_width=True):
            clear_cart()
            st.rerun()

def render_checkout(supabase, customer_row=None, session=None):
    st.subheader("Checkout")
    cart = _cart()
    if not cart:
        st.info("Your cart is empty.")
        return

    order_type = st.radio("Pickup or Delivery?", ["pickup", "delivery"], horizontal=True)
    if order_type == "delivery":
        st.caption("Delivery zone: Wiveliscombe only.")

    payment_method = st.selectbox("Payment method", ["cash", "card", "gift_card"])
    notes = st.text_area("Order notes (optional)")

    agreed = render_terms_checkbox("checkout_terms")
    if not agreed:
        st.warning("You must accept Terms & Conditions to place an order.")
        return

    products = supabase.table("products").select("id,name,recommended_price_inc_vat").limit(500).execute()
    prod_map = {str(p["id"]): p for p in products}
    total = 0.0
    line_items = []
    for pid, qty in cart.items():
        p = prod_map.get(pid)
        if not p:
            continue
        price = float(p.get("recommended_price_inc_vat") or 0)
        total += price * qty
        line_items.append({
            "product_id": int(p["id"]),
            "product_name_snapshot": p.get("name",""),
            "qty": int(qty),
            "unit_price_inc_vat": price
        })

    st.markdown(f"### Total: £{total:.2f}")

    gift_code = None
    if payment_method == "gift_card":
        gift_code = st.text_input("Gift card code")

    if st.button("Place order", use_container_width=True):
        payload = {
            "order_type": order_type,
            "payment_method": payment_method,
            "status": "pending",
            "total_inc_vat": round(total, 2),
            "order_notes": notes.strip() if notes else None,
        }
        if session and session.get("user") and customer_row:
            payload["customer_id"] = int(customer_row["id"])
            payload["customer_auth_user_id"] = session["user"]["id"]
            payload["customer_email_snapshot"] = session["user"].get("email")
            payload["customer_phone_snapshot"] = customer_row.get("phone")
        created = supabase.table("orders").insert(payload).execute()
        if not created:
            st.error("Order could not be created.")
            return
        order = created[0]
        oid = order["id"]

        for li in line_items:
            supabase.table("order_items").insert({
                "order_id": oid,
                "product_id": li["product_id"],
                "product_name_snapshot": li["product_name_snapshot"],
                "qty": li["qty"],
                "line_total_inc_vat": round(li["unit_price_inc_vat"] * li["qty"], 2),
            }).execute()

        if gift_code:
            st.info("Gift card will be validated/processed by staff if needed.")

        clear_cart()
        st.success(f"Order placed! Your order code is: {order.get('order_code','(code pending)')}")
        st.session_state["last_order_code"] = order.get("order_code")
        st.rerun()

def render_my_orders(supabase, session):
    st.subheader("My Orders")
    uid = session["user"]["id"]
    orders = supabase.table("orders").select("*").eq("customer_auth_user_id", uid).order("created_at", desc=True).limit(200).execute()
    if not orders:
        st.info("No orders yet.")
        return

    for o in orders:
    with st.container(border=True):
        code = o.get("order_code", "Order")
        status = o.get("status", "")
        st.markdown(f**{code}** — {status}")
        st.caption(STATUS_HELP.get(status, ""))
            st.caption(f"{o.get('order_type','')} • Total £{float(o.get('total_inc_vat') or 0):.2f}")
            cols = st.columns([1,1,2])
            with cols[0]:
                with st.expander("Items"):
                    items = supabase.table("order_items").select("*").eq("order_id", o["id"]).execute()
                    for it in items:
                        st.write(f"{it.get('qty')} × {it.get('product_name_snapshot')}")
            with cols[1]:
                if st.button("Reorder", key=f"reorder_{o['id']}", use_container_width=True):
                    items = supabase.table("order_items").select("*").eq("order_id", o["id"]).execute()
                    cart = {}
                    for it in items:
                        pid = str(it.get("product_id"))
                        if pid and pid != "None":
                            cart[pid] = int(it.get("qty") or 0)
                    st.session_state["cart"] = cart
                    st.success("Added to cart.")
                    st.rerun()
            with cols[2]:
                st.caption("Tracking: use your order code on the Tracking page (works for guest too).")

def render_tracking(supabase):
    st.subheader("Order Tracking")
    default_code = st.session_state.get("last_order_code", "")
    code = st.text_input("Enter your order code", value=default_code, placeholder="e.g., WIV-20251212-0001")
    if not code.strip():
        st.info("Enter an order code to view status.")
        return

    order = None
    try:
        res = supabase.rpc("track_order_by_code", {"p_order_code": code.strip()})
        if isinstance(res, list) and res:
            order = res[0]
        elif isinstance(res, dict) and res:
            order = res
    except Exception:
        order = None

    if not order:
        try:
            rows = supabase.table("orders").select("order_code,status,order_type,slot_start,slot_end,total_inc_vat").eq("order_code", code.strip()).limit(1).execute()
            order = rows[0] if rows else None
        except Exception:
            order = None

    if not order:
        st.error("Order not found. Please check the code.")
        return

    status = order.get("status","")
    st.markdown(f"### {order.get('order_code','')}")
    st.write(f"Status: **{status}** — {STATUS_HELP.get(status,'')}")
    st.write(f"Type: **{order.get('order_type','')}**")
    if order.get("slot_start"):
        st.write(f"Slot: {order.get('slot_start')} → {order.get('slot_end')}")
    st.write(f"Total: £{float(order.get('total_inc_vat') or 0):.2f}")
