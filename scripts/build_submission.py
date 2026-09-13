"""Assembles submission.json from the computed answers and findings."""
import json, os

CANDIDATE = {
    "name": os.environ.get("IVY_NAME", "TODO_YOUR_NAME"),
    "email": os.environ.get("IVY_EMAIL", "TODO_YOUR_COLLEGE_EMAIL"),
    "repo_url": os.environ.get("IVY_REPO", "TODO_REPO_URL"),
    "demo_url": os.environ.get("IVY_DEMO", "TODO_DEMO_URL"),
}

sub = {
    "api_key": "IVY26-71CA6294F4C1",
    "candidate": CANDIDATE,
    "answers": json.load(open("data/answers.json")),
    "findings": json.load(open("data/findings.json")),
}

# the template orders answers a particular way; keep it identical
ORDER = ["total_listing_records","unique_properties","active_listings","corrupt_listing_ids",
         "total_monthly_rent","avg_price_per_sqft_2bhk","costliest_project",
         "listings_last_7_days","fake_listing_ids","projects_with_wrong_listing_count"]
sub["answers"] = {k: sub["answers"][k] for k in ORDER}

json.dump(sub, open("submission.json","w"), indent=2)
print("submission.json written")
print("  answers keys :", len(sub["answers"]))
print("  findings     :", len(sub["findings"]))
print("  corrupt ids  :", len(sub["answers"]["corrupt_listing_ids"]))
print("  fake ids     :", len(sub["answers"]["fake_listing_ids"]))
for k, v in CANDIDATE.items():
    if str(v).startswith("TODO"): print(f"  !! candidate.{k} still a placeholder")
