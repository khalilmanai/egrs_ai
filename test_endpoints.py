import urllib.request
import json

BASE = "http://localhost:5000/api/v1"

def post(path, data=None):
    body = json.dumps(data).encode() if data else b"{}"
    req = urllib.request.Request(f"{BASE}{path}", method="POST", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        r = urllib.request.urlopen(req, timeout=300)
        return r.status, r.read(), r.headers
    except urllib.request.HTTPError as e:
        return e.code, e.read(), e.headers

def get(path):
    r = urllib.request.urlopen(f"{BASE}{path}", timeout=30)
    return r.status, r.read(), r.headers

# 1. Health
print("=== GET /health ===")
s, body, h = get("/health")
print(f"  {s}: {json.loads(body)}")

# 2. Ingest status
print("\n=== GET /ingest/status ===")
s, body, h = get("/ingest/status")
print(f"  {s}: {json.loads(body)}")

# 3. Global forecast sync (2026)
print("\n=== POST /reports/global-forecast (2026) ===")
s, body, h = post("/reports/global-forecast", {"target_year": 2026})
print(f"  Status: {s}, Size: {len(body)} bytes, Type: {h.get('Content-Type')}")

# 4. Site forecast sync (TUN_0091, 2026)
print("\n=== POST /reports/site-forecast (TUN_0091, 2026) ===")
s, body, h = post("/reports/site-forecast", {"site_code": "TUN_0091", "target_year": 2026})
print(f"  Status: {s}, Size: {len(body)} bytes, Type: {h.get('Content-Type')}")

# 5. Yearly analysis sync (2025)
print("\n=== POST /reports/yearly-analysis (2025) ===")
s, body, h = post("/reports/yearly-analysis", {"year": 2025})
print(f"  Status: {s}, Size: {len(body)} bytes, Type: {h.get('Content-Type')}")

# 6. Train endpoint
print("\n=== POST /train ===")
s, body, h = post("/train")
print(f"  {s}: {json.loads(body)}")

# 7. Async global forecast
print("\n=== POST /reports/async/global-forecast (2026) ===")
s, body, h = post("/reports/async/global-forecast", {"target_year": 2026})
print(f"  {s}: {json.loads(body)}")

print("\n=== All endpoints tested ===")
