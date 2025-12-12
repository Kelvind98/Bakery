import streamlit as st
from ui_text import TERMS_AND_CONDITIONS, STATUS_HELP

VAT_DEFAULT = 20.0  # used only to compute ex-VAT unit prices for order_items rows

def _cart():
    return st.session_state.setdefault("cart", {})  # {product_id: qty}

def clear_cart():
    st.session_state["cart"] = {}

def _hide_allergenic_products(products, allergies):
    if not allergies:
        return products
    allergies = set(a.lower() for a in allergies)
    safe = []
    for p in products:
        prod_allergens = set(a.lower() for a in (p.get("allergens") or []))
        if prod_allergens.intersection(allergies):
            continue
        safe.append(p)
    return safe

def render_terms_checkbox(key="terms_ok"):
    st.markdown(TERMS_AND_CONDITIONS)
    return st.checkbox("I agree to the Terms & Conditions", key=key)

def render_menu(supabase, customer_row=None):
    st.subheader("Menu")
    q = st.text_input("Search", placeholder="Search items...")
    query = supabase.table("products").select("*").eq("is_active", True).order("name")
    if q.strip():
        query = query.ilike("name", f"*{q.strip()}*")
    products = query.execute()

    allergies = customer_row.get("allergies") if customer_row else None
    products = _hide_allergenic_products(products, allergies)

    if not products:
        st.info("No items available.")
        return

    cart = _cart()
    for p in products:
        pid = str(p["id"])
        with st.container(border=True):
            cols = st.columns([3, 1])
            with cols[0]:
                st.markdown(f"**{p.get('name', 'Item')}**")
                if p.get("description"):
                    st.caption(p["description"])
                if p.get("image_url"):
                    st.image(p["image_url"], use_container_width=True)
                if p.get("allergens"):
                    st.caption("Allergens: " + ", ".join(p["allergens"]))
            with cols[1]:
                price = float(p.get("recommended_price_inc_vat") or p.get("price_inc_vat") or p.get("price") or 0)
                st.markdown(f"**£{price:.2f}**")
                qty = st.number_input("Qty", 0, 50, int(cart.get(pid, 0)), key=f"qty_{pid}")
                if qty > 0:
                    cart[pid] = int(qty)
                else:
                    cart.pop(pid, None)
    st.session_state["cart"] = cart

def render_cart_sidebar(supabase):
    with st.sidebar:
        st.markdown("## Cart")
        cart = _cart()
        if not cart:
            st.caption("Your cart is empty.")
            return

        products = supabase.table("products").select("id,name,recommended_price_inc_vat").execute()
        prod_map = {str(p["id"]): p for p in products}

        total = 0.0
        for pid, qty in cart.items():
            p = prod_map.get(pid)
            if not p:
                continue
            price = float(p.get("recommended_price_inc_vat") or 0)
            total += price * qty
            st.write(f"{qty} × {p['name']} — £{price*qty:.2f}")

        st.markdown(f"### Total: £{total:.2f}")
        if st.button("Clear cart", use_container_width=True):
            clear_cart()
            st.rerun()

def _compute_unit_ex_vat(unit_inc_vat: float, vat_percent: float) -> float:
    return round(unit_inc_vat / (1.0 + (vat_percent / 100.0)), 2)

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

    products = supabase.table("products").select("id,name,recommended_price_inc_vat").execute()
    prod_map = {str(p["id"]): p for p in products}

    total = 0.0
    line_items_for_db = []
    line_items_for_rpc = []

    for pid, qty in cart.items():
        p = prod_map.get(pid)
        if not p:
            continue
        qty_i = int(qty)
        unit_inc = float(p.get("recommended_price_inc_vat") or 0)
        unit_ex = _compute_unit_ex_vat(unit_inc, VAT_DEFAULT)
        line_total = round(unit_inc * qty_i, 2)
        total += line_total

        # For normal DB insert (must include unit_price_ex_vat because it's NOT NULL in your schema)
        line_items_for_db.append({
            "product_id": int(p["id"]),
            "product_name_snapshot": p.get("name", ""),
            "qty": qty_i,
            "unit_price_ex_vat": unit_ex,
            "unit_price_inc_vat": round(unit_inc, 2),
            "line_total_inc_vat": line_total,
        })

        # For guest RPC insert (RPC will insert these into order_items too)
        line_items_for_rpc.append({
            "product_id": int(p["id"]),
            "product_name": p.get("name", ""),
            "qty": qty_i,
            "unit_price_ex_vat": unit_ex,
            "unit_price_inc_vat": round(unit_inc, 2),
            "line_total": line_total,
        })

    st.markdown(f"### Total: £{total:.2f}")

    if payment_method == "gift_card":
        st.text_input("Gift card code (processed by staff)")

    is_logged_in = bool(session and session.get("access_token") and session.get("user"))

    if st.button("Place order", use_container_width=True):
        if is_logged_in and customer_row:
            payload = {
                "order_type": order_type,
                "payment_method": payment_method,
                "status": "pending",
                "total_inc_vat": round(total, 2),
                "order_notes": notes.strip() if notes else None,
                "customer_id": int(customer_row["id"]),
                "customer_auth_user_id": session["user"]["id"],
                "customer_email_snapshot": session["user"].get("email"),
                "customer_phone_snapshot": customer_row.get("phone"),
            }
            created = supabase.table("orders").insert(payload).execute()
            if not created:
                st.error("Order could not be created.")
                return
            order = created[0]
            oid = order["id"]

            for li in line_items_for_db:
                supabase.table("order_items").insert({
                    "order_id": oid,
                    "product_id": li["product_id"],
                    "product_name_snapshot": li["product_name_snapshot"],
                    "qty": li["qty"],
                    "unit_price_ex_vat": li["unit_price_ex_vat"],
                    "unit_price_inc_vat": li["unit_price_inc_vat"],
                    "line_total_inc_vat": li["line_total_inc_vat"],
                }).execute()

            clear_cart()
            st.session_state["last_order_code"] = order.get("order_code")
            st.success(f"Order placed! Your order code is: {order.get('order_code', '(code pending)')}")
            st.rerun()

        else:
            result = supabase.rpc("guest_create_order", {
                "p_order_type": order_type,
                "p_payment_method": payment_method,
                "p_total_inc_vat": round(total, 2),
                "p_order_notes": notes.strip() if notes else None,
                "p_items": line_items_for_rpc,
            })
            if not result:
                st.error("Order could not be created.")
                return
            order = result[0] if isinstance(result, list) else result

            clear_cart()
            st.session_state["last_order_code"] = order.get("order_code")
            st.success(f"Order placed! Your order code is: {order.get('order_code', '(code pending)')}")
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
            st.markdown(f"**{code}** — {status}")
            st.caption(STATUS_HELP.get(status, ""))

            items = supabase.table("order_items").select("*").eq("order_id", o["id"]).execute()
            with st.expander("Items"):
                for it in items:
                    st.write(f"{it.get('qty')} × {it.get('product_name_snapshot')}")

            if st.button("Reorder", key=f"reorder_{o['id']}", use_container_width=True):
                new_cart = {}
                for it in items:
                    pid = str(it.get("product_id"))
                    if pid and pid != "None":
                        new_cart[pid] = int(it.get("qty") or 0)
                st.session_state["cart"] = new_cart
                st.success("Items added to cart.")
                st.rerun()

def render_tracking(supabase):
    st.subheader("Order Tracking")
    default_code = st.session_state.get("last_order_code", "")
    code = st.text_input("Enter your order code", value=default_code)
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
        st.error("Order not found. Please check the code.")
        return

    status = order.get("status", "")
    st.markdown(f"### {order.get('order_code','')}")
    st.write(f"Status: **{status}** — {STATUS_HELP.get(status, '')}")
    st.write(f"Type: **{order.get('order_type','')}**")
    if order.get("slot_start"):
        st.write(f"Slot: {order.get('slot_start')} → {order.get('slot_end')}")
    st.write(f"Total: £{float(order.get('total_inc_vat') or 0):.2f}")
