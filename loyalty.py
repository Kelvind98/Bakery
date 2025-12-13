import streamlit as st
from supabase_client import get_client

# Simple “offers” ladder (edit any time)
OFFERS = [
    {"points": 100, "title": "£2 off your next order"},
    {"points": 250, "title": "Free cookie / small treat"},
    {"points": 500, "title": "£10 off a celebration cake"},
]


def page_loyalty():
    st.header("🎁 Loyalty")

    sb = get_client()

    # Must be logged in
    try:
        user = sb.auth.get_user().user
    except Exception:
        user = None

    if not user:
        st.info("Log in to view your loyalty points and offers.")
        return

    uid = getattr(user, "id", None)

    # ✅ If profile missing, create it automatically (no need to place an order)
    try:
        sb.rpc(
            "ensure_customer_profile",
            {
                "p_full_name": None,
                "p_phone": None,
                "p_marketing_consent": False,
            },
        ).execute()
    except Exception:
        # If this fails, we'll still try to read what exists
        pass

    # Now fetch your customer row
    cust_rows = (
        sb.table("customers")
        .select("id, full_name")
        .eq("auth_user_id", uid)
        .limit(1)
        .execute()
        .data
    )
    if not cust_rows:
        st.error(
            "You're logged in, but the customer profile still isn't visible. "
            "This usually means the auth session isn't being restored correctly."
        )
        st.caption("Fix: update supabase_client.py so get_client() restores session tokens.")
        return

    customer_id = cust_rows[0]["id"]

    acct_rows = (
        sb.table("loyalty_accounts")
        .select("points_balance,lifetime_points,tier")
        .eq("customer_id", customer_id)
        .limit(1)
        .execute()
        .data
    )
    acct = acct_rows[0] if acct_rows else {"points_balance": 0, "lifetime_points": 0, "tier": None}

    points = int(acct.get("points_balance") or 0)
    lifetime = int(acct.get("lifetime_points") or 0)
    tier = acct.get("tier") or "—"

    c1, c2, c3 = st.columns(3)
    c1.metric("Current points", points)
    c2.metric("Lifetime points", lifetime)
    c3.metric("Tier", tier)

    st.divider()
    st.subheader("Offers you can unlock")

    next_offer = None
    for o in OFFERS:
        if points < o["points"]:
            next_offer = o
            break

    if next_offer:
        st.progress(min(1.0, points / next_offer["points"]))
        st.caption(f"You're **{next_offer['points'] - points}** points away from: **{next_offer['title']}**")
    else:
        st.success("You've unlocked all current offers 🎉")

    for o in OFFERS:
        unlocked = points >= o["points"]
        with st.container(border=True):
            st.write(f"**{o['title']}**")
            st.write(f"Required: **{o['points']}** points")
            if unlocked:
                st.success("Unlocked")

