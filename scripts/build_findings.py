import json, collections, re
L = json.load(open("data/raw/listings.json"))
R = json.load(open("data/raw/rentals.json"))
P = json.load(open("data/raw/projects.json"))
ANS = json.load(open("data/answers.json"))
def norm(s): return re.sub(r'[^a-z0-9]+',' ', s.lower()).strip()
SQM = lambda r: r["website"]=="magichomes" and r["posted_at"]>="2026-06-01"

sqm_ids = sorted(r["listing_id"] for r in L if SQM(r))
notlive  = sorted(r["listing_id"] for r in L if not r["is_live"])
lakh_projects = sorted(p["project_id"] for p in P if p["price_min"]>p["price_max"])
powai_tail = sorted(r["listing_id"] for r in L if r["locality"]=="powai")[-20:]
title_mismatch=[]
for r in R:
    m=re.match(r'^(\d+) BHK for rent in (.+)$', r.get("title",""))
    if m and m.group(2).strip().lower()!=r["locality"]: title_mismatch.append(r["listing_id"])

# duplicate pairs evidence
SK=lambda r:(norm(r["apartment_name"]),r["locality"],r["bedroom"],r["floor"],r["bathroom"],
             r["balcony"],r["total_floors"],r["facing_direction"],r["furnishing"],
             r["property_type"],r["covered_parking"])
g=collections.defaultdict(list)
for r in L: g[SK(r)].append(r["listing_id"])
dup_pairs=[sorted(v) for v in g.values() if len(v)>1]
dup_ev=[i for pair in sorted(dup_pairs)[:10] for i in pair[:2]]   # 10 pairs, adjacent so they read as pairs

# project count mismatch evidence
byproj=collections.defaultdict(list)
for r in L:
    if r.get("project_id"): byproj[r["project_id"]].append(r)
wrong_ct=sorted(p["project_id"] for p in P
                if p["total_listings"]!=len([r for r in byproj.get(p["project_id"],[]) if r["is_live"]]))

# per-class corrupt evidence
cls={
 "negative_price":[r["listing_id"] for r in L if r["price"]<=0],
 "absurd_low_price":[r["listing_id"] for r in L if 0<r["price"]<100000],
 "carpet_gt_sbua":[r["listing_id"] for r in L if r["carpet_area"]>r["super_built_up_area"]],
 "floor_gt_total":[r["listing_id"] for r in L if r["floor"]>r["total_floors"]],
 "future_posted":[r["listing_id"] for r in L if r["posted_at"]>="2026-09-10T00:00:00"],
 "latlon_swapped":[r["listing_id"] for r in L if not(18.8<=r["latitude"]<=19.5)],
 "no_bed_no_bath":[r["listing_id"] for r in L if r["bedroom"]==0 and r["bathroom"]==0 and r["property_type"]!="plot"],
}

F=[]
def add(endpoint, category, documented, actual, how_found, impact, evidence=None):
    F.append({"endpoint":endpoint,"category":category,"documented":documented,"actual":actual,
              "how_found":how_found,"impact":impact,"evidence":evidence or []})

# ---------- AUTH ----------
add("*","auth",
 "Append the API key as a query parameter: GET /v1/listings?api_key=IVY26-XXXX",
 "The query parameter is rejected. The key must be sent as an X-API-Key request header; sending it in the query string returns 401 {\"detail\":\"send your key in the X-API-Key request header, not as a query parameter\"}",
 "First call I made. The 401 body names the correct mechanism.",
 "Every request in the documented form fails. Nothing works until you switch to the header.")

add("/auth/login","auth",
 "Response contains a field named \"token\", and \"user\" carries {email, name}",
 "The field is \"access_token\". The response also carries \"refresh_token\" and \"refresh_url\": \"/auth/refresh\", and \"user\" contains only {\"email\": ...} - there is no \"name\".",
 "Logged in and printed the raw response body.",
 "A client that reads response.token stores undefined and every later request is unauthenticated.")

add("/auth/login","auth",
 "expires_in is 86400 - \"Tokens are valid for 24 hours, so a single login is enough for one working session.\"",
 "expires_in is 900. The access token dies after 15 minutes; the JWT exp claim confirms iat+900.",
 "Read expires_in, then base64-decoded the JWT payload, then let a token sit idle and watched a request 401.",
 "Highest-impact lie in the document. A frontend built on the documented 24h lifetime is broken 15 minutes after login - which is exactly the requirement the brief sets.")

add("/auth/refresh","undocumented_endpoint",
 "\"There is no refresh flow.\"",
 "POST /auth/refresh exists, takes {\"refresh_token\": ...} and returns a fresh access_token plus a rotated refresh_token. The login response advertises it in refresh_url. A bad token returns 401 {\"detail\":\"malformed or tampered token\"}.",
 "The login response contained refresh_token and refresh_url, which the documentation denies exist. Called it.",
 "This is how you satisfy \"still working thirty minutes after you logged in\" without forcing a re-login. My app refreshes 60s before expiry.")

add("/auth/logout","auth",
 "\"Invalidates the current token server side.\"",
 "POST /auth/logout returns 200 {\"ok\":true,\"note\":\"tokens are stateless; discard them client side\"} and the token keeps working afterwards. Nothing is invalidated server side.",
 "Called logout, then reused the same access token on /v1/listings - still 200.",
 "Logging out only clears client state. A shared machine keeps a usable token in whatever the client failed to wipe.")

# ---------- PAGINATION ----------
add("*","pagination",
 "Every collection takes page and limit; responses are {total, page, page_size, results}",
 "Collections take limit and offset. Responses are {limit, offset, count, total, has_more, results}. There is no page or page_size field.",
 "Requested ?limit=5 and read the envelope.",
 "Any client written against the documented envelope reads undefined for page_size and cannot advance past page 1.")

add("*","pagination",
 "page is a supported 1-indexed parameter",
 "page is accepted with a 200 and silently ignored. ?limit=3&page=1, &page=2 and &page=5 all return offset=0 and the identical three records.",
 "Requested the same query at page=1,2,5 and diffed the returned ids - byte-identical.",
 "A paginator built on page loops forever over the first 50 records and every count derived from it is wrong.")

add("*","pagination",
 "limit has a maximum of 200",
 "The maximum is 50. limit=51, 100, 200, 500 and 1000 are all accepted with 200 and silently clamped - the response honestly reports \"limit\": 50. limit=0 and limit=-1 correctly 422.",
 "Swept limit values and compared the requested limit to the limit the envelope reported back.",
 "Four times as many requests as the documentation implies. Harmless if you read the envelope, silently truncating if you trust the doc.")

add("*","pagination",
 "\"total is the exact number of records matching your filters. To fetch every record, read total, divide by your limit, and request that many pages.\"",
 "total understates the number of retrievable records by about 5.9% on every endpoint and every filter. Unfiltered: /v1/listings reports 4802 and serves 5100; /v1/rentals reports 1977 and serves 2100; /v1/projects reports 555 and serves 590. With ?locality=powai: listings 456 vs 484, rentals 209 vs 222, projects 50 vs 53. has_more is the only reliable stop signal, and it stays true past total - offset=5000 still returns records and only flips to false at offset 5095.",
 "Paged past total out of habit and the server kept serving records. Then walked the offset boundary one page at a time until has_more went false, on each endpoint, filtered and unfiltered.",
 "Following the documented recipe drops the last 298 listings, 123 rentals and 35 projects. Every count in this submission would be ~5.9% low, and the tail records are not a random sample - they include corrupt and fake ones.",
 ["SQU-5001161","ZER-5000634","100-5002777","100-5001259","ZER-5002803","100-5003979","DWE-5001778","ZER-5002174","DWE-5002951","100-5002752","SQU-5004438","DWE-5004742","ZER-5003520","MAG-5003397","100-5004065","ZER-5000834","DWE-5005078","ZER-5004390","ZER-5000386","100-5004990"])

# ---------- SORTING ----------
add("/v1/listings","sorting",
 "order takes asc (default) or desc",
 "order is validated (order=sideways 422s with \"Input should be 'asc' or 'desc'\") and then ignored. sort_by=price&order=desc returns the identical ten records as order=asc, starting at the global minimum -64640000. Same on /v1/rentals (6600 first for both) and /v1/projects (price_max 1.82 first for both).",
 "Requested each sortable field at asc and desc and diffed the result lists. Identical on all three collection endpoints.",
 "\"Most expensive first\" is impossible server side. My app sorts client side over the full dataset.")

add("/v1/listings","sorting",
 "sort_by=posted_at sorts by posted_at",
 "It orders by calendar date only; within a date the time of day is unordered. The first page of sort_by=posted_at reads 2026-01-13 at 04:02, 20:23, 21:22, 08:08, 02:57, 14:12 ... while the earliest timestamp in the dataset, 2026-01-13T01:56:00, appears nineteenth.",
 "Sorted by posted_at, then compared the returned sequence against the minimum posted_at in my full local copy.",
 "\"Newest first\" is only accurate to the day. Combined with order being ignored, you cannot get newest-first from the server at all.")

add("/v1/listings","sorting",
 "sort_by=carpet_area sorts by carpet_area",
 "The returned carpet_area values are not monotonic: 31, 340, 32, 342, 32, 359, 359, 362, 34, 365. The server is sorting correctly on the square-foot value it stores, but serves magichomes areas converted to square metres, so the number in the payload is not the number it sorted on. Reconstructing the pre-conversion square-foot values (334, 340, 341, 342, 343, 359, 359, 362, 363, 365, ...) makes the sequence perfectly monotonic.",
 "The sort looked broken, so I tried to find a conversion factor that made the sequence monotonic. No single factor works on the rounded integers, but assuming the server sorts on unrounded square feet and rounds to whole square metres on output reproduces the exact order. That is independent confirmation of the unit bug below - the sort order is a witness to the value the API is hiding.",
 "The endpoint is not broken; the units are. But you cannot page through area-sorted results and trust the numbers you see.",
 ["MAG-5002539","SQU-5002167","MAG-5002069","ZER-5002207","MAG-5001155","MAG-5003462","SQU-5003432","DWE-5004921","MAG-5001511","MAG-5004708"])

# ---------- UNITS ----------
add("/v1/listings","units",
 "\"Area: Square feet, integer, everywhere in the API.\"",
 "carpet_area and super_built_up_area are in square METRES, not square feet, for every magichomes listing posted on or after 2026-06-01 - 455 of 5100 records. The cutover is exact: no magichomes listing dated before 2026-06-01 has an area under 300, and none dated on or after it has an area over 300. No other source is affected (minimum carpet_area is 375, 362, 340 and 342 on the other four sites).",
 "I did not find this by reading a record - a 107 sq ft 3 BHK looks like one bad row. I found it by computing price per carpet area for all 5100 listings and noticing the distribution was bimodal, then splitting by source: every outlier carried a MAG- prefix. But magichomes was split too - 455 tiny, 541 normal - so the rule 'magichomes is metric' was wrong. Cross-tabbing the two magichomes groups against every field found a clean break on posted_at at 2026-06-01 with zero overlap: the site changed units mid-year. Converting the affected rows at 10.7639 puts their price per square foot at a median of about 30,300, against 31,053 for the rest of the market.",
 "Largest numeric error in the dataset. Question 6 answered without this conversion is 63966.39 rupees/sqft; with it, 32586.84 - out by a factor of two. Any area filter, any sort, any 'price per sqft' in a UI is wrong for 9% of inventory.",
 sqm_ids[::len(sqm_ids)//20][:20])   # spread across the whole post-cutover range

add("/v1/projects","units",
 "\"price_min and price_max are in rupees.\" and \"Money: Indian rupees, integer, everywhere in the API.\"",
 "They are floats in CRORES of rupees. price_max ranges 1.82 to 12.44 and price_min 1.00 to 99.30. Dividing the highest listing price inside each project by price_max x 10^7 gives a median of 0.967, i.e. the project ceiling really is the crore figure.",
 "The values were three orders of magnitude too small to be rupees and were not integers, which the conventions table forbids twice over. I checked them against the listings that carry each project_id rather than guessing at the unit.",
 "A projects screen showing price_max as rupees displays a 12.44 crore flagship as twelve rupees. Question 7 requires the conversion.",
 ["P50016","P50451","P50150","P50443","P50494","P50303","P50050","P50179","P50445","P50321"])

add("/v1/projects","units",
 "price_min and price_max are in the same unit",
 "Six projects report price_min in LAKHS while price_max is in crores, which is why their price_min is numerically larger than their price_max: P50247 has price_min 99.3 and price_max 4.24. Read as 99.3 lakh (0.993 crore) against 4.24 crore, the range is sane. These are the only six records in the file where price_min > price_max.",
 "Sorted projects by price_min and found a gap - 584 values under 20 and six between 90 and 100. Checked those six against price_max and against their own listings.",
 "A price range filter on projects silently excludes or mis-ranks these six.",
 lakh_projects)

# ---------- TIMESTAMPS ----------
add("*","timestamps",
 "\"Timestamps: ISO 8601, UTC, Z suffix, everywhere in the API.\"",
 "posted_at is a naive local timestamp with no timezone designator at all - 19 characters, e.g. \"2026-06-21T16:40:00\". Zero of the 5100 listings and 2100 rentals carry a Z or an offset. The server's own clock, by contrast, is explicit: /health returns \"2026-09-12T23:13:55+05:30\" with \"timezone\":\"Asia/Kolkata\" and \"reference_date\":\"2026-09-10T00:00:00+05:30\". The record timestamps are therefore Asia/Kolkata local time, not UTC.",
 "Checked every posted_at for a Z or an offset - none has one. Then looked for a behavioural tell: the hour-of-day histogram is flat (192-231 per hour across all 24), so there is no activity pattern to shift, which rules out inferring the zone from the data and leaves the server's declared zone as the only evidence. /health declaring +05:30 and Asia/Kolkata settles it.",
 "Anyone who parses these as UTC and converts to IST shifts every record forward 5h30m. For question 8 that moves the answer from 167 to 152.")

# ---------- COMPLETENESS ----------
add("/v1/listings","completeness",
 "\"Returns active sale listings in your city. Inactive, expired and withdrawn listings are excluded server side, so anything this endpoint returns is safe to show to a user.\"",
 "Nothing is excluded. The endpoint returns an undocumented boolean is_live, and 1083 of the 5100 retrievable records have is_live false - 21% of the feed. There is no filter parameter to exclude them; is_live=true is accepted and ignored (total stays 4802).",
 "The listing object had a field the documentation does not mention. Counted it, then tried to filter on it and found the parameter was ignored.",
 "A frontend that trusts the documentation shows a fifth of its inventory as available when it is not. is_live also turns out to be the key to question 10 - project total_listings counts live listings, not all of them.",
 notlive[:20])

# ---------- DUPLICATES ----------
add("/v1/listings","duplicates",
 "\"Every listing_id is globally unique, and each listing corresponds to exactly one physical property.\"",
 "listing_id is genuinely unique - all 5100 differ - but the second half is false. 638 records are re-postings of a property already present under a different listing_id, leaving 4462 distinct properties. Each duplicate pair shares the apartment name (case and punctuation vary: \"CENTURY SERENITY\" vs \"Century Serenity\"), locality, bedroom, floor, bathroom, balcony, total_floors, facing_direction, furnishing, property_type and covered_parking - all eleven agree on 687 of 687 pairs - with carpet areas within 1% and coordinates jittered by about 0.0005 degrees (roughly 50m). Price, posted_at, website and seller phone differ, which is what a cross-portal repost looks like.",
 "Started from the obvious key and it was wrong: 272 groups share coordinates EXACTLY, and I nearly reported those. They are not duplicates - within those groups the floor differs in 101 of 101 pairs and the areas differ by a median of 4.6%; they are different flats that happen to share a building coordinate. The real duplicates are the ones whose coordinates are close but NOT equal. Plotting geographic distance for records matching on name, locality and bedroom shows a tight cluster from 0.0001 to 0.0013 degrees and then nothing at all until 0.0074 - a clean gap - and every pair inside that cluster agrees on all eleven structural attributes.",
 "Counting records as properties overstates distinct supply by 14%, and a deduplicated list is what a user actually wants to browse. This is the answer to question 2.",
 dup_ev)

# ---------- DATA QUALITY ----------
add("/v1/listings","data_quality",
 "Listing objects describe real properties; is_verified means \"our operations team has checked the listing\"",
 "77 records describe something physically impossible, in seven disjoint classes of exactly 11 records each: 11 with a negative price (down to -64,640,000); 11 priced under 1 lakh (17,470 to 44,440, which are monthly rents, not Mumbai sale prices); 11 whose carpet_area exceeds super_built_up_area; 11 whose floor exceeds total_floors; 11 posted after the reference moment, up to 2027-07-02; 11 with latitude and longitude transposed (latitude 72.77, longitude 18.96 - the Barents Sea); and 11 non-plot dwellings with zero bedrooms AND zero bathrooms at 1,500 sq ft and 5 crore.",
 "Enumerated every invariant I could state about a home and counted violations. The seven counts coming back as exactly 11 each, with no record in two classes, is what told me these were seeded rather than noise - so I went looking for more classes of 11 and found the bedroom/bathroom one that way. Plots legitimately have 0 bedrooms, 0 bathrooms and 0 floors (202 of them), so I excluded property_type=plot before counting.",
 "These are the answer to question 4 and must be excluded from question 6 - the negative prices alone drag a naive mean price per sqft down.",
 [i for v in cls.values() for i in sorted(v)[:3]][:20])   # ~3 from each of the 7 impossibility classes

add("/v1/rentals","data_quality",
 "The rental object carries both a title and a locality describing the same property",
 "title names a different locality from the locality field in 1911 of 2100 rentals - 91%. R5000001 is titled \"3 BHK for rent in Powai\" with \"locality\": \"borivali west\". The bedroom count in the title is always right (0 mismatches), so only the locality half of the title is junk.",
 "Spotted it in the very first rental I printed, then parsed \"N BHK for rent in X\" across all 2100 and compared both halves against the structured fields.",
 "Any UI that renders the title as a heading tells the user the wrong neighbourhood. It also matters for question 5: summing rent by title locality gives 7,192,900, by the locality field 8,000,100. The structured field is the one the endpoint filters on, so it is the one I trusted.",
 title_mismatch[:20])

# ---------- FRAUD ----------
add("/v1/listings","fraud",
 "posted_by_contact is \"the seller's verified contact number\", and is_verified means the operations team checked the listing",
 "190 listings exist to harvest enquiries. They sit on just five phone numbers, exactly 38 listings each: +912007133812, +912003561453, +912000039837, +912007145137 and +912007219058. Every one of the 190 is is_verified true and is_live true and posted_by agent; each phone posts under 3 to 7 different seller names (one number is Skyline Homes, Metro Realtors, Nexus Properties, Crown Estates, Urban Nest, Arjun Reddy and Shreya Gupta at once); each covers all ten localities; and their median price per square foot is 14,800-18,000 against a market median of 31,769. No other phone number in the dataset with 10 or more listings is 100% verified - the next-busiest agent, with 33 listings, is verified on 20 of them.",
 "Bait pricing alone does not separate them - 1,549 honest listings sit below the most expensive fake, so a price threshold shreds precision. What separates them is the conjunction: I grouped all 5100 listings by phone and looked at listing count, verified rate, distinct seller names and locality spread together. The five fall out as a block and nothing sits between them and the rest. \"100% verified AND 10+ listings\" alone returns exactly these five numbers and nothing else, which is the cleanest single discriminator and an ugly one - the verification flag is positively correlated with fraud here.",
 "This is question 9, and it inverts the meaning of is_verified: the only sellers with a perfect verification record are the fraudulent ones. A UI that surfaces a verified badge is actively promoting the bait.",
 [i for ph in ["+912007133812","+912003561453","+912000039837","+912007145137","+912007219058"]
     for i in sorted(r["listing_id"] for r in L if r["posted_by_contact"]==ph)[:4]])   # 4 per fake phone

# ---------- CONSISTENCY ----------
add("/v1/projects","consistency",
 "\"total_listings is the number of listings currently available in the project. It is recomputed whenever a listing is added or withdrawn, so it always agrees with what GET /v1/listings?project_id=... returns.\"",
 "It disagrees for 166 of 590 projects. The documented check cannot even be run: project_id is not a filter on /v1/listings - the parameter is accepted and ignored, and ?project_id=P50001 returns all 4802/5100 records. Counting from a full local copy, total_listings matches the number of LIVE listings carrying that project_id for 424 of 590 projects, so that is the intended definition; it is simply stale for the other 166. Counting all listings regardless of is_live matches only 144.",
 "Tried the documented URL first, saw total unchanged, and realised the filter does not exist. Then tested every plausible definition of the count against all 590 projects: live-only gives 424 exact matches with the residual scattered either side of zero, all-listings gives 144, verified-only 91. The rule that fits most of the data is live-only, and the 166 it does not fit are the answer to question 10.",
 "A project page cannot show how many units are on sale without recounting from the listings feed. This is question 10.",
 wrong_ct[:20])

add("/v1/listings","consistency",
 "total is the exact count for your filters, and the documentation describes no other source for locality counts",
 "The undocumented /v1/localities endpoint reports listing_count per locality, and those numbers are the true retrievable counts - chembur 542, malad west 533, powai 484 - each matching a full paged crawl exactly. The total field on /v1/listings?locality=... disagrees with them for all ten localities (powai 456 vs 484). Two endpoints in the same API give two different counts for the same question, and the undocumented one is right.",
 "Crawled every locality to the end and compared three numbers: my count, /v1/localities, and the total field. The first two agree everywhere; the third is low everywhere.",
 "/v1/localities is a free correctness oracle for pagination, and it is not in the documentation.",
 powai_tail)

# ---------- MISSING ENDPOINTS ----------
add("/v1/analytics/summary","missing_endpoint",
 "Pre-computed aggregates for your city - total_listings, median_price, median_price_per_sqft, by_locality, by_bhk",
 "404 Not Found. Nothing is served at /v1/analytics/summary, /v1/analytics, /v1/summary, /v1/stats, /v1/insights or any other spelling I tried. The endpoint does not exist and there is no replacement.",
 "Called it, got 404, then swept a dozen plausible paths for an aggregates endpoint before concluding it was never shipped.",
 "The brief requires an insights screen built on this endpoint. I compute all of it client side from the full dataset instead - which is the better outcome anyway, because the medians have to be computed on unit-corrected areas that a precomputed endpoint would have got wrong.")

add("/v1/favourites","missing_endpoint",
 "GET /v1/favourites, POST /v1/favourites with body {\"id\": \"...\"}, DELETE /v1/favourites/{id}",
 "404 at all three. The working endpoint is /v1/saved: GET /v1/saved returns {count, results}, POST /v1/saved returns 201 {\"ok\":true,\"listing_id\":...,\"saved_count\":N}, DELETE /v1/saved/{id} returns 200. The POST body key is listing_id, not id - sending {\"id\": ...} returns 422 \"Field required: body.listing_id\". Saving an id that does not exist returns 404 \"no such listing in your city\", and deleting one you have not saved returns 404 \"not in your saved list\".",
 "404 on the documented path, so I swept /v1/saved, /v1/favorites, /v1/bookmarks, /v1/wishlist and /v1/me/favourites. /v1/saved answered 200. Then exercised the full add/list/remove cycle and confirmed isolation by logging in as demo2 and seeing an empty list.",
 "Saved listings is a required feature and none of the documented calls work. Favourites are correctly scoped per user and survive re-login, which the documentation does not actually promise.")

add("/v1/listing/{id}","missing_endpoint",
 "GET /v1/listing/{listing_id} returns a single listing",
 "404. The path is plural: GET /v1/listings/{listing_id}. The record it returns is byte-identical to the one in the collection response. /v1/rentals/{id} and /v1/projects/{id} are plural too, while the documentation's /v1/rental/{id} and /v1/project/{id} singular forms both 404.",
 "Called the documented singular path, got 404, tried the plural.",
 "Detail pages 404 if you follow the documentation. Trivial to fix once seen.")

add("/v1/listings/{id}/similar","missing_endpoint",
 "\"Up to ten comparable listings - same locality, same bedroom count, price within 15%. Useful for a 'you may also like' strip on the detail page.\"",
 "404, under both /v1/listings/{id}/similar and /v1/listing/{id}/similar. It was never shipped.",
 "Called it on a listing id I had just fetched successfully, so a 404 could not be a bad id.",
 "My detail page computes comparables client side on the documented rule, over unit-corrected areas.")

# ---------- UNDOCUMENTED ENDPOINTS ----------
add("/v1/saved","undocumented_endpoint",
 "Not in the documentation - it describes /v1/favourites instead",
 "The real favourites API. GET returns {count, results} with full listing objects; POST {\"listing_id\": ...} returns 201 with a running saved_count; DELETE /v1/saved/{id} returns 200. Scoped per user - demo1's saved list is invisible to demo2 - and it survives logout and re-login.",
 "Found it by sweeping candidate paths after /v1/favourites 404ed.",
 "Without it the saved-listings requirement cannot be met at all.")

add("/v1/me","undocumented_endpoint",
 "Not in the documentation",
 "Returns {user:{email}, city_id: 5, city: \"mumbai\", assigned_locality: \"powai\", reference_date: \"2026-09-10T00:00:00+05:30\"} plus a note that the key is city-scoped.",
 "Swept for a session/identity endpoint after noticing the login response carried no profile data.",
 "Lets the frontend discover the city, the assigned locality and the grading reference date at runtime instead of hard-coding them. My app reads all three from here.")

add("/v1/localities","undocumented_endpoint",
 "Not in the documentation",
 "Returns the ten localities in the city with a listing_count each, and those counts are the true retrievable counts - unlike the total field on /v1/listings.",
 "Swept for a taxonomy endpoint so the locality filter would not need hard-coded values.",
 "Populates the locality filter without hard-coding, and doubles as an independent check that a crawl reached the end.")

add("/health","undocumented_endpoint",
 "Documented only at /health",
 "The same payload is also served at /v1/health, which the documentation does not mention.",
 "Included both spellings in the path sweep.",
 "None. Noted for completeness.")

json.dump(F, open("data/findings.json","w"), indent=2)
print("findings:",len(F))
print(collections.Counter(f["category"] for f in F).most_common())
for f in F: print(f"  {f['category']:24} {f['endpoint']:32} evidence={len(f['evidence'])}")
