import sys, json
sys.path.insert(0,"scripts")
from ivy import Ivy
c=Ivy()
st,b=c.get("/v1/listings",{"sort_by":"carpet_area","order":"asc","limit":20})
print("sort_by=carpet_area:")
for r in b["results"]:
    conv = r["carpet_area"]*10.7639 if (r["website"]=="magichomes" and r["posted_at"]>="2026-06-01") else r["carpet_area"]
    print(f"  {r['listing_id']} ca={r['carpet_area']:5} sbua={r['super_built_up_area']:5} conv={conv:7.1f} web={r['website']:11} posted={r['posted_at']}")

st,b=c.get("/v1/listings",{"sort_by":"posted_at","limit":20})
print("\nsort_by=posted_at:")
for r in b["results"]: print(f"  {r['listing_id']} {r['posted_at']} web={r['website']}")

st,b=c.get("/v1/listings",{"sort_by":"bedroom","limit":8})
print("\nsort_by=bedroom:", [(r["listing_id"],r["bedroom"],r["property_type"]) for r in b["results"]])

print("\nrentals sort_by=price:")
for od in ["asc","desc"]:
    st,b=c.get("/v1/rentals",{"sort_by":"price","order":od,"limit":8})
    print(f"  {od}: {[r['price'] for r in b['results']]}")
print("projects sort_by=price_max:")
for od in ["asc","desc"]:
    st,b=c.get("/v1/projects",{"sort_by":"price_max","order":od,"limit":8})
    print(f"  {od}: {[(r['project_id'],r['price_max']) for r in b['results']]}")
print("projects sort_by=launch_date:")
st,b=c.get("/v1/projects",{"sort_by":"launch_date","limit":8})
print("  ", [(r['project_id'],r['launch_date']) for r in b['results']])
print("projects sort_by=total_units:")
st,b=c.get("/v1/projects",{"sort_by":"total_units","limit":8})
print("  ", [(r['project_id'],r['total_units']) for r in b['results']])

print("\n### does offset+limit paging with sort stay stable? ###")
st,b1=c.get("/v1/listings",{"limit":10,"offset":0})
st,b2=c.get("/v1/listings",{"limit":10,"offset":0})
print("  same first page twice:", [r["listing_id"] for r in b1["results"]]==[r["listing_id"] for r in b2["results"]])
st,b3=c.get("/v1/listings",{"limit":5,"offset":0}); st,b4=c.get("/v1/listings",{"limit":5,"offset":5})
print("  page1+page2 vs limit10:", [r["listing_id"] for r in b3["results"]]+[r["listing_id"] for r in b4["results"]] == [r["listing_id"] for r in b1["results"]])

print("\n### how far past 'total' does data go? ###")
for off in [4800,5000,5090,5095,5099,5100,5150]:
    st,b=c.get("/v1/listings",{"limit":5,"offset":off})
    print(f"  offset={off} count={b['count']} has_more={b['has_more']} total={b['total']} ids={[r['listing_id'] for r in b['results']]}")
