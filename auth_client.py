import requests

class SupabaseAuth:
    def __init__(self, supabase_url: str, anon_key: str):
        self.url = supabase_url.rstrip("/")
        self.anon_key = anon_key

    def _headers(self, access_token: str | None = None):
        h = {
            "apikey": self.anon_key,
            "Content-Type": "application/json",
        }
        if access_token:
            h["Authorization"] = f"Bearer {access_token}"
        return h

    def sign_up(self, email: str, password: str):
        r = requests.post(
            f"{self.url}/auth/v1/signup",
            headers=self._headers(),
            json={"email": email, "password": password},
            timeout=30,
        )
        return r

    def sign_in(self, email: str, password: str):
        r = requests.post(
            f"{self.url}/auth/v1/token?grant_type=password",
            headers=self._headers(),
            json={"email": email, "password": password},
            timeout=30,
        )
        return r

    def sign_out(self, access_token: str):
        r = requests.post(
            f"{self.url}/auth/v1/logout",
            headers=self._headers(access_token),
            timeout=30,
        )
        return r

    def send_reset_email(self, email: str, redirect_to: str):
        # Supabase will email a reset link. redirect_to must be allowed in Auth settings.
        r = requests.post(
            f"{self.url}/auth/v1/recover",
            headers=self._headers(),
            json={"email": email, "redirect_to": redirect_to},
            timeout=30,
        )
        return r
