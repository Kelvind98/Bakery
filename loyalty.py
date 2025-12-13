import streamlit as st
from supabase_client import get_client

# Simple “offers” ladder (you can change these anytime)
OFFERS = [
    {"points": 100, "title": "£2 off your next order", "notes": "Reward voucher applied by staff/admin later."},
    {"points": 250, "title": "Free cookie / small treat", "notes": "Ask in-store when collecting."},
    {"points": 500, "title": "£10 off a celebration cake", "notes": "Valid on custom cakes (subject to availability)."},
]

def _get_user(sb):
    try:
        return sb.auth.get_user().user
    except Exception:
        return None

def page_loyalty():
    st.header("🎁 Loyalty")

    sb = get_client()
    user = _get_user(sb)
    if not user:
        st.info("Log in to view your loyalty points and offers.")
        return

    uid = getattr(user, "id", None)
    email = getattr(user, "email", "")

    # Find the customer row by auth_user_id
    cust = sb.table("customers").select("id, full_name, email").eq("auth_user_id", uid).limit(1).execute().data
    cust = cust[0] if cust else None

    if not cust:
        st.warning("We couldn't find your customer profile yet. Place an order once while logged in, then come back.")
        return

    customer_id = cust["id"]

    acct = sb.table("loyalty_accounts").select("points_balance,lifetime_points,tier").eq("customer_id", customer_id).limit(1).execute().data
    acct = acct[0] if acct else {"points_balance": 0, "lifetime_points": 0, "tier": None}

    points = int(acct.get("points_balance") or 0)
    lifetime = int(acct.get("lifetime_points") or 0)
    tier = acct.get("tier") or "—"

    st.subheader("Your points")
    c1, c2, c3 = st.columns(3)
    c1.metric("Current points", points)
    c2.metric("Lifetime points", lifetime)
    c3.metric("Tier", tier)

    st.divider()
    st.subheader("Offers you can unlock")

    # Find next offer progress
    next_offer = None
    for o in OFFERS:
        if points < o["points"]:
            next_offer = o
            break

    if next_offer:
        needed = next_offer["points"] - points
        st.progress(min(1.0, points / next_offer["points"]))
        st.caption(f"You're **{needed}** points away from: **{next_offer['title']}**")
    else:
        st.success("You've unlocked all current offers 🎉")

    for o in OFFERS:
        unlocked = points >= o["points"]
        with st.container(border=True):
            st.write(f"**{o['title']}**")
            st.write(f"Required: **{o['points']}** points")
            st.write(o.get("notes",""))
            if unlocked:
                st.success("Unlocked")

    st.divider()
    st.subheader("Current promotions")
    # Show active discount codes (not tied to points, just useful for customers)
    try:
        discounts = sb.table("discounts").select("code,name,description,discount_type,amount,valid_from,valid_to,is_active").eq("is_active", True).execute().data or []
    except Exception:
        discounts = []

    if not discounts:
        st.caption("No promotions listed right now.")
    else:
        for d in discounts:
            with st.container(border=True):
                title = d.get("name") or d.get("code")
                st.write(f"**{title}** — code: `{d.get('code','')}`")
                if d.get("description"):
                    st.write(d["description"])
                st.caption(f"Type: {d.get('discount_type')} • Amount: {d.get('amount')}")
