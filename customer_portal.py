import streamlit as st
from datetime import datetime, date, timedelta, time

DELIVERY_TOWN = "Wiveliscombe"
SLOT_MINUTES = 45
MAX_PER_SLOT = 2
CLOSED_WEEKDAY = 6
NO_SAME_DAY_AFTER = time(15, 0)

def _filter_products_by_allergies(products, allergies):
    if not allergies:
        return products
    allergies = set([a.lower() for a in allergies])
    filtered = []
    for p in products:
        prod_allergens = p.get("allergens") or []
        prod_allergens = set([str(a).lower() for a in prod_allergens])
        if allergies.intersection(prod_allergens):
            continue
        filtered.append(p)
    return filtered

def _parse_time(val):
    if val is None:
        return None
    if isinstance(val, str):
        parts = val.split(":")
        if len(parts) >= 2:
            return time(int(parts[0]), int(parts[1]))
    return None

def _get_opening_hours(supabase):
    r = supabase.select("opening_hours", select="weekday,open_time,close_time,is_closed", params={"order": "weekday.asc"})
    return r.json() if r.ok else []

def _get_slot_rules(supabase):
    r = supabase.select("slot_rules", select="slot_length_minutes,max_orders_per_slot,last_same_day_order_time,max_preorder_days", params={"limit": 1})
    return (r.json()[0] if r.ok and r.json() else None)

def _generate_slots_for_date(day: date, opening_hours_rows, rules):
    slot_len = int((rules or {}).get("slot_length_minutes") or SLOT_MINUTES)
    max_per = int((rules or {}).get("max_orders_per_slot") or MAX_PER_SLOT)
    last_same_day = (rules or {}).get("last_same_day_order_time")
    max_days = int((rules or {}).get("max_preorder_days") or 14)

    if day.weekday() == CLOSED_WEEKDAY:
        return []

    row = next((x for x in opening_hours_rows if int(x.get("weekday")) == day.weekday()), None)
    if not row or row.get("is_closed"):
        return []

    open_t = _parse_time(row.get("open_time"))
    close_t = _parse_time(row.get("close_time"))
    if not open_t or not close_t:
        return []

    now = datetime.now()
    if day == now.date():
        cutoff = _parse_time(last_same_day) if last_same_day else NO_SAME_DAY_AFTER
        if now.time() >= cutoff:
            return []

    if day > (now.date() + timedelta(days=max_days)):
        return []

    slots = []
    cur = datetime.combine(day, open_t)
    end = datetime.combine(day, close_t)
    while cur + timedelta(minutes=slot_len) <= end:
        slots.append((cur, cur + timedelta(minutes=slot_len), max_per))
        cur += timedelta(minutes=slot_len)
    return slots

def render_menu_and_checkout(supabase, customer_row):
    st.subheader("Menu")

    pr = supabase.select("products", select="id,name,description,recommended_price_inc_vat,base_price,is_active,allergens,dietary_flags", params={"is_active": "eq.true", "order": "name.asc"})
    products = pr.json() if pr.ok else []
    allergies = (customer_row.get("allergies") if customer_row else []) or []
    products = _filter_products_by_allergies(products, allergies)

    if "cart" not in st.session_state:
        st.session_state["cart"] = {}

    if not products:
        st.info("No products available right now.")
        return

    colL, colR = st.columns([3, 2])

    with colL:
        for p in products:
            with st.container(border=True):
                c1, c2 = st.columns([4, 1])
                with c1:
                    st.markdown(f"**{p.get('name','')}**")
                    if p.get("description"):
                        st.caption(p["description"])
                    flags = p.get("dietary_flags") or []
                    allergens_p = p.get("allergens") or []
                    if flags:
                        st.caption("Dietary: " + ", ".join(flags))
                    if allergens_p:
                        st.caption("Allergens: " + ", ".join(allergens_p))
                with c2:
                    price = p.get("recommended_price_inc_vat") or p.get("base_price") or 0
                    st.markdown(f"**£{float(price):.2f}**")
                    pid = str(p["id"])
                    qty = st.session_state["cart"].get(pid, 0)
                    if st.button("Add", key=f"add_{pid}", use_container_width=True):
                        st.session_state["cart"][pid] = qty + 1
                        st.rerun()
                    if qty > 0 and st.button("Remove", key=f"rem_{pid}", use_container_width=True):
                        st.session_state["cart"][pid] = max(0, qty - 1)
                        if st.session_state["cart"][pid] == 0:
                            st.session_state["cart"].pop(pid, None)
                        st.rerun()

    with colR:
        st.subheader("Checkout")
        if not st.session_state["cart"]:
            st.info("Your cart is empty.")
            return

        id_to_product = {str(p["id"]): p for p in products}
        total = 0.0
        for pid, qty in st.session_state["cart"].items():
            p = id_to_product.get(pid)
            if not p:
                continue
            unit = float(p.get("recommended_price_inc_vat") or p.get("base_price") or 0)
            total += unit * qty
            st.write(f"{qty} × {p.get('name')} — £{unit*qty:.2f}")
        st.markdown(f"### Total: £{total:.2f}")

        order_type = st.radio("Pickup or delivery?", ["pickup", "delivery"], horizontal=True, key="order_type")
        payment_method = st.selectbox("Payment method", ["cash", "card", "gift_card"], key="payment_method")
        notes = st.text_area("Order notes (optional)", key="order_notes", height=80)

        opening_hours = _get_opening_hours(supabase)
        rules = _get_slot_rules(supabase)

        date_choice = st.date_input("Date", value=datetime.now().date(), key="slot_date")
        slots = _generate_slots_for_date(date_choice, opening_hours, rules)
        if not slots:
            st.warning("No slots available for this date.")
            return

        slot_labels = []
        slot_map = {}
        for s, e, cap in slots:
            label = f"{s.strftime('%H:%M')} - {e.strftime('%H:%M')}"
            slot_labels.append(label)
            slot_map[label] = (s, e, cap)

        slot_pick = st.selectbox("Time slot", slot_labels, key="slot_pick")
        slot_start, slot_end, cap = slot_map[slot_pick]

        tc = st.checkbox("I agree to the Terms & Conditions", key="tc_order")
        mk = st.checkbox("Marketing (optional)", key="mk_order")

        if not customer_row:
            st.info("Guest checkout: please provide your details.")
            g_name = st.text_input("Full name", key="g_name")
            g_email = st.text_input("Email", key="g_email")
            g_phone = st.text_input("Phone", key="g_phone")
            g_addr1 = st.text_input("Address line 1", key="g_addr1")
            g_post = st.text_input("Postcode", key="g_post")
        else:
            g_name = customer_row.get("full_name")
            g_email = customer_row.get("email")
            g_phone = customer_row.get("phone")
            g_addr1 = customer_row.get("address_line1")
            g_post = customer_row.get("postcode")
            if mk != bool(customer_row.get("marketing_opt_in", False)):
                supabase.update("customers", {"marketing_opt_in": bool(mk)}, params={"id": f"eq.{customer_row['id']}"})

        if st.button("Place order", type="primary", use_container_width=True):
            if not tc:
                st.error("You must accept Terms & Conditions.")
                return
            if not g_name or not g_phone or not g_email:
                st.error("Please provide name, email and phone.")
                return
            if order_type == "delivery" and (not g_addr1 or not g_post):
                st.error("Delivery requires address line 1 and postcode.")
                return

            order_payload = {
                "status": "pending",
                "order_type": order_type,
                "slot_start": slot_start.isoformat(),
                "slot_end": slot_end.isoformat(),
                "payment_method": payment_method,
                "order_notes": notes,
                "customer_email_snapshot": g_email,
                "customer_phone_snapshot": g_phone,
                "delivery_address_snapshot": f"{g_addr1}, {DELIVERY_TOWN}, {g_post}" if order_type == "delivery" else "",
                "total_inc_vat": total,
            }
            if customer_row:
                order_payload["customer_id"] = customer_row["id"]

            created = supabase.insert("orders", order_payload)
            if not created.ok:
                st.error(created.text)
                return
            created_rows = created.json() or []
            order_row = created_rows[0] if created_rows else None
            if not order_row:
                st.success("Order placed. Use Track Order to check status.")
                st.session_state["cart"] = {}
                return

            order_id = order_row["id"]
            order_code = order_row.get("order_code")

            items_payload = []
            for pid, qty in st.session_state["cart"].items():
                p = id_to_product.get(pid)
                if not p:
                    continue
                unit = float(p.get("recommended_price_inc_vat") or p.get("base_price") or 0)
                items_payload.append({
                    "order_id": order_id,
                    "product_id": int(pid),
                    "product_name_snapshot": p.get("name"),
                    "qty": qty,
                    "unit_price_inc_vat": unit,
                    "line_total_inc_vat": unit * qty
                })

            ir = supabase.insert("order_items", items_payload)
            if not ir.ok:
                st.error(f"Order created but items failed: {ir.text}")
                return

            st.session_state["cart"] = {}
            st.success(f"✅ Order placed! Your order code is: **{order_code}**")

def render_order_tracking(supabase, customer_row):
    st.subheader("Track your order")

    if customer_row and "id" in customer_row:
        r = supabase.select("orders", select="id,order_code,status,slot_start,order_type,total_inc_vat", params={
            "customer_id": f"eq.{customer_row['id']}",
            "order": "id.desc",
            "limit": 10
        })
        if r.ok and r.json():
            st.caption("Your recent orders")
            for o in r.json():
                st.write(f"**{o.get('order_code')}** — {o.get('status')} — {o.get('order_type')} — {o.get('slot_start')}")
        else:
            st.info("No recent orders found.")

    st.divider()
    code = st.text_input("Enter order code", key="track_code")
    if st.button("Track", use_container_width=True, key="btn_track"):
        if not code:
            st.error("Enter an order code.")
            return
        rr = supabase.rpc("track_order_by_code", {"p_order_code": code})
        if rr.ok and rr.json():
            o = rr.json()[0] if isinstance(rr.json(), list) else rr.json()
            st.success(f"Status: **{o.get('status','')}**")
            st.write(f"Order type: {o.get('order_type','')}")
            st.write(f"Slot: {o.get('slot_start','')} to {o.get('slot_end','')}")
            st.write(f"Total: £{float(o.get('total_inc_vat') or 0):.2f}")
        else:
            r = supabase.select("orders", select="order_code,status,slot_start,slot_end,order_type,total_inc_vat", params={
                "order_code": f"eq.{code}",
                "limit": 1
            })
            if r.ok and r.json():
                o = r.json()[0]
                st.success(f"Status: **{o.get('status','')}**")
                st.write(f"Order type: {o.get('order_type','')}")
                st.write(f"Slot: {o.get('slot_start','')} to {o.get('slot_end','')}")
                st.write(f"Total: £{float(o.get('total_inc_vat') or 0):.2f}")
            else:
                st.error("Order not found (check the code).")
