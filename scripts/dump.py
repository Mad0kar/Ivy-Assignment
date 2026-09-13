import sys, json, time, os
sys.path.insert(0, "scripts")
from ivy import Ivy

c = Ivy()
os.makedirs("data/raw", exist_ok=True)

def drain(path, label, hard_cap=40000):
    out, offset, limit = [], 0, 50
    seen_pages = 0
    while True:
        st, b = c.get(path, {"limit": limit, "offset": offset})
        if st != 200 or not isinstance(b, dict):
            print(f"  !! stop at offset={offset} status={st} body={str(b)[:200]}"); break
        res = b.get("results", [])
        out.extend(res)
        seen_pages += 1
        if seen_pages % 20 == 0:
            print(f"    {label}: offset={offset} got={len(res)} accum={len(out)} total_field={b.get('total')} has_more={b.get('has_more')}")
        if not b.get("has_more") or not res:
            print(f"  {label}: DONE offset={offset} accum={len(out)} total_field={b.get('total')} has_more={b.get('has_more')}")
            break
        offset += limit
        if len(out) > hard_cap:
            print(f"  !! {label}: hit hard cap"); break
    return out

for path, name in [("/v1/listings","listings"), ("/v1/rentals","rentals"), ("/v1/projects","projects")]:
    t0=time.time()
    rows = drain(path, name)
    json.dump(rows, open(f"data/raw/{name}.json","w"))
    print(f"{name}: {len(rows)} rows in {time.time()-t0:.1f}s ({c.calls} calls so far)\n")
