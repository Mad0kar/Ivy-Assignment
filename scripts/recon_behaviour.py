import sys, json, time
sys.path.insert(0,"scripts")
from ivy import Ivy
c=Ivy()

print("### FAVOURITES /v1/saved lifecycle ###")
print(" GET  ", c.get("/v1/saved"))
print(" POST {id}", c.raw("/v1/saved", method="POST", body={"id":"SQU-5004678"}))
print(" POST {listing_id}", c.raw("/v1/saved", method="POST", body={"listing_id":"100-5003908"}))
st,b=c.get("/v1/saved"); print(" GET  ", json.dumps(b)[:600])
print(" POST dup", c.raw("/v1/saved", method="POST", body={"listing_id":"SQU-5004678"}))
print(" DELETE", c.raw("/v1/saved/SQU-5004678", method="DELETE"))
print(" DELETE missing", c.raw("/v1/saved/NOPE-1", method="DELETE"))
st,b=c.get("/v1/saved"); print(" GET after delete", json.dumps(b)[:300])
print(" POST bad id", c.raw("/v1/saved", method="POST", body={"listing_id":"DOES-NOT-EXIST"}))

print("\n### per-user isolation ###")
c2=Ivy("demo2@ivy.homes")
st,b=c2.get("/v1/saved"); print(" demo2 saved:", json.dumps(b)[:200])

print("\n### date / extra filter params on /v1/listings ###")
for p in [{"posted_after":"2026-09-01"},{"from_date":"2026-09-01"},{"since":"2026-09-01"},
          {"min_carpet_area":1000},{"max_carpet_area":500},{"is_verified":"true"},
          {"posted_by":"owner"},{"website":"magichomes"},{"min_bhk":3},{"q":"powai"},
          {"search":"powai"},{"apartment_name":"assetz park"},{"locality":"nonexistent"},
          {"bhk":99},{"property_type":"castle"},{"furnishing":"bogus"},{"order":"sideways"}]:
    st,b=c.get("/v1/listings", {**p,"limit":2})
    t = b.get("total") if isinstance(b,dict) else None
    print(f"  {str(p):42} -> {st} total={t} {json.dumps(b)[:110] if st!=200 else ''}")

print("\n### sorting deep-dive ###")
for sb in ["price","carpet_area","posted_at","bedroom"]:
    for od in ["asc","desc"]:
        st,b=c.get("/v1/listings",{"sort_by":sb,"order":od,"limit":10})
        print(f"  sort_by={sb:12} order={od:4} -> {[r[sb] for r in b['results']]}")

print("\n### rentals/projects param support ###")
for path,ps in [("/v1/rentals",[{"locality":"powai"},{"bhk":2},{"sort_by":"price","order":"desc"},{"furnishing":"unfurnished"},{"min_price":50000}]),
                ("/v1/projects",[{"locality":"powai"},{"project_status":"ready to move"},{"sort_by":"price_max","order":"desc"},{"sort_by":"launch_date"},{"min_price":1}])]:
    for p in ps:
        st,b=c.get(path,{**p,"limit":3})
        t=b.get("total") if isinstance(b,dict) else None
        ids=[r.get("listing_id") or r.get("project_id") for r in b.get("results",[])] if st==200 else []
        print(f"  {path} {str(p):40} -> {st} total={t} {ids}")

print("\n### auth edge cases ###")
import urllib.request, urllib.error
def bare(path, hdrs):
    req=urllib.request.Request("https://solve.ivy.homes"+path)
    for k,v in hdrs.items(): req.add_header(k,v)
    try:
        with urllib.request.urlopen(req,timeout=30) as r: return r.status, r.read()[:120].decode()
    except urllib.error.HTTPError as e: return e.code, e.read()[:200].decode()
print(" no key no token:", bare("/v1/listings?limit=1",{}))
print(" key only:", bare("/v1/listings?limit=1",{"X-API-Key":"IVY26-71CA6294F4C1"}))
print(" token only:", bare("/v1/listings?limit=1",{"Authorization":"Bearer "+c.access}))
print(" bad key:", bare("/v1/listings?limit=1",{"X-API-Key":"IVY26-000000000000","Authorization":"Bearer "+c.access}))
print(" query-param key:", bare("/v1/listings?limit=1&api_key=IVY26-71CA6294F4C1",{"Authorization":"Bearer "+c.access}))
print(" 404 listing:", c.get("/v1/listings/NOPE-999"))
