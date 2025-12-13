import streamlit as st
from utils.catalog import fetch_categories, fetch_products, display_price_ex_vat
from utils.cart import cart_add

def page_home():
    st.header("🥐 Wivey Bakery – Shop")

    cats = fetch_categories()
    cat_options = [{"id": None, "name": "All"}] + cats
    cat_name_to_id = {c["name"]: c["id"] for c in cat_options}

    col1, col2 = st.columns([2, 1])
    with col1:
        selected = st.selectbox("Category", [c["name"] for c in cat_options], index=0)
    with col2:
        q = st.text_input("Search", placeholder="e.g. brownie, sourdough")

    prods = fetch_products(category_id=cat_name_to_id.get(selected), search=q.strip() if q else None)
    if not prods:
        st.info("No products found.")
        return

    for p in prods:
        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 1, 1])
            with c1:
                st.subheader(p["name"])
                if p.get("description"):
                    st.write(p["description"])
            with c2:
                st.metric("Price (ex VAT)", f"£{display_price_ex_vat(p):.2f}")
            with c3:
                qty = st.number_input("Qty", min_value=1, max_value=50, value=1, step=1, key=f"qty_{p['id']}")
                if st.button("Add to cart", key=f"add_{p['id']}"):
                    cart_add(int(p["id"]), int(qty))
                    st.success("Added.")
    st.sidebar.caption("Go to Checkout to place your order.")
