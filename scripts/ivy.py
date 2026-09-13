"""Ivy Homes API client: X-API-Key header + bearer token with auto-refresh."""
import json, os, time, threading, urllib.request, urllib.error, urllib.parse

BASE = "https://solve.ivy.homes"
KEY = "IVY26-71CA6294F4C1"
PASSWORD = "556dec66ae"

class Ivy:
    def __init__(self, email="demo1@ivy.homes"):
        self.email = email
        self.access = None
        self.refresh = None
        self.exp = 0
        self.lock = threading.Lock()
        self.calls = 0
        self.login()

    def _post(self, path, body, auth=None):
        data = json.dumps(body).encode()
        req = urllib.request.Request(BASE + path, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("X-API-Key", KEY)
        if auth:
            req.add_header("Authorization", "Bearer " + auth)
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())

    def login(self):
        d = self._post("/auth/login", {"email": self.email, "password": PASSWORD})
        self.access = d["access_token"]
        self.refresh = d.get("refresh_token")
        self.exp = time.time() + d.get("expires_in", 900)
        return d

    def ensure(self):
        if time.time() > self.exp - 60:
            with self.lock:
                if time.time() > self.exp - 60:
                    try:
                        d = self._post("/auth/refresh", {"refresh_token": self.refresh})
                        self.access = d["access_token"]
                        if d.get("refresh_token"):
                            self.refresh = d["refresh_token"]
                        self.exp = time.time() + d.get("expires_in", 900)
                    except Exception:
                        self.login()

    def raw(self, path, params=None, method="GET", body=None, retries=4):
        self.ensure()
        url = BASE + path
        if params:
            url += ("&" if "?" in path else "?") + urllib.parse.urlencode(params)
        for attempt in range(retries):
            data = json.dumps(body).encode() if body is not None else None
            req = urllib.request.Request(url, data=data, method=method)
            req.add_header("X-API-Key", KEY)
            req.add_header("Authorization", "Bearer " + self.access)
            if body is not None:
                req.add_header("Content-Type", "application/json")
            try:
                self.calls += 1
                with urllib.request.urlopen(req, timeout=90) as r:
                    txt = r.read().decode()
                    return r.status, (json.loads(txt) if txt else None)
            except urllib.error.HTTPError as e:
                txt = e.read().decode()
                try: parsed = json.loads(txt)
                except Exception: parsed = {"raw": txt}
                if e.code == 401 and attempt < retries - 1:
                    self.login(); continue
                if e.code == 429 and attempt < retries - 1:
                    time.sleep(3); continue
                if e.code >= 500 and attempt < retries - 1:
                    time.sleep(2); continue
                return e.code, parsed
            except Exception:
                if attempt < retries - 1:
                    time.sleep(2); continue
                raise
        return None, None

    def get(self, path, params=None):
        return self.raw(path, params)

def probe(client, path, params=None):
    st, body = client.get(path, params)
    s = json.dumps(body)[:400] if body is not None else ""
    print(f"  {st}  {path}{'?'+urllib.parse.urlencode(params) if params else ''}  ->  {s}")
    return st, body

if __name__ == "__main__":
    c = Ivy()
    print("logged in, token exp in", int(c.exp - time.time()), "s")
    for p in ["/v1/listings", "/v1/rentals", "/v1/projects", "/v1/analytics/summary", "/v1/favourites"]:
        probe(c, p, {"limit": 1})
