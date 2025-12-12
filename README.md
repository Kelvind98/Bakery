# Wivey Bakery — Customer App (Supabase Auth)

Includes:
- Supabase Auth login/signup/reset (no supabase-py)
- Full menu with search + allergen hiding
- Cart + Checkout (pickup/delivery + notes + payment type)
- My Orders + Reorder
- Order Tracking (guest compatible via RPC `track_order_by_code`)
- My Account dashboard (address/allergies/contact)

## Streamlit Secrets
```toml
SUPABASE_URL = "https://YOURPROJECT.supabase.co"
SUPABASE_ANON_KEY = "YOUR_PUBLIC_ANON_KEY"
AUTH_REDIRECT_URL = "https://YOUR-APP.streamlit.app"
```
