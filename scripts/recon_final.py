import sys, json
sys.path.insert(0,"scripts")
from ivy import Ivy
c=Ivy()
print("### logout / refresh ###")
print(" POST /auth/logout:", c.raw("/auth/logout", method="POST", body={}))
print(" POST /auth/refresh:", str(c.raw("/auth/refresh", method="POST", body={"refresh_token":c.refresh}))[:260])
print(" POST /auth/refresh bad:", c.raw("/auth/refresh", method="POST", body={"refresh_token":"garbage"}))
print(" still authorised after logout:", c.get("/v1/listings",{"limit":1})[0])

print("\n### documented filters on rentals / projects ###")
import urllib.parse
def t(path, params):
    st,b=c.get(path,{**params,"limit":2})
    return st, (b.get("total") if isinstance(b,dict) else None)
print(" rentals baseline:", t("/v1/rentals",{}))
for p in [{"locality":"powai"},{"bhk":3},{"furnishing":"unfurnished"},{"property_type":"villa"},{"page":3}]:
    print(f"  rentals {p} -> {t('/v1/rentals',p)}")
print(" projects baseline:", t("/v1/projects",{}))
for p in [{"locality":"powai"},{"project_status":"new launch"},{"page":3},{"developer_name":"Brigade"}]:
    print(f"  projects {p} -> {t('/v1/projects',p)}")

print("\n### page param proof (offset unchanged) ###")
for pg in [1,2,5]:
    st,b=c.get("/v1/listings",{"limit":3,"page":pg})
    print(f"  page={pg} offset={b['offset']} ids={[r['listing_id'] for r in b['results']]}")

print("\n### limit clamp proof ###")
for lim in [50,51,100,200]:
    st,b=c.get("/v1/listings",{"limit":lim})
    print(f"  requested limit={lim} -> served limit={b['limit']} count={b['count']}")

print("\n### total vs true count per endpoint (with locality filter) ###")
for path,loc in [("/v1/listings","powai"),("/v1/rentals","powai"),("/v1/projects","powai")]:
    st,b=c.get(path,{"locality":loc,"limit":50})
    n=len(b["results"]); off=50
    while b.get("has_more"):
        st,b=c.get(path,{"locality":loc,"limit":50,"offset":off}); n+=len(b["results"]); off+=50
    st,b0=c.get(path,{"locality":loc,"limit":1})
    print(f"  {path}?locality={loc}: reported total={b0['total']}  actually retrievable={n}")

print("\n### /v1/localities cross-check ###")
st,b=c.get("/v1/localities"); print(" ", json.dumps(b)[:400])
print("\n### listing detail vs list-view record identical? ###")
st,a=c.get("/v1/listings",{"limit":1})
st,d=c.get("/v1/listings/"+a["results"][0]["listing_id"])
print("  identical:", json.dumps(a["results"][0],sort_keys=True)==json.dumps(d,sort_keys=True))
print("\n### rentals detail fields ###")
st,r=c.get("/v1/rentals/R5000001"); print(" ", sorted(r.keys()))
print("  maintenance present:", "maintenance" in r, " deposit:", r.get("deposit"), " price:", r.get("price"))
print("\ncalls used:", c.calls)
