import sys, json
sys.path.insert(0, "scripts")
from ivy import Ivy

c = Ivy()
candidates = [
 "/v1/analytics/summary","/v1/analytics","/v1/analytics/summary/","/v1/summary","/v1/stats",
 "/v1/analytics/city","/v1/analytics/overview","/v1/insights","/v1/analytics/localities",
 "/v1/favourites","/v1/favorites","/v1/saved","/v1/user/favourites","/v1/users/me/favourites",
 "/v1/me","/v1/me/favourites","/v1/bookmarks","/v1/wishlist",
 "/v1/listing/SQU-5004678","/v1/listings/SQU-5004678","/v1/listings/SQU-5004678/similar",
 "/v1/listing/SQU-5004678/similar","/v1/rentals/R5000001","/v1/rental/R5000001",
 "/v1/projects/P50001","/v1/project/P50001","/v1/projects/P50001/listings",
 "/v1/localities","/v1/cities","/v1/city","/v1/search","/v1/enquiries","/v1/leads",
 "/docs","/openapi.json","/redoc","/v1","/v1/health","/health",
 "/auth/me","/auth/refresh","/auth/logout","/v1/auth/login",
]
for p in candidates:
    st, body = c.get(p)
    s = json.dumps(body)[:220] if body is not None else ""
    print(f"{st}  {p}\n      {s}\n")
print("calls:", c.calls)
