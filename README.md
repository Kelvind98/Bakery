# Wivey Bakery — Customer App (v6)

This version fixes the issue where order items were not attaching to orders.

- Logged-in checkout: inserts into `orders` then inserts into `order_items` for that `order_id`
- Guest checkout: uses secure RPC `guest_create_order` (order + items inserted server-side)

DB prerequisites:
- RPC: `guest_create_order(...)` granted to anon
- RPC: `track_order_by_code(text)` granted to anon
- RLS policies: authenticated insert/select on orders + order_items
