import requests

class SupabaseAuth:
    def __init__(self, url, anon_key):
        self.url = url.rstrip("/")
        self.anon_key = anon_key

    def _headers(self, token=None):
        h = {"apikey": self.anon_key, "Content-Type": "application/json"}
        if token:
            h["Authorization"] = f"Bearer {token}"
        return h

    def sign_up(self, email, password):
        return requests.post(
            f"{self.url}/auth/v1/signup",
            headers=self._headers(),
            json={"email": email, "password": password},
            timeout=30,
        )

    def sign_in(self, email, password):
        return requests.post(
            f"{self.url}/auth/v1/token?grant_type=password",
            headers=self._headers(),
            json={"email": email, "password": password},
            timeout=30,
        )

    def send_reset(self, email, redirect_to):
        return requests.post(
            f"{self.url}/auth/v1/recover",
            headers=self._headers(),
            json={"email": email, "redirect_to": redirect_to},
            timeout=30,
        )
