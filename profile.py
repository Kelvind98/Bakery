import streamlit as st

ALLERGY_OPTIONS = ["gluten", "nuts", "dairy", "eggs", "soy", "sesame"]

def ensure_customer_profile(supabase, session_dict):
    user = session_dict.get("user") or {}
    auth_user_id = user.get("id")
    email = user.get("email")

    if not auth_user_id:
        return None

    r = supabase.select("customers", select="*", params={"auth_user_id": f"eq.{auth_user_id}", "limit": 1})
    if r.ok and r.json():
        return r.json()[0]

    r2 = supabase.select("customers", select="*", params={"email": f"eq.{email}", "auth_user_id": "is.null", "limit": 1})
    if r2.ok and r2.json():
        row = r2.json()[0]
        upd = supabase.update("customers", {"auth_user_id": auth_user_id}, params={"id": f"eq.{row['id']}"})
        if upd.ok and upd.json():
            return upd.json()[0]

    marketing_opt_in = bool(st.session_state.get("pending_marketing_opt_in", False))
    created = supabase.insert("customers", {"auth_user_id": auth_user_id, "email": email, "marketing_opt_in": marketing_opt_in})
    if created.ok and created.json():
        return created.json()[0]
    st.error("Could not create customer profile.")
    return None

def require_profile_completion(supabase, customer_row):
    if not customer_row:
        return None

    required = ["full_name", "phone", "address_line1", "postcode"]
    missing = [k for k in required if not customer_row.get(k)]

    if missing:
        st.warning("Please complete your details to place orders.")
        with st.form("complete_profile"):
            st.subheader("Your details")
            full_name = st.text_input("Full name", value=customer_row.get("full_name",""))
            phone = st.text_input("Phone", value=customer_row.get("phone",""))

            st.subheader("Delivery address (Wiveliscombe)")
            addr1 = st.text_input("Address line 1", value=customer_row.get("address_line1",""))
            addr2 = st.text_input("Address line 2", value=customer_row.get("address_line2",""))
            town = st.text_input("Town", value=customer_row.get("town","Wiveliscombe"))
            postcode = st.text_input("Postcode", value=customer_row.get("postcode",""))

            st.subheader("Allergies")
            allergies = st.multiselect(
                "Select any allergies (we will hide items that contain them)",
                ALLERGY_OPTIONS,
                default=customer_row.get("allergies") or []
            )

            save = st.form_submit_button("Save & continue", use_container_width=True)

        if save:
            payload = {
                "full_name": full_name.strip(),
                "phone": phone.strip(),
                "address_line1": addr1.strip(),
                "address_line2": addr2.strip(),
                "town": town.strip(),
                "postcode": postcode.strip(),
                "allergies": allergies,
            }
            upd = supabase.update("customers", payload, params={"id": f"eq.{customer_row['id']}"})
            if upd.ok and upd.json():
                st.success("Saved")
                st.rerun()
            st.error(upd.text)

        st.stop()

    return customer_row

def render_account_settings(supabase, customer_row):
    st.subheader("Account settings")
    if not customer_row:
        st.info("No profile loaded.")
        return

    with st.form("account_update"):
        full_name = st.text_input("Full name", value=customer_row.get("full_name",""))
        phone = st.text_input("Phone", value=customer_row.get("phone",""))
        addr1 = st.text_input("Address line 1", value=customer_row.get("address_line1",""))
        addr2 = st.text_input("Address line 2", value=customer_row.get("address_line2",""))
        town = st.text_input("Town", value=customer_row.get("town","Wiveliscombe"))
        postcode = st.text_input("Postcode", value=customer_row.get("postcode",""))
        allergies = st.multiselect("Allergies", ALLERGY_OPTIONS, default=customer_row.get("allergies") or [])
        marketing = st.checkbox("Marketing opt‑in", value=bool(customer_row.get("marketing_opt_in", False)))
        save = st.form_submit_button("Save", use_container_width=True)

    if save:
        upd = supabase.update("customers", {
            "full_name": full_name.strip(),
            "phone": phone.strip(),
            "address_line1": addr1.strip(),
            "address_line2": addr2.strip(),
            "town": town.strip(),
            "postcode": postcode.strip(),
            "allergies": allergies,
            "marketing_opt_in": bool(marketing),
        }, params={"id": f"eq.{customer_row['id']}"})
        if upd.ok and upd.json():
            st.success("Updated")
            st.rerun()
        st.error(upd.text)

    st.divider()
    st.markdown("### Terms & Conditions")
    st.markdown(_terms_md())

def _terms_md():
    return """
**Wivey Bakery – Terms & Conditions (Summary)**

- **Ordering & availability:** Items are subject to availability.
- **Collection & delivery:** Delivery is limited to **Wiveliscombe** only.
- **Time slots:** Slots are allocated in advance.
- **Allergens:** Allergen info is shown. If you have severe allergies, contact us before ordering.
- **Refunds:** Contact us with your order code as soon as possible.
- **Data:** We store customer info to fulfil orders and support your account. Marketing opt‑in is optional.
"""
