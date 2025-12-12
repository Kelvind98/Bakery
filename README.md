# Wivey Bakery — Customer App (Supabase Auth)

Customer-facing ordering portal:
- Supabase Auth login + reset password
- Guest checkout
- Allergies-based product hiding
- Pickup / delivery (Wiveliscombe)
- Time slot selection
- Order tracking by order code

## Deploy (GitHub → Streamlit Cloud)

1. Upload this folder to a GitHub repo (do NOT commit secrets).
2. Streamlit Cloud → New app → choose repo → main file `app.py`
3. App Settings → Secrets:

```toml
SUPABASE_URL = "https://YOURPROJECT.supabase.co"
SUPABASE_ANON_KEY = "YOUR_ANON_PUBLIC_KEY"
AUTH_REDIRECT_URL = "https://YOUR-APP.streamlit.app"
```

## Supabase Auth settings

Supabase → Authentication → URL Configuration:
- Site URL: `https://YOUR-APP.streamlit.app`
- Redirect URLs:
  - `https://YOUR-APP.streamlit.app`
  - `http://localhost:8501` (optional)
