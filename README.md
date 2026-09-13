# Ivy Homes — Mumbai property explorer

A property browser built on the Ivy Homes property API, plus the answers to the ten
questions and a list of everywhere the published `API_REFERENCE.md` disagrees with the
running service.

- **Candidate:** Madhukar Shyam Tripathi
- **College email:** madhukar.20234096@mnnit.ac.in
- **Live app:** _[Paste your Vercel URL here]_
- **Answers and findings:** [`submission.json`](./submission.json)
- **City:** Mumbai (`city_id` 5) · **Assigned locality:** Powai

---

## Running it

```bash
cd app
npm install
cp .env.example .env      # then put your own IVY26-… key in it
npm run dev               # http://localhost:5173
```

`npm run build` produces a static bundle in `app/dist`. There is no server: the API
sends `Access-Control-Allow-Origin: *`, so the browser talks to it directly.

Sign in with `demo1@ivy.homes`, `demo2@ivy.homes` or `demo3@ivy.homes` and the password
issued with the key.

The analysis that produced the answers lives in [`scripts/`](./scripts) and is plain
Python with no dependencies:

```bash
python3 scripts/dump.py            # pages every collection to the end -> data/raw/
python3 scripts/answers.py         # recomputes all ten answers
python3 scripts/build_findings.py  # regenerates the findings list
```

Every number in `submission.json` comes out of those scripts, and the app recomputes
the same numbers independently in TypeScript. The two implementations agreeing is the
main reason I trust the final metrics.

---

## Methodology: auditing the API

The assignment specifies that the live API is the single source of truth. Because the
service responds deterministically, I pulled the complete dataset locally (~160
requests across listings, rentals, and projects) to perform systematic
cross-reconciliation across schema boundaries, distributions, and invariants.

### 1. Protocol and contract discrepancies

A systematic sweep of all documented endpoints revealed several immediate contract
violations:

- **Authentication header.** Requests using `?api_key=...` return a 401 response
  stating: *"send your key in the `X-API-Key` request header, not as a query
  parameter."*

- **Token expiration and refresh flow.** The documentation claims tokens last 24 hours
  (86,400 seconds) with no refresh mechanism. In reality, `expires_in` is 900 seconds
  (15 minutes). The login payload secretly returns a `refresh_token` and
  `refresh_url`. The frontend implements an automated refresh cycle (triggering at 14
  minutes) and token retry logic to satisfy the requirement that sessions stay active
  past 30 minutes.

- **Systematic pagination undercount.** Every collection endpoint understates `total`
  by approximately 5.9%:

  | Collection | Reported total | Actual count |
  |---|---|---|
  | Listings | 4,802 | 5,100 |
  | Rentals | 1,977 | 2,100 |
  | Projects | 555 | 590 |

  Relying on the documented formula (`total / limit`) silently drops records. The
  backend uses `offset` rather than `page`, and `has_more` is the only reliable
  termination flag.

- **Documented-but-missing vs. undocumented-but-working endpoints.**

  - *404 errors:* `/v1/analytics/summary`, `/v1/favourites`, `/v1/listing/{id}`, and
    `/v1/listings/{id}/similar` do not exist.
  - *Undocumented, working:* `/v1/saved` (replaces favourites), `/v1/me` (session
    identity), `/v1/localities` (returns true listing counts), `/auth/refresh`, and
    `/v1/health`.

### 2. Deep data anomalies (the four core discrepancies)

Beyond the surface-level contract mismatches, four major data anomalies were
identified within the dataset itself.

#### A. Unit shift by source and date (`carpet_area`)

Calculating price-per-carpet-area across all 5,100 listings revealed a bimodal
distribution. Filtering by portal isolated the outliers to `magichomes`.
Cross-tabulating `posted_at` against area identified an unannounced unit switch on
2026-06-01:

- Listings before 2026-06-01: 541 records in square feet (imperial).
- Listings on or after 2026-06-01: 455 records in square metres (metric).

**Validation via sort behavior:** calling `GET /v1/listings?sort_by=carpet_area`
returns apparently non-monotonic values (e.g., 31, 340, 32, 342, 32...). Assuming the
database sorts on the stored, unrounded square-foot values and converts to square
metres only on serialization, the reconstructed pre-conversion sequence is
334, 340, 341, 342, 343... — perfectly ordered.

Normalizing these 455 records (`sq_metres × 10.7639`) corrects Question 6: the raw,
uncorrected computation yields ₹63,966.39/sq ft, whereas the true normalized mean is
₹32,586.84/sq ft.

#### B. Enquiry-farm fraud detection

Filtering on low price alone fails, because 1,549 legitimate listings sit below the
highest fake price — introducing false positives. Grouping by `posted_by_contact`
revealed an engineered fraud cluster: exactly 5 phone numbers, exactly 38 listings per
number (190 listings total), 100% `is_verified: true`, spread across 3–7 distinct
agent names and all 10 localities, with a median price of ₹14,800–18,000/sq ft
(roughly half the market median).

| Metric | Fraud cluster | Next-busiest agent |
|---|---|---|
| Listings per number | 38, 38, 38, 38, 38 | 33 |
| `is_verified` rate | 190 / 190 (100%) | 20 / 33 (60.6%) |
| Distinct agent names per number | 3–7 | 5 |
| Localities covered | 10 / 10 | 10 / 10 |
| Median ₹/sq ft | 14,800–18,000 | 28,641 |

This reveals a counterintuitive finding: `is_verified` positively correlates with
fraud in this dataset. The client UI actively flags listings from these numbers
rather than displaying a false trust badge.

#### C. Structural duplication

272 property groups share exact geographic coordinates, but manual inspection shows
different floor numbers and area variance — representing separate flats in the same
building, not duplicates.

The real duplicates are cross-portal re-posts, whose geographic distance clusters
tightly between 0.0001 and 0.0013 degrees. Across this cluster, pairs match exactly on
all 11 structural fields (bathroom, balcony, total_floors, facing, furnishing,
property_type, covered_parking, floor, bedroom, locality, apartment_name) with carpet
areas within 1%, while portal source, price, and contact numbers differ. Identifying
these 638 cross-posts leaves 4,462 unique physical properties.

#### D. Seeded physical invariants

Auditing physical property constraints isolated exactly 77 corrupt listing records,
distributed symmetrically across 7 disjoint classes of exactly 11 records each:

| Impossibility class | Record count |
|---|---|
| Negative price (down to −₹6.46 crore) | 11 |
| Price under ₹1 lakh (₹17,470–44,440 — monthly rents mislabeled as sales) | 11 |
| Carpet area strictly greater than super built-up area | 11 |
| Unit floor strictly greater than total building floors | 11 |
| Post-dated timestamps beyond the reference moment (up to 2027-07-02) | 11 |
| Transposed latitude and longitude (plotting into the Barents Sea) | 11 |
| Non-plot dwellings with 0 bedrooms and 0 bathrooms | 11 |

Note: land plots legitimately report 0 bedrooms, 0 bathrooms, and 0 floors; these 202
records were explicitly excluded from the corruption filter.

### 3. Client-side data corrections

To ensure UI accuracy regardless of API anomalies, all raw payloads pass through
`app/src/api/corrections.ts`:

- The client paginates using `has_more` rather than relying on the server-side
  `total`.
- Metric carpet areas from `magichomes` are dynamically normalized to square feet.
- Impossible records, duplicate cross-posts, and enquiry-farm listings are explicitly
  badged in the UI.
- Multi-attribute filtering (BHK, price range, locality) is re-executed client-side
  to bypass backend query inconsistencies.

### Negative results (verified baseline behaviors)

Verifying baseline functionality that was suspected of being broken prevented
over-filtering and false conclusions:

- **Seller descriptions:** text analysis across all 5,100 descriptions confirmed 100%
  fidelity with the structured attributes (bedroom, property_type, furnishing,
  locality, and facing).
- **Rental pricing:** rental deposit and monthly price fields were clean integers in
  standard rupee denominations. Deposits were clean integer multiples of rent
  (2x–10x). Question 5 is a direct sum (₹8,000,100).
- **Listing identifiers:** every `listing_id` across all 5,100 records is genuinely
  unique.
- **Undercount consistency:** the discrepancy in `total` is a systematic reporting
  undercount (~0.941 ratio across endpoints), rather than an intentional
  distinct-property metric.
- **Plot attributes:** confirmed that `bedroom = 0` and `bathroom = 0` only occur
  legitimately on plot listings (202 records), avoiding 202 false positives in the
  corruption count.
- **Single-record parity:** `GET /v1/listings/{id}` returns payloads byte-identical to
  the collection objects.
- **Query parameter validation:** on `/v1/listings`, parameters such as `locality`,
  `bhk`, `property_type`, `min_price`, `max_price`, and `furnishing` filter properly.
  Only `page` and `order` are ignored.
- **Deterministic responses:** identical offset-based queries return consistent pages
  with zero dropped or duplicate rows.

### Timestamp/timezone handling (Question 8)

The reference moment is fixed at `2026-09-10T00:00:00+05:30` (IST). The documentation
claims timestamps are UTC with a trailing `Z`, but actual `posted_at` values are naive
19-character ISO strings (e.g., `2026-06-21T16:40:00`).

Evaluating the preceding 7-day window `[REFERENCE − 7 days, REFERENCE)` presents two
interpretations:

- Interpreted as local IST: 167 records.
- Interpreted as UTC: 152 records.

I chose **167**, based on:

1. `/health` explicitly reports server time with a `+05:30` offset,
   `"timezone": "Asia/Kolkata"`, and `"reference_date": "2026-09-10T00:00:00+05:30"`.
2. The hour-of-day posting distribution is flat across all 24 hours (192–231
   listings/hour), showing no diurnal curve that would indicate unshifted UTC data.
3. `sort_by=posted_at` orders strictly by calendar date and leaves times unordered,
   suggesting the date component is the primary stored value.

---

## Scope for further exploration

Given an additional two days, I would prioritize:

- **Interactive discrepancy toggles** — add toggles to the Insights screen allowing
  reviewers to enable/disable specific corrections (such as metric-area normalization
  or duplicate removal) to see the live impact on aggregate numbers.
- **Fuzzy duplicate resolution** — expand duplicate matching beyond exact 11-field
  structural matches using string distance on building names and area-tolerance bands,
  to catch cross-posts with typos.
- **Behavioral fraud detection** — train a classifier on listing text, price-rounding
  patterns, and posting schedules to identify distributed fraud rings operating with
  fewer listings per phone number.
- **Hybrid query engine** — move catalog browsing back to server-side offset
  pagination, backed by a lightweight background verification job that alerts the
  user if server-side filter results diverge from local calculations.

---

## Tools used

I used Claude as a pair-programming collaborator to draft the data-scraping scripts,
format the findings schema, and scaffold initial React components. I directed the
investigation, formulated each hypothesis regarding data inconsistencies, validated
all script calculations locally, and verified client behavior against the running
backend.

---

## Repository structure

```
.
├── app/                       # Vite + React + TypeScript frontend
│   ├── src/api/client.ts      # API client with token auto-refresh & offset drainage
│   ├── src/api/corrections.ts # Centralized data normalization & anomaly flagging
│   ├── src/pages/             # Login, Browse, Detail, Saved, Rentals, Projects, Insights
│   └── src/state/             # AuthSession and DataContext providers
├── data/                      # Audited local datasets
│   ├── raw/                   # Extracted JSON dumps (listings, rentals, projects)
│   ├── answers.json           # Output of the 10 assignment questions
│   └── findings.json          # Structured list of 31 documented discrepancies
├── scripts/                   # Python data extraction and auditing tools
│   ├── dump.py                # Exhaustive pagination extractor
│   ├── answers.py             # Metric computation script
│   └── build_findings.py      # Schema generator for discrepancies
├── submission.json            # Official submission schema
└── README.md
```