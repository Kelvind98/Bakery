import requests

class SupabaseClient:
    def __init__(self, url, anon_key):
        self.url = url.rstrip("/")
        self.anon_key = anon_key
        self.token = None

    def set_auth(self, token):
        self.token = token

    def _headers(self):
        h = {"apikey": self.anon_key, "Content-Type": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def table(self, name):
        return Table(self, name)

class Table:
    def __init__(self, client, name):
        self.client = client
        self.name = name
        self.filters = []
        self.payload = None
        self.method = "GET"

    def select(self, cols="*"):
        self.method = "GET"
        self.cols = cols
        return self

    def insert(self, payload):
        self.method = "POST"
        self.payload = payload
        return self

    def update(self, payload):
        self.method = "PATCH"
        self.payload = payload
        return self

    def eq(self, col, val):
        self.filters.append(f"{col}=eq.{val}")
        return self

    def is_(self, col, val):
        v = "null" if val is None else val
        self.filters.append(f"{col}=is.{v}")
        return self

    def limit(self, n):
        self.filters.append(f"limit={n}")
        return self

    def execute(self):
        url = f"{self.client.url}/rest/v1/{self.name}"
        if self.method == "GET":
            params = {"select": self.cols}
            if self.filters:
                url += "?" + "&".join(self.filters)
            r = requests.get(url, headers=self.client._headers(), params=params)
        elif self.method == "POST":
            r = requests.post(url, headers=self.client._headers(), json=self.payload)
        elif self.method == "PATCH":
            url += "?" + "&".join(self.filters)
            r = requests.patch(url, headers=self.client._headers(), json=self.payload)
        r.raise_for_status()
        return r.json()
