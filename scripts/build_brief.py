# -*- coding: utf-8 -*-
"""Generates the pre-submission brief from the same data the submission uses."""
import json, html, collections

OUT = "/private/tmp/claude-501/-Users-devanshsinghal/e2caabe8-c6ea-4ece-8364-1dc8de453142/scratchpad/ivy-brief.html"
F = json.load(open("data/findings.json"))
A = json.load(open("data/answers.json"))
e = html.escape

CAT_LABEL = {
    "auth": "Authentication", "pagination": "Pagination", "units": "Units",
    "sorting": "Sorting", "timestamps": "Timestamps", "duplicates": "Duplicates",
    "completeness": "Completeness", "data_quality": "Data quality", "fraud": "Fraud",
    "consistency": "Consistency", "missing_endpoint": "Documented but absent",
    "undocumented_endpoint": "Present but undocumented", "filters": "Filters",
}
ORDER = ["auth","pagination","units","timestamps","sorting","completeness","duplicates",
         "data_quality","fraud","consistency","missing_endpoint","undocumented_endpoint"]

ANSWER_ROWS = [
    ("1", "Retrievable listing records", f'{A["total_listing_records"]:,}',
     "Paged to <code>has_more:false</code>. The server’s <code>total</code> says 4,802.", "high"),
    ("2", "Distinct properties", f'{A["unique_properties"]:,}',
     "638 records re-post a property already listed. ±1% allowed.", "medium"),
    ("3", "Records with <code>is_live</code> true", f'{A["active_listings"]:,}',
     "Plain count. The docs claim non-live records are filtered out server side.", "high"),
    ("4", "Impossible listing records", f'{len(A["corrupt_listing_ids"])} ids',
     "Seven disjoint classes of exactly 11. Scored on precision and recall.", "high"),
    ("5", "Monthly rent across Powai", f'₹{A["total_monthly_rent"]:,}',
     "All 222 Powai rentals. Rent needed no unit correction.", "high"),
    ("6", "Mean ₹/sq ft, live 2 BHK", f'₹{A["avg_price_per_sqft_2bhk"]:,}',
     "Excludes Q4 and Q9. <strong>₹63,966 without the m² fix.</strong> ±1%.", "high"),
    ("7", "Costliest project", f'{A["costliest_project"]["project_id"]} · ₹{A["costliest_project"]["price_max_inr"]:,}',
     "<code>price_max</code> 12.44 arrives in crores, not rupees. ±1%.", "high"),
    ("8", "Posted in the 7 days before the reference", str(A["listings_last_7_days"]),
     "Reading naive timestamps as IST. As UTC it would be 152 — the one real judgement call.", "medium"),
    ("9", "Enquiry-farm listings", f'{len(A["fake_listing_ids"])} ids',
     "Five numbers × 38 listings, every one “verified”. Scored on precision and recall.", "high"),
    ("10", "Projects with a wrong listing count", str(A["projects_with_wrong_listing_count"]),
     "<code>total_listings</code> counts live listings; it fits 424 of 590.", "high"),
]

STEPS = [
    ("Fill in your details",
     "Tell Claude your full name, the <strong>@mnnit.ac.in</strong> address you registered with, and your GitHub "
     "username. <code>submission.json</code> and the README still carry <code>TODO</code> placeholders, and the "
     "commit history needs a real author identity before any of it is pushed.", "2 min"),
    ("Create the GitHub repository",
     "Make a <strong>public</strong> repo — the assignment requires public. Do not initialise it with a README, "
     "licence or .gitignore; the local repo already has them and an initialised repo forces an awkward merge. "
     "Copy the URL it gives you.", "2 min"),
    ("Push",
     "Claude will run the <code>git remote add</code> and <code>git push -u origin main</code> for you once the "
     "repo exists. Then open the repo in a browser and confirm <code>submission.json</code> is visible at the root "
     "— the graders look for it there by name.", "3 min"),
    ("Deploy to Vercel",
     "Sign in at <strong>vercel.com</strong> with GitHub → <em>Add New… → Project</em> → import the repo. Set "
     "<strong>Root Directory</strong> to <code>app</code>; framework, build command and output directory are "
     "detected automatically. Add the environment variable <code>VITE_IVY_API_KEY</code> with your key before the "
     "first deploy, or the built site will have no key.", "8 min"),
    ("Test the deployed site yourself",
     "Open the Vercel URL in a fresh private window. Log in as demo1, wait for the catalogue to finish loading, "
     "star a listing, reload the page, and confirm you are still signed in and the star is still there. Then check "
     "the Insights screen shows the same ten numbers as the table above.", "5 min"),
    ("Put the two URLs back into the repo",
     "The live URL has to go into <code>submission.json</code> as <code>demo_url</code> and into the README. Claude "
     "will regenerate and push them — a submission whose <code>demo_url</code> is a placeholder reads as unfinished.", "3 min"),
    ("Submit the Google Form",
     "<strong>forms.gle/e8L79HaN3MbJJact7</strong>, before <strong>23:59 IST on Monday 14 September</strong>. "
     "Submit with time to spare; if you find something afterwards you can push to the repo, but you cannot "
     "resubmit the form.", "5 min"),
]

KNOW = [
    ("The unit bug is the whole assignment in miniature",
     "magichomes switched <code>carpet_area</code> from square feet to square metres on 2026-06-01 — 455 records. "
     "Nothing in any single response says so. Finding it took noticing the price-per-area distribution was bimodal, "
     "splitting by source, discovering the source was <em>itself</em> split, and only then finding the date cutover. "
     "If you get asked one “how did you actually work it out” question, this is the answer to give: the first rule "
     "that fit — “magichomes is metric” — was wrong for 541 of its 996 records, and the answer was in what it got wrong."),
    ("The broken sort is independent proof of the unit bug",
     "<code>sort_by=carpet_area</code> returns 31, 340, 32, 342, 32 — apparently unsorted. It is not: the server sorts "
     "on the square-foot value it stores and converts to m² only on output. Reconstructing the pre-conversion values "
     "gives 334, 340, 341, 342, 343 — perfectly ordered. This is the strongest single thing in the submission, "
     "because it turns an inference into a demonstration."),
    ("Fraud could not be found by price",
     "1,549 honest listings undercut the most expensive fake, so any price threshold destroys precision — and "
     "precision is scored as hard as recall. The signal is a conjunction: 38 listings per number, 100% verified, "
     "3–7 seller names on one phone, all ten localities, half the market rate. Worth saying out loud that "
     "<code>is_verified</code> turns out to be <em>positively correlated with fraud</em> here."),
    ("The near-miss on duplicates is worth admitting",
     "272 groups share coordinates exactly and they are <em>not</em> duplicates — different flats in one building, "
     "floors differ in 101 of 101 pairs. The real duplicates are the pairs that are close but not equal, clustered "
     "at 0.0001–0.0013 degrees with a clean gap before 0.0074. Volunteering the wrong turn is more convincing than "
     "presenting the answer as if it were obvious."),
    ("Question 8 is a judgement call, not a fact",
     "<code>posted_at</code> has no timezone marker at all. IST gives 167, UTC gives 152. I went with IST because "
     "<code>/health</code> declares <code>+05:30</code> and <code>Asia/Kolkata</code>, and because the hour-of-day "
     "histogram is dead flat so there is no evidence pointing anywhere else. Say this is the one you are least sure "
     "of — the README already does."),
    ("Have the negative results ready",
     "They asked for what turned out to be fine, and it is 10% of the final weighting. Seller descriptions are "
     "<em>perfectly</em> consistent with the structured fields — 0 mismatches on five attributes across 5,100 "
     "records — which is the opposite of what you would expect. Rental rents and deposits needed no correction. "
     "<code>bathroom=0</code> is legitimate for all 202 plots."),
    ("Know why the app pulls the whole catalogue",
     "It makes ~160 requests on login, against a 1,200/min limit. That is deliberate: <code>total</code> is wrong, "
     "<code>order</code> is ignored and <code>sort_by=carpet_area</code> orders on a hidden value, so server-side "
     "paging and sorting cannot produce correct numbers. Loading everything is what makes every figure on screen right."),
    ("The session requirement is a trap and it is handled",
     "Tokens last 900 seconds, not the documented 86,400, and the docs say there is no refresh flow while the login "
     "response literally contains <code>refresh_token</code> and <code>refresh_url</code>. The brief's “still working "
     "thirty minutes after you logged in” is testing exactly this. The app refreshes 60s early, on a timer, and "
     "recovers from a 401 mid-flight — all three paths were tested in a real browser."),
]

def confidence_chip(level):
    label = {"high": "solid", "medium": "±1% band"}[level]
    return f'<span class="chip chip-{level}">{label}</span>'

by_cat = collections.OrderedDict()
for c in ORDER:
    rows = [f for f in F if f["category"] == c]
    if rows: by_cat[c] = rows

findings_html = []
for cat, rows in by_cat.items():
    items = []
    for f in rows:
        ev = ""
        if f["evidence"]:
            shown = ", ".join(e(x) for x in f["evidence"][:6])
            more = f" <span class='ev-more'>+{len(f['evidence']) - 6} more</span>" if len(f["evidence"]) > 6 else ""
            ev = f"<p class='ev'><span class='ev-label'>Evidence</span> <code>{shown}</code>{more}</p>"
        items.append(f"""
        <article class="finding">
          <h4><code class="ep">{e(f['endpoint'])}</code></h4>
          <div class="claims">
            <div class="claim claim-doc"><span class="claim-label">The documentation says</span><p>{e(f['documented'])}</p></div>
            <div class="claim claim-real"><span class="claim-label">The API actually does</span><p>{e(f['actual'])}</p></div>
          </div>
          <p class="how"><span class="how-label">How it surfaced</span> {e(f['how_found'])}</p>
          {ev}
        </article>""")
    findings_html.append(f"""
      <section class="cat">
        <header class="cat-head">
          <h3>{CAT_LABEL[cat]}</h3><span class="count">{len(rows)}</span>
        </header>
        {''.join(items)}
      </section>""")

answers_html = "".join(
    f"""<tr>
      <td class="num">{n}</td>
      <td class="q">{q}</td>
      <td class="a">{v}</td>
      <td class="conf">{confidence_chip(c)}</td>
      <td class="note">{note}</td>
    </tr>""" for n, q, v, note, c in ANSWER_ROWS)

steps_html = "".join(
    f"""<li class="step">
      <div class="step-head"><h3>{t}</h3><span class="mins">{m}</span></div>
      <p>{b}</p>
    </li>""" for t, b, m in STEPS)

know_html = "".join(
    f"""<article class="know">
      <h3>{t}</h3><p>{b}</p>
    </article>""" for t, b in KNOW)

CSS = """
:root {
  --ground:#f2f4f3; --panel:#ffffff; --panel-2:#e9edeb;
  --ink:#141d1b; --ink-2:#3f524e; --ink-3:#6d807b;
  --line:#d6dedb; --line-2:#c2cec9;
  --accent:#0d5c50; --accent-soft:#e2efec;
  --doc:#9a4a16; --doc-soft:#f7ebe2;
  --real:#0d5c50; --real-soft:#e2efec;
  --solid:#1c6b46; --band:#8a6510;
  --shadow:0 1px 2px rgba(20,29,27,.05), 0 8px 24px -16px rgba(20,29,27,.28);
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --ground:#0c1211; --panel:#121a18; --panel-2:#18211f;
    --ink:#e4ebe8; --ink-2:#a8b8b3; --ink-3:#7d8f8a;
    --line:#223029; --line-2:#2d3d37;
    --accent:#5fc4ae; --accent-soft:#152a26;
    --doc:#e39a63; --doc-soft:#2a1d13;
    --real:#5fc4ae; --real-soft:#152a26;
    --solid:#63c795; --band:#d7ab52;
    --shadow:0 1px 2px rgba(0,0,0,.4), 0 8px 24px -16px rgba(0,0,0,.8);
  }
}
:root[data-theme="dark"] {
  --ground:#0c1211; --panel:#121a18; --panel-2:#18211f;
  --ink:#e4ebe8; --ink-2:#a8b8b3; --ink-3:#7d8f8a;
  --line:#223029; --line-2:#2d3d37;
  --accent:#5fc4ae; --accent-soft:#152a26;
  --doc:#e39a63; --doc-soft:#2a1d13;
  --real:#5fc4ae; --real-soft:#152a26;
  --solid:#63c795; --band:#d7ab52;
  --shadow:0 1px 2px rgba(0,0,0,.4), 0 8px 24px -16px rgba(0,0,0,.8);
}
* { box-sizing:border-box; }
body {
  margin:0; background:var(--ground); color:var(--ink);
  font-family:"IBM Plex Sans", ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  font-size:16px; line-height:1.6; -webkit-font-smoothing:antialiased;
}
.wrap { max-width:1060px; margin:0 auto; padding:0 24px 96px; }
code, .mono { font-family:"IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, monospace; }
code { font-size:.86em; background:var(--panel-2); padding:.1em .38em; border-radius:4px; }
h1,h2,h3,h4 { font-family:"Newsreader", Georgia, "Times New Roman", serif; font-weight:500; text-wrap:balance; margin:0; }
p { margin:0; }

/* masthead */
.mast { padding:64px 0 40px; border-bottom:1px solid var(--line); }
.eyebrow {
  font-size:.72rem; letter-spacing:.16em; text-transform:uppercase;
  color:var(--accent); font-weight:600; margin-bottom:18px;
}
.mast h1 { font-size:clamp(2.3rem,5.4vw,3.6rem); line-height:1.06; letter-spacing:-.022em; max-width:19ch; }
.mast .sub { margin-top:20px; font-size:1.08rem; color:var(--ink-2); max-width:62ch; }
.meta { display:flex; flex-wrap:wrap; gap:10px; margin-top:28px; }
.meta div {
  background:var(--panel); border:1px solid var(--line); border-radius:7px;
  padding:8px 13px; display:flex; gap:9px; align-items:baseline; box-shadow:var(--shadow);
}
.meta dt { font-size:.7rem; text-transform:uppercase; letter-spacing:.08em; color:var(--ink-3); margin:0; }
.meta dd { margin:0; font-weight:600; font-size:.9rem; }
.meta dd.mono { font-size:.84rem; }

section.block { padding-top:60px; }
.block > h2 {
  font-size:1.75rem; letter-spacing:-.015em; padding-bottom:10px;
  border-bottom:2px solid var(--ink); display:inline-block; margin-bottom:8px;
}
.block > .intro { color:var(--ink-2); max-width:66ch; margin:14px 0 26px; }

/* answers */
.table-scroll { overflow-x:auto; border:1px solid var(--line); border-radius:10px; background:var(--panel); box-shadow:var(--shadow); }
table { border-collapse:collapse; width:100%; font-size:.92rem; min-width:720px; }
th, td { text-align:left; padding:13px 16px; border-bottom:1px solid var(--line); vertical-align:top; }
thead th {
  font-size:.68rem; text-transform:uppercase; letter-spacing:.1em;
  color:var(--ink-3); font-weight:600; background:var(--panel-2); white-space:nowrap;
}
tbody tr:last-child td { border-bottom:0; }
td.num { font-family:"IBM Plex Mono", monospace; color:var(--ink-3); width:34px; }
td.q { font-weight:500; min-width:200px; }
td.a { font-family:"IBM Plex Mono", monospace; font-weight:600; font-variant-numeric:tabular-nums; white-space:nowrap; color:var(--accent); }
td.note { color:var(--ink-2); font-size:.86rem; min-width:260px; }
.chip {
  font-size:.68rem; padding:.16em .55em; border-radius:99px; white-space:nowrap;
  border:1px solid currentColor; font-weight:600;
}
.chip-high { color:var(--solid); } .chip-medium { color:var(--band); }

/* steps */
ol.steps { list-style:none; margin:0; padding:0; display:flex; flex-direction:column; gap:0; counter-reset:s; }
.step {
  counter-increment:s; position:relative; padding:22px 0 22px 62px;
  border-bottom:1px solid var(--line);
}
.step:last-child { border-bottom:0; }
.step::before {
  content:counter(s,decimal-leading-zero); position:absolute; left:0; top:22px;
  font-family:"IBM Plex Mono", monospace; font-size:.82rem; font-weight:600;
  color:var(--accent); background:var(--accent-soft);
  width:38px; height:38px; display:grid; place-items:center; border-radius:50%;
}
.step-head { display:flex; align-items:baseline; justify-content:space-between; gap:16px; margin-bottom:5px; }
.step-head h3 { font-size:1.14rem; }
.mins { font-family:"IBM Plex Mono", monospace; font-size:.74rem; color:var(--ink-3); white-space:nowrap; }
.step p { color:var(--ink-2); max-width:70ch; }

/* know */
.knows { display:grid; grid-template-columns:repeat(auto-fit,minmax(320px,1fr)); gap:14px; }
.know {
  background:var(--panel); border:1px solid var(--line); border-radius:10px;
  padding:20px 22px; box-shadow:var(--shadow);
}
.know h3 { font-size:1.08rem; margin-bottom:8px; letter-spacing:-.01em; }
.know p { color:var(--ink-2); font-size:.92rem; }

/* findings */
.cat { margin-bottom:34px; }
.cat-head { display:flex; align-items:center; gap:12px; margin-bottom:14px; }
.cat-head h3 { font-size:1.3rem; letter-spacing:-.01em; }
.count {
  font-family:"IBM Plex Mono", monospace; font-size:.74rem; font-weight:600;
  color:var(--accent); background:var(--accent-soft);
  border-radius:99px; padding:.15em .62em;
}
.cat-head::after { content:""; flex:1; height:1px; background:var(--line); }
.finding {
  background:var(--panel); border:1px solid var(--line); border-radius:10px;
  padding:18px 20px; margin-bottom:10px; box-shadow:var(--shadow);
}
.finding h4 { margin-bottom:13px; }
code.ep { font-size:.86rem; background:var(--panel-2); color:var(--ink); padding:.2em .5em; border-radius:5px; font-weight:600; }
.claims { display:grid; grid-template-columns:1fr 1fr; gap:1px; background:var(--line); border-radius:8px; overflow:hidden; }
@media (max-width:720px) { .claims { grid-template-columns:1fr; } }
.claim { padding:13px 15px; background:var(--panel); }
.claim-label {
  display:block; font-size:.66rem; text-transform:uppercase; letter-spacing:.1em;
  font-weight:700; margin-bottom:6px;
}
.claim-doc { background:var(--doc-soft); }
.claim-doc .claim-label { color:var(--doc); }
.claim-real { background:var(--real-soft); }
.claim-real .claim-label { color:var(--real); }
.claim p { font-size:.88rem; color:var(--ink-2); }
.how { margin-top:13px; font-size:.87rem; color:var(--ink-2); }
.how-label, .ev-label {
  font-size:.66rem; text-transform:uppercase; letter-spacing:.1em;
  font-weight:700; color:var(--ink-3); margin-right:7px;
}
.ev { margin-top:9px; font-size:.8rem; }
.ev code { font-size:.76rem; word-break:break-word; }
.ev-more { color:var(--ink-3); font-size:.76rem; }

footer { margin-top:72px; padding-top:22px; border-top:1px solid var(--line); color:var(--ink-3); font-size:.85rem; }
a { color:var(--accent); }
:focus-visible { outline:2px solid var(--accent); outline-offset:2px; }
@media (prefers-reduced-motion:reduce) { * { animation:none !important; transition:none !important; } }
"""

HTML = f"""<title>Ivy Homes Submission Brief</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,400;6..72,500;6..72,600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<style>{CSS}</style>
<div class="wrap">
  <header class="mast">
    <p class="eyebrow">Ivy Homes · Software Engineering Internship · Round 1</p>
    <h1>Everything to check before you press submit</h1>
    <p class="sub">The ten answers, the {len(F)} places the documentation contradicts the running API, and the
    steps only you can do. Every number here was reproduced against the live API twice — once in Python, once
    independently in the app’s TypeScript.</p>
    <dl class="meta">
      <div><dt>City</dt><dd>Mumbai</dd></div>
      <div><dt>Locality</dt><dd>Powai</dd></div>
      <div><dt>Key</dt><dd class="mono">IVY26-71CA6294F4C1</dd></div>
      <div><dt>Deadline</dt><dd>23:59 IST · Mon 14 Sep</dd></div>
      <div><dt>Findings</dt><dd>{len(F)}</dd></div>
    </dl>
  </header>

  <section class="block">
    <h2>The ten answers</h2>
    <p class="intro">Counts are graded exactly. Questions 2, 6 and 7 allow ±1%. Questions 4 and 9 are scored on
    how much of the real list you found against how much you invented, so both lists are deliberately tight
    rather than padded.</p>
    <div class="table-scroll">
      <table>
        <thead><tr><th></th><th>Question</th><th>Answer</th><th>Confidence</th><th>Why</th></tr></thead>
        <tbody>{answers_html}</tbody>
      </table>
    </div>
  </section>

  <section class="block">
    <h2>What only you can do</h2>
    <p class="intro">In order. Nothing below is done yet — the repo is committed locally but has no remote, and
    the submission file still carries placeholders where your name and the two URLs go.</p>
    <ol class="steps">{steps_html}</ol>
  </section>

  <section class="block">
    <h2>What to know if they ask</h2>
    <p class="intro">Stage 2 is a human reading your code and your history. These are the eight things worth
    being able to say without looking anything up.</p>
    <div class="knows">{know_html}</div>
  </section>

  <section class="block">
    <h2>The {len(F)} findings</h2>
    <p class="intro">One row per discrepancy, grouped the way the assignment’s own category list groups them.
    Each was reproduced directly against the API before it went into <code>submission.json</code> — precision is
    weighted as heavily as recall, so nothing here is a guess.</p>
    {''.join(findings_html)}
  </section>

  <footer>
    Generated from <code>data/findings.json</code> and <code>data/answers.json</code> — the same files that build
    <code>submission.json</code>, so this page cannot drift from what you submit.
  </footer>
</div>"""

open(OUT, "w").write(HTML)
print("wrote", OUT, len(HTML), "bytes")
print("findings rendered:", sum(len(v) for v in by_cat.values()), "in", len(by_cat), "categories")
