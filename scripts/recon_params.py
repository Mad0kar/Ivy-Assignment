import sys, json
sys.path.insert(0, "scripts")
from ivy import Ivy
c = Ivy()

def show(label, path, params=None):
    st, b = c.get(path, params)
    if isinstance(b, dict) and "results" in b:
        meta = {k: v for k, v in b.items() if k != "results"}
        ids = [r.get("listing_id") or r.get("project_id") or r.get("locality") for r in b["results"]][:6]
        print(f"{st} {label:55} meta={meta} ids={ids}")
    else:
        print(f"{st} {label:55} {json.dumps(b)[:300]}")

print("=== /v1/me ==="); st,b=c.get("/v1/me"); print(json.dumps(b, indent=1))
print("\n=== /v1/localities ==="); st,b=c.get("/v1/localities"); print(json.dumps(b, indent=1))

print("\n=== PAGINATION ===")
show("limit=5", "/v1/listings", {"limit":5})
show("limit=5&offset=5", "/v1/listings", {"limit":5,"offset":5})
show("limit=5&page=2 (docs param)", "/v1/listings", {"limit":5,"page":2})
show("limit=200", "/v1/listings", {"limit":200})
show("limit=500", "/v1/listings", {"limit":500})
show("limit=1000", "/v1/listings", {"limit":1000})
show("limit=201", "/v1/listings", {"limit":201})
show("limit=0", "/v1/listings", {"limit":0})
show("limit=-1", "/v1/listings", {"limit":-1})
show("offset=4800", "/v1/listings", {"limit":50,"offset":4800})
show("offset=4802", "/v1/listings", {"limit":50,"offset":4802})

print("\n=== FILTERS ===")
for p in [{"locality":"powai"},{"locality":"Powai"},{"bhk":2},{"bedroom":2},
          {"property_type":"apartment"},{"furnishing":"unfurnished"},
          {"min_price":10000000},{"max_price":5000000},
          {"min_price":10000000,"max_price":5000000},
          {"project_id":"P50001"},{"is_live":"true"},{"bogus_param":"xyz"}]:
    show(str(p), "/v1/listings", {**p, "limit":3})

print("\n=== SORT ===")
for p in [{"sort_by":"price","order":"asc"},{"sort_by":"price","order":"desc"},
          {"sort_by":"carpet_area","order":"desc"},{"sort_by":"posted_at","order":"desc"},
          {"sort_by":"bedroom","order":"desc"},{"sort_by":"nonsense"}]:
    st,b = c.get("/v1/listings", {**p,"limit":5})
    if isinstance(b,dict) and "results" in b:
        key = p.get("sort_by","price")
        vals=[r.get(key) for r in b["results"]]
        print(f"{st} {str(p):50} {key}={vals}")
    else:
        print(f"{st} {str(p):50} {json.dumps(b)[:200]}")
print("calls:", c.calls)
