# Indian Flight Analytics — Development Journey

This project wasn't built all at once — it grew in four phases, each one
solving a real limitation of the phase before it. This document walks
through that progression: what existed, what was missing or broken, and
how each problem was actually solved.

---

## Phase 1 — Static Dashboard

**What was built**

A Streamlit dashboard connected to a live MySQL database (`flights` table,
15,000 records). Users could search flights by source/destination, sort
and filter results, and view 6 charts plus 4 KPI cards summarizing the
dataset (busiest airports, busiest routes, price trends, airline
distribution, COVID impact over time).

**The problem**

The dashboard was entirely **static and pre-built**. Every chart, every
KPI, every filter option was something *I* had decided in advance and
hard-coded as a specific SQL query. If a user had a question that didn't
match one of the existing charts — even something simple like "which
airline has the most flights out of Delhi specifically?" — there was no
way to ask it. The dashboard could only answer the questions it was
literally built to answer. There was no AI, no flexibility, no way to
explore the data beyond the fixed set of views.

**Outcome**

A working, functional dashboard — but a rigid one. This limitation is
what motivated Phase 2.

---

## Phase 2 — Ask AI (Natural Language → SQL)

**The problem being solved**

Give users a way to ask *any* question about the flight data in plain
English, instead of being limited to pre-built charts — without letting
an AI model touch the live database directly and unsafely.

**What was built**

`nl_query_layer.py` — a pipeline that takes a plain-English question,
converts it to real SQL using Google's Gemini API, runs that SQL against
the live database, and returns a grounded, plain-English explanation plus
an auto-generated chart when appropriate.

**Problems encountered, and how they were resolved**

- **Safety risk: an LLM writing live SQL is dangerous.** A model could,
  in principle, generate a `DROP TABLE`, an `UPDATE`, or a query against
  a table it shouldn't touch.
  → Resolved with `is_safe_select()` — every generated query is checked
  before it's allowed to run: it must be a plain `SELECT`, must not
  contain dangerous keywords (`INSERT`, `UPDATE`, `DELETE`, `DROP`,
  `ALTER`, etc.), and must only reference the whitelisted `flights` table.

- **Hallucination risk: the LLM could invent numbers that aren't in the
  data**, especially when writing the plain-English explanation.
  → Resolved by design: `explain_result()` only ever shows Gemini the
  *actual* query results and explicitly instructs it not to invent any
  data not present in what it was shown.

- **Model availability changed mid-build.** The original plan was to use
  `gemini-2.5-flash` / `gemini-2.5-flash-lite`, but these were deprecated
  for new API users.
  → Switched to `gemini-3-flash-preview`, which was available and worked
  for the free tier at the time.

- **API key friction during development** — manually pasting the API key
  into the terminal every session was tedious and error-prone.
  → Resolved with a `.env` file + `python-dotenv`, so the key loads
  automatically.

**Outcome**

A working, tested Ask AI feature — confirmed with real questions like
"which airline has the most flights from Delhi" and "what's the average
price per airline" (which correctly triggered an auto-generated bar chart).

---

## Phase 3 — Anomaly Alerts

**The problem being solved**

The dashboard so far only answered "what happened" (descriptive analytics)
and "what does the user want to know" (Ask AI). Nothing looked at the data
and proactively said "this specific thing looks unusual." The goal was to
add that — flagging flights that are priced, timed, or routed very
differently from other flights on the same route, with an AI-written
explanation of why.

**What was built**

`anomaly_detection.py` — groups flights by route, computes a z-score for
price, duration, and stop-count relative to that route's own normal
range, flags flights that fall outside a threshold, scores severity based
on how many factors are flagged, and sends the most severe anomalies to
Gemini for a plain-English explanation.

**Problems encountered, and how they were resolved**

- **Deciding what "anomaly" honestly means for this dataset.** The flights
  data is a static snapshot, not a real time series — there's no
  "yesterday vs. today" to compare. A true time-series anomaly detector
  (the kind that "watches a metric and alerts") wasn't a fit.
  → Resolved by scoping this honestly as **cross-sectional outlier
  detection**: comparing each flight to its *peers on the same route*,
  not to its own history over time. This is a real, legitimate technique
  (used in fraud detection and pricing anomalies), just a different kind
  of "anomaly" than time-series drift — and it's named accordingly rather
  than oversold.

- **A pandas version bug silently broke the pipeline.** The original
  implementation used `groupby("Route").apply(...)` to compute z-scores
  per route. In newer pandas versions, `.apply()` can silently drop the
  column you grouped on from the result — so the `Route` column
  disappeared partway through the pipeline, and the failure only surfaced
  much later as a `KeyError: 'Route'` inside the Gemini explanation step,
  far from its actual cause.
  → Resolved by replacing `groupby().apply()` with `groupby().agg()` +
  `merge()` — computing route-level statistics once, then joining them
  back onto every row. This is both more reliable (no version-dependent
  behavior) and faster (vectorized instead of row-by-row). A regression
  test (`test_route_column_survives_the_pipeline`) was added later so this
  specific bug can never silently reappear.

- **Gemini's free-tier rate limit was hit mid-batch.** Explaining up to
  12 anomalies meant 12 sequential API calls; free-tier Gemini allows a
  limited number of requests per minute, and firing them back-to-back
  triggered failures partway through a run.
  → Resolved by adding a short delay between calls and retrying once
  (with a longer wait) specifically when the failure looked like a
  rate-limit error.

- **Gemini's daily/quota limit was hit during heavy testing.** Beyond the
  per-minute limit, repeated testing across a single day used up the
  account's daily allowance for the (preview-tier) model, which returned
  a clear "quota exceeded" error that a short retry can't fix.
  → Addressed by lowering `TOP_N` (how many anomalies get explained per
  run) from 12 to 8, reducing how much quota each test run consumes, and
  documenting that this is expected behavior with a preview model's
  tighter daily cap — not a bug.

**Outcome**

A working, tested anomaly detector — confirmed against real data with
correct severity scoring (e.g. a flight that was simultaneously
overpriced, slower, and had more stops than normal for its route was
correctly flagged as "High" severity).

---

## Phase 4 — Metrics Layer + Testing

**The problem being solved**

Even with three working features, there was a subtler risk: **the
dashboard's KPI cards and the Ask AI chatbot could each calculate the
"same" number differently** — different SQL, different rounding, no
shared definition — because each was written independently. This is a
real, common problem in production BI systems (two teams' dashboards
disagreeing on "active users"), and the goal was to prevent it here by
design, not just by convention.

**What was built**

`metrics_layer.py` — a single source of truth defining 9 official business
metrics (total flights, average price, busiest route, non-stop rate, etc.),
each with one exact SQL definition. Both the dashboard's KPI cards and
the Ask AI chatbot were changed to read from these same definitions.

**Problems encountered, and how they were resolved**

- **Deciding how strictly to enforce consistency.** Simply telling Gemini
  "here are our official metrics" as extra prompt context would only be a
  suggestion — nothing would guarantee it actually used them, which
  wouldn't really solve the problem.
  → Resolved by building actual enforcement: `match_question_to_metric()`
  checks whether a user's question matches a known metric *before*
  letting Gemini write any custom SQL. If it matches, the app runs the
  metric's exact, pre-written SQL directly — guaranteeing the chatbot's
  answer is identical to the dashboard's number for that metric, because
  it's the literal same query. Gemini is only used to explain the result
  in plain English, and only falls back to generating its own SQL when no
  known metric matches the question.

- **A deprecation warning surfaced during testing.** Streamlit flagged
  `use_container_width=True` (used in 10 places across `app.py`) as
  deprecated, to be removed after 2025-12-31.
  → Fixed by replacing all 10 occurrences with the new `width='stretch'`
  parameter — a direct, behavior-preserving swap.

- **No automated way to catch regressions.** Up to this point, the only
  way to verify the app worked was manually clicking through it — which
  is exactly how the Phase 3 `groupby()` bug went unnoticed until it
  crashed deep in the pipeline.
  → Resolved by adding `test_project.py` — 25 automated tests covering
  duration/stop-count parsing, severity scoring (including the
  route-column regression test), metric matching, and the SQL safety
  check. All 25 pass, and can be re-run in under a second any time the
  code changes, without touching the real database or the Gemini API.

**Outcome**

A complete, internally-consistent, and automatically-verified project:
four distinct features (search, descriptive analytics, NL querying,
anomaly detection) all sharing one governed set of metric definitions,
with a test suite guarding the core logic against silent regressions.

---

## The throughline across all four phases

Each phase followed the same pattern: **build something useful, notice
its real limitation through actually using it, then solve that specific
limitation** — rather than planning every feature upfront. That's also
why the problems above are worth mentioning in an interview: they weren't
hypothetical edge cases, they were things that actually broke or fell
short while building and testing the real app, and each one has a
specific, defensible fix.