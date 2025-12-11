import streamlit as st
from datetime import datetime, timedelta
from decimal import Decimal

from utils import get_local_now, get_current_customer

DIETARY_FILTERS = {
    "Gluten-free": "gluten_free",
    "Nut-free": "nut_free",
    "Dairy-free": "dairy_free",
    "Vegan": "vegan",
    "Egg-free": "egg_free",
}

def _get_opening_and_slots(supabase):
    slot_rules_res = supabase.table("slot_rules").select("*").limit(1).execute()
    slot_rules = slot_rules_res.data[0] if slot_rules_res.data else {
        "slot_length_minutes": 45,
        "max_orders_per_slot": 2,
        "last_same_day_order_time": "15:00",
        "max_preorder_days": 30,
    }
    opening = supabase.table("opening_hours").select("*").execute().data
    return slot_rules, opening

def _generate_slots_for_date(date_obj, opening_hours, slot_rules):
    weekday = date_obj.weekday()
    db_weekday = (weekday + 1) % 7
    rows = [r for r in opening_hours if r["weekday"] == db_weekday]
    if not rows:
        return []
    row = rows[0]
    if row.get("is_closed"):
        return []
    open_t = row["open_time"]
    close_t = row["close_time"]
    slot_len = slot_rules["slot_length_minutes"]

    slots = []
    current = datetime.combine(date_obj, open_t)
    end_of_day = datetime.combine(date_obj, close_t)
    while current < end_of_day:
        end = current + timedelta(minutes=slot_len)
        if end <= end_of_day:
            slots.append((current, end))
        current = end
    return slots

def _render_menu(supabase):
    st.subheader("Menu")
    st.caption("Browse available items and add them to your order.")

    with st.container():
        col_f1, col_f2 = st.columns([2, 1])
        with col_f1:
            search = st.text_input("Search products", placeholder="Search by name or description...")
        with col_f2:
            st.write("Dietary filters")
            active_filters = []
            cols = st.columns(len(DIETARY_FILTERS))
            for (label, key), col in zip(DIETARY_FILTERS.items(), cols):
                if col.checkbox(label, value=False, key=f"flt_{key}"):
                    active_filters.append(key)

    query = supabase.table("products").select("*").eq("is_active", True)
    if search:
        products = query.execute().data or []
        products = [
            p for p in products
            if search.lower() in (p.get("name", "").lower() + " " + (p.get("description") or "").lower())
        ]
    else:
        products = query.execute().data or []

    if active_filters:
        def matches_flags(p):
            flags = p.get("dietary_flags") or []
            return all(f in flags for f in active_filters)
        products = [p for p in products if matches_flags(p)]

    if not products:
        st.info("No products found. Please adjust filters.")
        return {}

    cart = st.session_state.setdefault("cart", {})

    cols_per_row = 3
    for i in range(0, len(products), cols_per_row):
        row = products[i:i + cols_per_row]
        cols = st.columns(len(row))
        for p, col in zip(row, cols):
            with col:
                with st.container():
                    st.markdown(f"**{p['name']}**")
                    price = p.get("base_price") or 0
                    st.markdown(f"£{price:.2f}")
                    desc = p.get("description") or ""
                    if desc:
                        st.caption(desc)
                    allergens = p.get("allergens") or []
                    if allergens:
                        st.markdown(
                            "<span style='font-size: 0.8rem; color: #555;'>Allergens: "
                            + ", ".join(allergens)
                            + "</span>",
                            unsafe_allow_html=True,
                        )
                    qty = st.number_input("Qty", min_value=0, max_value=50, step=1, key=f"qty_{p['id']}")
                    if qty > 0:
                        cart[p["id"]] = {"product": p, "qty": qty}
                    elif p["id"] in cart:
                        del cart[p["id"]]
    return cart

def render_customer_portal(supabase):
    customer = get_current_customer()
    st.markdown("### Place an Order")

    cart = _render_menu(supabase)

    st.markdown("---")
    st.markdown("### Collection / Delivery")

    now = get_local_now()
    slot_rules, opening_hours = _get_opening_and_slots(supabase)

    max_pre = slot_rules.get("max_preorder_days", 30)
    date_choice = st.date_input(
        "Collection / delivery date",
        value=now.date(),
        min_value=now.date(),
        max_value=now.date() + timedelta(days=max_pre),
    )

    last_cutoff_str = slot_rules.get("last_same_day_order_time") or "15:00"
    cutoff_time = datetime.strptime(last_cutoff_str, "%H:%M").time()
    if date_choice == now.date() and now.time() > cutoff_time:
        st.warning("Same-day orders are closed for today. Please choose another date.")
        allow_today = False
    else:
        allow_today = True

    slots = _generate_slots_for_date(date_choice, opening_hours, slot_rules)
    slot_labels = []
    for start, end in slots:
        label = f"{start.strftime('%H:%M')} - {end.strftime('%H:%M')}"
        slot_labels.append((label, start, end))
    slot_label = None
    if not allow_today and date_choice == now.date():
        st.error("No available slots today.")
    else:
        if slot_labels:
            slot_label = st.selectbox("Available time slots", [l[0] for l in slot_labels])
        else:
            st.error("No slots for this day (closed).")
            return

    st.markdown("### Your details")

    col1, col2 = st.columns(2)
    default_name = customer.get("full_name") if customer else ""
    default_email = customer.get("email") if customer else ""
    default_phone = customer.get("phone") if customer else ""
    with col1:
        name = st.text_input("Name", value=default_name)
        email = st.text_input("Email", value=default_email)
    with col2:
        phone = st.text_input("Phone number", value=default_phone)
        order_type = st.selectbox("Order type", ["Pickup", "Delivery"])

    address = ""
    if order_type == "Delivery":
        address = st.text_area("Delivery address (Wiveliscombe only)")
        st.info("Delivery zone is Wiveliscombe only.")

    order_notes = st.text_area(
        "Order notes (optional)",
        help="Add information such as allergy notes, gift card references or special instructions.",
    )

    tcs = st.checkbox("I accept the terms and conditions")
    with st.expander("View terms and conditions"):
        st.markdown(
            """
### Terms and Conditions – Bakery Online Ordering

These Terms and Conditions govern the use of the online ordering service (the **“Service”**) provided by our bakery (referred to as **“we”**, **“us”**, or **“our”**). By placing an order through this website, you agree to be bound by these Terms and Conditions.

---

#### 1. Orders

1.1. All orders placed through this Service are **requests** and are subject to acceptance and availability.  
1.2. You are responsible for ensuring that all information provided (including contact details, delivery address and order contents) is accurate and complete.  
1.3. Once an order is submitted, we may not be able to make changes; however, you can contact us and we will do our best to help.

---

#### 2. Products, Allergens and Dietary Requirements

2.1. We take care to provide accurate descriptions of our products, including ingredients and allergens where possible.  
2.2. Allergen information is based on our recipes and information from suppliers. **Trace amounts of allergens may still be present** due to shared equipment and preparation areas.  
2.3. If you have a severe allergy or specific dietary requirement, you **must contact us directly** before placing an order so we can advise you.  
2.4. Photographs or images of products are for illustration only and actual products may vary slightly in appearance.

---

#### 3. Pricing and Payment

3.1. All prices shown include VAT where applicable.  
3.2. Prices may change from time to time, but the price confirmed at checkout applies to your order.  
3.3. Payment methods offered may include:
- Cash on collection or delivery  
- Card payment on collection or delivery  
- Gift card or voucher (where accepted by us)

3.4. If there is an obvious pricing error, we reserve the right to cancel the order or contact you to agree a revised price.

---

#### 4. Collection and Delivery

4.1. Collection and delivery slots are offered on a first-come, first-served basis.  
4.2. We will do our best to honour your chosen time slot, but it is an estimate and not a guarantee.  
4.3. Delivery is currently available **only within our specified delivery area (Wiveliscombe)**. If you provide an address outside this area, we may cancel or amend your order.  
4.4. You are responsible for ensuring someone is available to receive the delivery at the agreed time. If no one is available and we cannot contact you, your order may be returned to the bakery and may not be eligible for a refund.

---

#### 5. Cancellations and Changes

5.1. If you need to cancel or amend your order, please contact us as soon as possible.  
5.2. For same-day orders or short-notice orders, we may have already started preparing your items and may not be able to cancel or refund.  
5.3. We reserve the right to cancel an order if:
- We are unable to fulfil it due to stock or staffing issues  
- There is a technical or pricing error  
- We believe the order is fraudulent or inappropriate  

If we cancel your order, we will notify you using the contact details you provided and, where payment has been made, issue a refund where appropriate.

---

#### 6. Quality, Issues and Refunds

6.1. We aim to provide products of high quality and prepared with care.  
6.2. If you are unhappy with any part of your order, please contact us **on the same day** where possible, providing details and, if applicable, photos of the issue.  
6.3. Any refunds, replacements or goodwill gestures are at our discretion.

---

#### 7. Gift Cards and Discount Codes

7.1. Gift cards or vouchers may be subject to their own terms, including expiry dates and usage limits.  
7.2. Discount or promo codes must be entered at the time of ordering and cannot normally be applied after an order is placed.  
7.3. We reserve the right to withdraw or change discount codes at any time.

---

#### 8. Use of the Service

8.1. You must not use this Service for any unlawful purpose or to cause disruption or harm.  
8.2. We may suspend or restrict the Service at any time for maintenance, security or operational reasons.

---

#### 9. Data Protection and Privacy

9.1. We will process your personal data in accordance with our Privacy Policy and applicable data protection laws.  
9.2. Your details are used to manage your orders, provide customer support and, where you have opted in, send you marketing communications.  
9.3. You can update your marketing preferences in your account or by contacting us.

---

#### 10. Changes to These Terms

10.1. We may update these Terms and Conditions from time to time. The version displayed on this page at the time you place an order will apply to that order.

---

If you have any questions about these Terms and Conditions, please contact us before placing your order.
"""
        )
    marketing = st.checkbox("I agree to receive marketing emails (optional)")
    payment_method = st.selectbox(
        "Payment method", ["Cash on delivery/collection", "Card on delivery/collection", "Gift card"]
    )

    st.markdown("---")
    col_left, col_right = st.columns([2, 1])
    if cart:
        subtotal = sum(
            Decimal(str(item["product"].get("base_price") or 0)) * item["qty"]
            for item in cart.values()
        )
    else:
        subtotal = Decimal("0")
    vat_rate = Decimal("20.0")
    vat_total = (subtotal * vat_rate / Decimal("100")).quantize(Decimal("0.01"))
    total_inc_vat = (subtotal + vat_total).quantize(Decimal("0.01"))

    with col_left:
        st.markdown(f"**Subtotal (ex VAT):** £{subtotal:.2f}")
        st.markdown(f"**VAT (20%):** £{vat_total:.2f}")
        st.markdown(f"**Total to pay:** £{total_inc_vat:.2f}")
    with col_right:
        place_order = st.button("Place order", type="primary", use_container_width=True)

    if place_order:
        if not cart:
            st.error("Your cart is empty.")
            return
        if not tcs:
            st.error("You must accept the terms and conditions.")
            return

        selected_slot = next((s for s in slot_labels if s[0] == slot_label), None)
        if not selected_slot:
            st.error("Please choose a valid slot.")
            return

        customer_id = customer.get("id") if customer else None
        is_guest = customer_id is None

        import random
        order_code = f"ORD-{random.randint(100000, 999999)}"

        order_payload = {
            "order_code": order_code,
            "customer_id": customer_id,
            "is_guest": is_guest,
            "status": "pending",
            "order_type": "pickup" if order_type == "Pickup" else "delivery",
            "channel": "online",
            "slot_start": selected_slot[1].isoformat(),
            "slot_end": selected_slot[2].isoformat(),
            "subtotal_ex_vat": float(subtotal),
            "discount_total": 0.0,
            "vat_total": float(vat_total),
            "total_inc_vat": float(total_inc_vat),
            "payment_method": "cash"
            if payment_method.startswith("Cash")
            else "card"
            if "Card" in payment_method
            else "gift_card",
            "customer_notes": order_notes,
        }

        order_res = supabase.table("orders").insert(order_payload).execute()
        order = order_res.data[0]

        items_payload = []
        for entry in cart.values():
            p = entry["product"]
            qty = entry["qty"]
            unit_price_ex_vat = Decimal(str(p.get("base_price") or 0))
            line_total_ex = unit_price_ex_vat * qty
            line_vat = (line_total_ex * vat_rate / Decimal("100")).quantize(Decimal("0.01"))
            line_inc = line_total_ex + line_vat
            items_payload.append(
                {
                    "order_id": order["id"],
                    "product_id": p["id"],
                    "product_name_snapshot": p["name"],
                    "qty": qty,
                    "unit_price_ex_vat": float(unit_price_ex_vat),
                    "vat_rate": float(vat_rate),
                    "line_total_ex_vat": float(line_total_ex),
                    "line_vat": float(line_vat),
                    "line_total_inc_vat": float(line_inc),
                }
            )

        supabase.table("order_items").insert(items_payload).execute()
        st.success(f"Order placed! Your order number is {order_code}")
        st.session_state["cart"] = {}

def render_order_tracking(supabase):
    st.subheader("Track your order")
    code = st.text_input("Order number (e.g. ORD-123456)")
    if st.button("Check status"):
        res = supabase.table("orders").select("*").eq("order_code", code).execute()
        if not res.data:
            st.error("Order not found.")
            return
        order = res.data[0]
        st.write(f"**Status:** {order['status'].title()}")
        st.write(f"**Total:** £{order['total_inc_vat']:.2f}")
        st.write(f"**Type:** {order['order_type']}")
        st.write(f"**Slot:** {order['slot_start']} → {order['slot_end']}")
