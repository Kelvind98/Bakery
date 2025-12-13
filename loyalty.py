import streamlit as st
from supabase_client import get_client

REWARDS = [
    {"points": 100, "type": "fixed", "amount": 2.00, "title": "£2 off"},
    {"points": 250, "type": "fixed", "amount": 5.00, "title": "£5 off"},
    {"points": 500, "type": "fixed", "amount": 10.00, "title": "£10 off cake"},
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
        st.info("Log in to view your loyalty points and redeem rewards.")
        return

    uid = user.id

    # Ensure customer profile exists
    try:
        sb.rpc(
            "ensure_customer_profile",
            {"p_full_name": None, "p_phone": None, "p_marketing_consent": False},
        ).execute()
    except Exception:
        pass

    cust = (
        sb.table("customers")
        .select("id,full_name,email")
        .eq("auth_user_id", uid)
        .limit(1)
        .execute()
        .data
    )
    if not cust:
        st.error("You're logged in, but your customer profile isn't visible yet.")
        st.caption("Fix: ensure supabase_client.py restores session tokens in get_client().")
        return

    customer_id = cust[0]["id"]

    acct = (
        sb.table("loyalty_accounts")
        .select("points_balance,lifetime_points,tier")
        .eq("customer_id", customer_id)
        .limit(1)
        .execute()
        .data
    )
    acct = acct[0] if acct else {"points_balance": 0, "lifetime_points": 0, "tier": None}

    points = int(acct.get("points_balance") or 0)
    lifetime = int(acct.get("lifetime_points") or 0)
    tier = acct.get("tier") or "—"

    # Header stats
    c1, c2, c3 = st.columns(3)
    c1.metric("Current points", points)
    c2.metric("Lifetime points", lifetime)
    c3.metric("Tier", tier)

    # Next reward progress
    st.divider()
    st.subheader("Progress to your next reward")

    next_reward = None
    for r in REWARDS:
        if points < r["points"]:
            next_reward = r
            break

    if next_reward:
        st.progress(min(1.0, points / next_reward["points"]))
        st.caption(
            f"You're **{next_reward['points'] - points}** points away from **{next_reward['title']}**."
        )
    else:
        st.success("You've unlocked all current rewards 🎉")

    # Show last generated code nicely
    last_code = st.session_state.get("last_reward_code")
    last_valid = st.session_state.get("last_reward_validity")
    if last_code:
        st.success("Reward code generated ✅")
        st.text_input("Your code (tap to copy)", value=last_code, disabled=False)
        if last_valid:
            st.caption(last_valid)
        st.info("Enter this code at Checkout in the Promo code box.")

    st.divider()
    st.subheader("Redeem points for a single-use code")

    for r in REWARDS:
        unlocked = points >= r["points"]
        with st.container(border=True):
            left, right = st.columns([3, 1])
            with left:
                st.write(f"**{r['title']}**")
                st.caption(f"Costs **{r['points']} points** • Generates a **single-use** code valid for 30 days")
            with right:
                st.write("✅ Unlocked" if unlocked else "🔒 Locked")
                if st.button("Redeem", disabled=not unlocked, key=f"redeem_{r['points']}"):
                    try:
                        resp = sb.rpc(
                            "redeem_loyalty_discount",
                            {
                                "p_points_required": r["points"],
                                "p_discount_type": r["type"],
                                "p_amount": r["amount"],
                                "p_valid_days": 30,
                                "p_min_order_value": None,
                                "p_title": f"Loyalty reward: {r['title']}",
                            },
                        ).execute()
                        data = resp.data or {}
                        st.session_state.last_reward_code = data.get("code")
                        st.session_state.last_reward_validity = f"Valid until: {data.get('valid_to')}"
                        st.rerun()
                    except Exception as e:
                        st.error("Could not redeem points.")
                        st.exception(e)

    st.divider()
    st.subheader("Recent activity")
    try:
        tx = (
            sb.table("loyalty_transactions")
            .select("created_at,points_change,reason,order_id")
            .eq("customer_id", customer_id)
            .order("created_at", desc=True)
            .limit(20)
            .execute()
            .data
        ) or []
    except Exception:
        tx = []

    if not tx:
        st.caption("No activity yet.")
    else:
        for t in tx:
            pts = int(t.get("points_change") or 0)
            sign = "+" if pts > 0 else ""
            st.write(f"- {t.get('created_at','')}: **{sign}{pts}** pts • {t.get('reason','')} • Order: {t.get('order_id')}")
