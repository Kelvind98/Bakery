import streamlit as st
from supabase_client import get_client

REWARDS = [
    # points, type, amount, title
    {"points": 100, "type": "fixed", "amount": 2.00, "title": "£2 off"},
    {"points": 250, "type": "fixed", "amount": 5.00, "title": "£5 off"},
    {"points": 500, "type": "fixed", "amount": 10.00, "title": "£10 off cake"},
]

def page_loyalty():
    st.header("🎁 Loyalty")
    sb = get_client()

    # must be logged in
    try:
        user = sb.auth.get_user().user
    except Exception:
        user = None

    if not user:
        st.info("Log in to view your loyalty points and redeem rewards.")
        return

    uid = user.id

    # Make sure customer profile exists
    try:
        sb.rpc("ensure_customer_profile", {"p_full_name": None, "p_phone": None, "p_marketing_consent": False}).execute()
    except Exception:
        pass

    cust = sb.table("customers").select("id").eq("auth_user_id", uid).limit(1).execute().data
    if not cust:
        st.error("Profile not found (session issue). If this keeps happening, your supabase_client.py session restore needs updating.")
        return
    customer_id = cust[0]["id"]

    acct = sb.table("loyalty_accounts").select("points_balance,lifetime_points,tier").eq("customer_id", customer_id).limit(1).execute().data
    acct = acct[0] if acct else {"points_balance": 0, "lifetime_points": 0, "tier": None}

    points = int(acct.get("points_balance") or 0)
    lifetime = int(acct.get("lifetime_points") or 0)
    tier = acct.get("tier") or "—"

    c1, c2, c3 = st.columns(3)
    c1.metric("Current points", points)
    c2.metric("Lifetime points", lifetime)
    c3.metric("Tier", tier)

    st.divider()
    st.subheader("Redeem points for a code")

    # show last generated code this session
    if st.session_state.get("last_reward_code"):
        st.success(f"Your code: **{st.session_state.last_reward_code}** (enter this at checkout)")
        st.caption(st.session_state.get("last_reward_validity",""))

    for r in REWARDS:
        unlocked = points >= r["points"]
        with st.container(border=True):
            st.write(f"**{r['title']}**")
            st.write(f"Costs: **{r['points']} points**")
            st.write(f"Generates: **{('£' if r['type']=='fixed' else '')}{r['amount']} {'off' if r['type']=='fixed' else '% off'}** (single-use)")

            if st.button("Redeem", disabled=not unlocked, key=f"redeem_{r['points']}"):
                try:
                    resp = sb.rpc("redeem_loyalty_discount", {
                        "p_points_required": r["points"],
                        "p_discount_type": r["type"],
                        "p_amount": r["amount"],
                        "p_valid_days": 30,
                        "p_min_order_value": None,
                        "p_title": f"Loyalty reward: {r['title']}"
                    }).execute()
                    data = resp.data or {}
                    code = data.get("code")
                    st.session_state.last_reward_code = code
                    st.session_state.last_reward_validity = f"Valid until: {data.get('valid_to')}"
                    st.rerun()
                except Exception as e:
                    st.error("Could not redeem points.")
                    st.exception(e)

    st.divider()
    st.subheader("Your recent point activity")
    try:
        tx = (
            sb.table("loyalty_transactions")
            .select("created_at,points_change,reason,order_id")
            .eq("customer_id", customer_id)
            .order("created_at", desc=True)
            .limit(20)
            .execute().data
        ) or []
    except Exception:
        tx = []

    if not tx:
        st.caption("No activity yet.")
    else:
        for t in tx:
            st.write(f"- {t.get('created_at','')}: {t.get('points_change')} pts ({t.get('reason','')})")

