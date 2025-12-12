import json
import requests
import streamlit as st

class SupabaseResponse:
    def __init__(self, data):
        self.data = data

class SupabaseTable:
    def __init__(self, client, table_name: str):
        self.client = client
        self.table_name = table_name
        self._reset()

    def _reset(self):
        self._select = "*"
        self._filters = []
        self._order = None
        self._limit = None
        self._mode = "select"
        self._payload = None

    def select(self, columns: str = "*"):
        self._select = columns
        return self

    def eq(self, column: str, value):
        self._filters.append((column, "eq", value))
        return self

    def gte(self, column: str, value):
        self._filters.append((column, "gte", value))
        return self

    def lt(self, column: str, value):
        self._filters.append((column, "lt", value))
        return self

    def in_(self, column: str, values):
        self._filters.append((column, "in", values))
        return self

    def contains(self, column: str, values):
        self._filters.append((column, "cs", values))
        return self

    def order(self, column: str, desc: bool = False):
        self._order = (column, desc)
        return self

    def limit(self, n: int):
        self._limit = n
        return self

    def insert(self, payload):
        self._mode = "insert"
        self._payload = payload
        return self

    def update(self, payload):
        self._mode = "update"
        self._payload = payload
        return self

    def _build_params(self):
        params = {"select": self._select}
        for col, op, val in self._filters:
            if op == "eq":
                params[col] = f"eq.{val}"
            elif op == "gte":
                params[col] = f"gte.{val}"
            elif op == "lt":
                params[col] = f"lt.{val}"
            elif op == "in":
                joined = ",".join(str(v) for v in val)
                params[col] = f"in.({joined})"
            elif op == "cs":
                params[col] = f"cs.{json.dumps(val)}"
        if self._order:
            col, desc = self._order
            direction = "desc" if desc else "asc"
            params["order"] = f"{col}.{direction}"
        if self._limit is not None:
            params["limit"] = str(self._limit)
        return params

    def execute(self):
        url = f"{self.client.base_url}/{self.table_name}"
        headers = self.client.headers()
        params = self._build_params()

        if self._mode == "select":
            resp = requests.get(url, headers=headers, params=params)
        elif self._mode == "insert":
            payload = self._payload
            if isinstance(payload, dict):
                payload = [payload]
            resp = requests.post(url, headers=headers, params={"select": "*"}, json=payload)
        elif self._mode == "update":
            payload = self._payload
            resp = requests.patch(url, headers=headers, params=params, json=payload)
        else:
            raise ValueError(f"Unsupported mode {self._mode}")

        self._reset()

        if not resp.ok:
            raise Exception(f"Supabase error: {resp.status_code} {resp.text}")

        try:
            data = resp.json()
        except Exception:
            data = None
        return SupabaseResponse(data)

class SupabaseClientRest:
    def __init__(self, url: str, key: str):
        self.url = url.rstrip("/")
        self.base_url = f"{self.url}/rest/v1"
        self.key = key

    def headers(self):
        return {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Prefer": "return=representation",
        }

    def table(self, name: str) -> SupabaseTable:
        return SupabaseTable(self, name)

@st.cache_resource
def get_supabase_client():
    url = st.secrets["SUPABASE_URL"]
    anon_key = st.secrets["SUPABASE_ANON_KEY"]
    client = SupabaseClientRest(url, anon_key)
    return client
