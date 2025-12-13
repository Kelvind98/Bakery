# Wivey Bakery Customer App (Streamlit + Supabase)

This customer-facing app is designed to run on Streamlit Cloud from GitHub.

## What it uses
- Supabase **anon** key only (safe for public app)
- RPC-only writes:
  - `guest_create_order`
  - `track_order_by_code`
  - `ensure_customer_profile` (optional if you later add login)

## Setup (Streamlit Cloud Secrets)
Add these to Streamlit Cloud → App → Settings → Secrets:

```toml
SUPABASE_URL="https://YOURPROJECT.supabase.co"
SUPABASE_ANON_KEY="YOUR_ANON_KEY"
# Optional: used by maintenance overlay UI
CUSTOMER_MAINTENANCE_PIN="1234"
```

The app reads public settings from the DB via RPC `get_public_settings()`:
- `customer_maintenance_enabled`
- `customer_contact_email`

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```
