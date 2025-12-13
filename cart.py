import streamlit as st
from catalog import display_price_ex_vat

def cart_add(product_id: int, qty: int = 1):
    cart = st.session_state.cart
    cart[product_id] = int(cart.get(product_id, 0)) + int(qty)
    if cart[product_id] <= 0:
        cart.pop(product_id, None)

def cart_set(product_id: int, qty: int):
    cart = st.session_state.cart
    if qty <= 0:
        cart.pop(product_id, None)
    else:
        cart[product_id] = int(qty)

def cart_clear():
    st.session_state.cart = {}

def cart_items(products_by_id: dict):
    items = []
    for pid, qty in st.session_state.cart.items():
        p = products_by_id.get(pid)
        if not p:
            continue
        unit_ex = display_price_ex_vat(p)
        items.append({
            "product_id": pid,
            "name": p.get("name", ""),
            "qty": int(qty),
            "unit_price_ex_vat": unit_ex,
            "line_ex_vat": unit_ex * int(qty),
        })
    return items

def cart_totals(products_by_id: dict):
    items = cart_items(products_by_id)
    subtotal = sum(i["line_ex_vat"] for i in items)
    return items, round(subtotal, 2)
