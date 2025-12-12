import streamlit as st
from ui_text import TERMS_AND_CONDITIONS, STATUS_HELP

# -----------------------
# Helpers
# -----------------------

def _cart():
    return st.session_state.setdefault("cart", {})

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

# -----------------------
# Terms
# -----------------------

def render_terms_checkbox(key="terms_ok"):
    st.markdown(TERMS_AND_CONDITIONS)
    return st.checkbox("I agree to the Terms & Conditions", key=key)

# -----------------------
# Menu
# -----------------------

def render_menu(supabase, customer_row=None):
    st.subheader("Menu")

    q = st.text_input("Search", placeholder="Search items...")
    query = supabase.table("products").select("*").eq("is_active", True).order("name")

    if q.strip():
        query = query.ilike("name", f"*{q.strip()}*")

    products = query.execute()
    allergies = customer_row.get("allergies") if customer_row else None
    products = _hide_allergenic_products(products, allergies)

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
                price = float(p.get("recommended_price_inc_vat") or 0)
                st.markdown(f"**£{price:.2f}**")
                qty = st.number_input(
                    "Qty",
                    min_value=0,
                    max_value=50,
                    value=int(cart.get(pid, 0)),
                    key=f"qty_{pid}",
                )
                if qty > 0:
                    cart[pid] = qty
                else:
                    cart.pop(pid, None)

    st.session_state["cart"] = cart

# -----------------------
# Cart Sidebar
# -----------------------

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
            line = price * qty
            total += line
            st.write(f"{qty} × {p['name']} — £{line:.2f}")

        st.markdown(f"### Total: £{total:.2f}")

        if st.button("Clear cart", use_container_width=True):
            clear_cart()
            st.rerun()

# -----------------------
# My Orders
# -----------------------

def render_my_orders(supabase, session):
    st.subheader("My Orders")

    uid = session["user"]["id"]
    orders = (
        supabase.table("orders")
        .select("*")
        .eq("customer_auth_user_id", uid)
        .order("created_at", desc=True)
        .execute()
    )

    if not orders:
        st.info("No orders yet.")
        return

    for o in orders:
        with st.container(border=True):
            code = o.get("order_code", "Order")
            status = o.get("status", "")
            st.markdown(f"**{code}** — {status}")
            st.caption(STATUS_HELP.get(status, ""))

            with st.expander("Items"):
                items = supabase.table("order_items").select("*").eq("order_id", o["id"]).execute()
                for it in items:
                    st.write(f"{it.get('qty')} × {it.get('product_name_snapshot')}")

            if st.button("Reorder", key=f"reorder_{o['id']}"):
                cart = {}
                for it in items:
                    cart[str(it["product_id"])] = int(it["qty"])
                st.session_state["cart"] = cart
                st.success("Items added to cart")
                st.rerun()

# -----------------------
# Order Tracking
# -----------------------

def render_tracking(supabase):
    st.subheader("Order Tracking")

    code = st.text_input("Order code")
    if not code.strip():
        return

    try:
        result = supabase.rpc("track_order_by_code", {"p_order_code": code.strip()})
    except Exception:
        result = None

    if not result:
        st.error("Order not found")
        return

    o = result[0] if isinstance(result, list) else result
    st.markdown(f"### {o['order_code']}")
    st.write(f"Status: **{o['status']}**")
    st.write(f"Type: {o['order_type']}")
    st.write(f"Total: £{float(o['total_inc_vat']):.2f}")
