import requests

class SupabaseClient:
    def __init__(self, supabase_url: str, anon_key: str):
        self.url = supabase_url.rstrip("/")
        self.anon_key = anon_key
        self._access_token = None

    def set_auth(self, access_token: str | None):
        self._access_token = access_token

    def _headers(self):
        h = {"apikey": self.anon_key, "Content-Type": "application/json"}
        if self._access_token:
            h["Authorization"] = f"Bearer {self._access_token}"
        return h

    def select(self, table: str, select: str="*", params: dict | None=None):
        params = params or {}
        params.setdefault("select", select)
        return requests.get(f"{self.url}/rest/v1/{table}", headers=self._headers(), params=params, timeout=30)

    def insert(self, table: str, payload):
        # Prefer return=representation if you later want created rows
        headers = self._headers() | {"Prefer": "return=representation"}
        return requests.post(f"{self.url}/rest/v1/{table}", headers=headers, json=payload, timeout=30)

    def update(self, table: str, payload: dict, params: dict):
        headers = self._headers() | {"Prefer": "return=representation"}
        return requests.patch(f"{self.url}/rest/v1/{table}", headers=headers, params=params, json=payload, timeout=30)

    def rpc(self, fn: str, payload: dict):
        return requests.post(f"{self.url}/rest/v1/rpc/{fn}", headers=self._headers(), json=payload, timeout=30)
