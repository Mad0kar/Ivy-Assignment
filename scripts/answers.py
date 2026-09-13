import json, collections, re, math, itertools
from datetime import datetime
L = json.load(open("data/raw/listings.json"))
R = json.load(open("data/raw/rentals.json"))
P = json.load(open("data/raw/projects.json"))
def norm(s): return re.sub(r'[^a-z0-9]+',' ', s.lower()).strip()
SQM = lambda r: r["website"]=="magichomes" and r["posted_at"]>="2026-06-01"
SQFT_PER_SQM = 10.7639
def area(r): return r["carpet_area"]*SQFT_PER_SQM if SQM(r) else float(r["carpet_area"])

# ---- Q4 corrupt ----
corrupt=set()
classes={
 "negative_price":       [r for r in L if r["price"]<=0],
 "absurd_low_price":     [r for r in L if 0<r["price"]<100000],
 "carpet_gt_superbuiltup":[r for r in L if r["carpet_area"]>r["super_built_up_area"]],
 "floor_gt_total_floors":[r for r in L if r["floor"]>r["total_floors"]],
 "posted_after_reference":[r for r in L if r["posted_at"]>="2026-09-10T00:00:00"],
 "latlon_swapped":       [r for r in L if not(18.8<=r["latitude"]<=19.5)],
 "no_bedroom_no_bathroom":[r for r in L if r["bedroom"]==0 and r["bathroom"]==0 and r["property_type"]!="plot"],
}
for k,v in classes.items(): corrupt |= set(r["listing_id"] for r in v)
CORRUPT=sorted(corrupt)

# ---- Q9 fake ----
byphone=collections.defaultdict(list)
for r in L: byphone[r["posted_by_contact"]].append(r)
FAKE_PHONES=sorted(p for p,rs in byphone.items() if len(rs)>=10 and all(x["is_verified"] for x in rs))
FAKE=sorted(r["listing_id"] for p in FAKE_PHONES for r in byphone[p])

# ---- Q2 unique properties ----
SK=lambda r:(norm(r["apartment_name"]),r["locality"],r["bedroom"],r["floor"],r["bathroom"],
             r["balcony"],r["total_floors"],r["facing_direction"],r["furnishing"],
             r["property_type"],r["covered_parking"])
UNIQUE=len(set(SK(r) for r in L))

# ---- Q6 ----
sel=[r for r in L if r["is_live"] and r["bedroom"]==2
     and r["listing_id"] not in corrupt and r["listing_id"] not in set(FAKE)]
pps=[r["price"]/area(r) for r in sel]
Q6=round(sum(pps)/len(pps),2)

# ---- Q7 ----
best=max(P, key=lambda p:p["price_max"])
Q7={"project_id":best["project_id"],"price_max_inr":int(round(best["price_max"]*1e7))}

# ---- Q8 ----
Q8=sum(1 for r in L if datetime(2026,9,3)<=datetime.fromisoformat(r["posted_at"])<datetime(2026,9,10))

# ---- Q10 ----
byproj=collections.defaultdict(list)
for r in L:
    if r.get("project_id"): byproj[r["project_id"]].append(r)
Q10=sum(1 for p in P if p["total_listings"]!=len([r for r in byproj.get(p["project_id"],[]) if r["is_live"]]))

ANS={
 "total_listing_records": len(L),
 "unique_properties": UNIQUE,
 "active_listings": sum(1 for r in L if r["is_live"]),
 "corrupt_listing_ids": CORRUPT,
 "total_monthly_rent": sum(r["price"] for r in R if r["locality"]=="powai"),
 "avg_price_per_sqft_2bhk": Q6,
 "costliest_project": Q7,
 "listings_last_7_days": Q8,
 "fake_listing_ids": FAKE,
 "projects_with_wrong_listing_count": Q10,
}
json.dump(ANS, open("data/answers.json","w"), indent=2)
print("### ANSWERS ###")
for k,v in ANS.items():
    print(f"  {k:36} {v if not isinstance(v,list) else str(len(v))+' ids'}")
print("\ncorrupt classes:", {k:len(v) for k,v in classes.items()}, "union", len(CORRUPT))
print("fake phones:", FAKE_PHONES, "->", len(FAKE), "listings")
print("Q6 detail: n=",len(sel)," mean=",Q6," median=",round(sorted(pps)[len(pps)//2],2))
print("Q6 without exclusions:", round(sum(r['price']/area(r) for r in L if r['is_live'] and r['bedroom']==2)/sum(1 for r in L if r['is_live'] and r['bedroom']==2),2))
print("Q6 without sqm conversion:", round(sum(r['price']/r['carpet_area'] for r in sel)/len(sel),2))
print("Q8 alt (treat naive as UTC, shift +5:30):", sum(1 for r in L if datetime(2026,9,3)<=datetime.fromisoformat(r["posted_at"]).replace(microsecond=0)+__import__('datetime').timedelta(hours=5,minutes=30)<datetime(2026,9,10)))
print("Q7 runner-ups:", sorted(((p["price_max"],p["project_id"]) for p in P), reverse=True)[:4])
