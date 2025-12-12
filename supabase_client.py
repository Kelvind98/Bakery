import requests
from urllib.parse import urlencode

class SupabaseError(Exception):
    pass

class SupabaseClient:
    def __init__(self, url: str, anon_key: str):
        self.url = url.rstrip("/")
        self.anon_key = anon_key
        self.token = None

    def set_auth(self, token: str | None):
        self.token = token

    def _headers(self, returning: bool = False):
        h = {"apikey": self.anon_key, "Content-Type": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        if returning:
            h["Prefer"] = "return=representation"
        return h

    def table(self, name: str):
        return Table(self, name)

    def rpc(self, fn: str, payload: dict, returning: bool = False):
        r = requests.post(
            f"{self.url}/rest/v1/rpc/{fn}",
            headers=self._headers(returning=returning),
            json=payload,
            timeout=30,
        )
        if not r.ok:
            raise SupabaseError(f"{r.status_code}: {r.text}")
        if r.status_code == 204:
            return None
        try:
            return r.json()
        except Exception:
            return None

class Table:
    def __init__(self, client: SupabaseClient, name: str):
        self.client = client
        self.name = name
        self._filters = []
        self._select = "*"
        self._order = None
        self._limit = None
        self._method = "GET"
        self._payload = None

    def select(self, cols="*"):
        self._method = "GET"
        self._select = cols
        return self

    def insert(self, payload):
        self._method = "POST"
        self._payload = payload
        return self

    def update(self, payload):
        self._method = "PATCH"
        self._payload = payload
        return self

    def delete(self):
        self._method = "DELETE"
        return self

    def eq(self, col, val):
        self._filters.append((col, f"eq.{val}"))
        return self

    def is_(self, col, val):
        v = "null" if val is None else val
        self._filters.append((col, f"is.{v}"))
        return self

    def ilike(self, col, pattern):
        self._filters.append((col, f"ilike.{pattern}"))
        return self

    def order(self, col, desc=False):
        direction = "desc" if desc else "asc"
        self._order = f"{col}.{direction}"
        return self

    def limit(self, n: int):
        self._limit = n
        return self

    def _build_url(self):
        base = f"{self.client.url}/rest/v1/{self.name}"
        params = {"select": self._select}
        if self._order:
            params["order"] = self._order
        if self._limit is not None:
            params["limit"] = str(self._limit)
        for k, v in self._filters:
            params[k] = v
        return base + "?" + urlencode(params)

    def execute(self):
        url = self._build_url()
        returning = self._method in ("POST", "PATCH")
        h = self.client._headers(returning=returning)

        if self._method == "GET":
            r = requests.get(url, headers=h, timeout=30)
        elif self._method == "POST":
            r = requests.post(f"{self.client.url}/rest/v1/{self.name}", headers=h, json=self._payload, timeout=30)
        elif self._method == "PATCH":
            r = requests.patch(url.replace("select=%2A", "select=*"), headers=h, json=self._payload, timeout=30)
        elif self._method == "DELETE":
            r = requests.delete(url.replace("select=%2A", "select=*"), headers=h, timeout=30)
        else:
            raise SupabaseError("Unsupported method")

        if not r.ok:
            raise SupabaseError(f"{r.status_code}: {r.text}")

        if r.status_code == 204:
            return []
        try:
            return r.json()
        except Exception:
            return []
