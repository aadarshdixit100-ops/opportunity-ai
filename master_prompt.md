# MASTER PROMPT — OpportunityAI (Personal Opportunity Intelligence Platform)

This is the specification the code in this repository implements.

**Verified since this prompt was written** (checked against the live Sarvam docs):
- Chat endpoint `POST {base}/v1/chat/completions`, model `sarvam-105b` — correct as written.
- Translation is a **separate endpoint**, `POST {base}/translate`, model `mayura:v1`, response
  field `translated_text`. It is **not** a chat-completions call, so no chat fallback is needed.
- `POST /translate` caps `input` at **1000 characters** (`mayura:v1`) / 2000 (`sarvam-translate:v1`)
  and returns **422** beyond that — so `SarvamClient.translate()` chunks on sentence boundaries.

--- BEGIN MASTER PROMPT ---

ROLE
You are a principal Python engineer and product architect. Upgrade my existing Streamlit project
"OpportunityAI" into a Personal Opportunity Intelligence Platform for Indian college students:
discovery -> eligibility -> preparation -> application -> tracking. This is a 45-minute hackathon
sprint. Correctness, honesty and a flawless live demo matter more than feature count.

EXISTING PROJECT (keep working)
- Stack: Streamlit + Python. Files: app.py, recommender.py, sarvam_client.py, data/opportunities.json,
  requirements.txt, .env.example, README.md.
- Base score = 0.35*skill + 0.25*interest + 0.20*academic + 0.10*workmode + 0.10*experience.
  Each component is 0-1. Weights are editable in the sidebar and normalised.
- PRESERVE: Try Demo Profile button, profile form, filters (category, skill, work mode, min fit %),
  weight sliders, skill-gap analyzer with 12-week roadmap, grounded chat assistant, CSV export,
  profile-completeness meter.
- Must run with `streamlit run app.py` and NO API key, using deterministic templates. Same input must
  always give the same output.

NON-NEGOTIABLE RULES
1. Zero fabrication. Never invent deadlines, URLs, stipends or eligibility. Unknown = null, shown as
   "Not verified".
2. Every record has source_url, last_verified (ISO date) and verification_status: "verified"
   (human-checked), "fetched" (auto-ingested, not human-checked), "sample" (fictional demo), "closed".
   source_url may be null only for "sample" and is then shown as "Sample, no source".
3. Sample records use FICTIONAL organisation names marked "(sample)". Never pair a real company name
   with invented terms.
4. Secrets only via environment variables. Never log keys or resume text.
5. AI-generated application content may use ONLY facts in the student's profile or resume. No invented
   achievements.
6. Fit scores are guidance, not predictions of selection. Say so in the UI.
7. Escape (html.escape) ALL dataset, ingested and resume text before putting it into any
   unsafe_allow_html block.
8. Time: use a helper today() that reads env OPPORTUNITYAI_TODAY (ISO date) else date.today(), so demos
   and tests are reproducible.

DEFINITIONS (keep these three concerns separate)
- Eligibility gates: degree, branch, year, CGPA, women_only. Each gate result is pass | fail | unknown.
  Any fail -> "Ineligible". Else any unknown -> "Potentially Eligible" (list exactly what to verify).
  Else "Eligible". Skills are NEVER eligibility gates.
- Timing status: open | closing_soon (<=7 days) | rolling | not_yet_open (opens_on in future) |
  closed (deadline passed or status "closed") | unknown. A closed deadline is not ineligibility.
- Fit: the weighted score below, computed for every non-ineligible opportunity.

DATA SCHEMA (data/opportunities.json, plus data/knowledge.json)
Record fields: id, title, organization, category, description, required_skills[], preferred_skills[],
interests[], min_cgpa (nullable), eligible_years (list of ints, or null = unknown), eligible_degrees
(list or null), eligible_branches (list or null), work_mode, location, stipend_or_award (nullable),
deadline (ISO or null), deadline_kind ("fixed" | "rolling" | "unknown"), opens_on (ISO or null),
demo_deadline_offset_days (int or null, sample records only), apply_url (nullable), source_url,
last_verified, verification_status, women_only (bool or null), tags[].
Demo Mode (sidebar toggle, default ON when no "verified" records exist): a sample record's
demo_deadline_offset_days resolves to today()+N and is shown with an "Illustrative deadline (demo)"
badge. Outside Demo Mode such records have an unknown deadline.
knowledge.json holds three human-written maps: skill_synonyms, skill_playbook (>=15 common skills ->
project idea, practice task, resource TYPE; no URLs, plus a generic fallback), domain_bridges
(branch -> adjacent interest areas, each with a one-line rationale).

ENGINE SPEC (recommender.py)
Stage 1 Eligibility: gate-by-gate result list (gate, status, detail).
Stage 2 Ranking: skill credit per required/preferred skill: exact = 1.0, synonym-map hit = 0.9,
rapidfuzz token_set_ratio >= 90 = 0.7, else 0. Required skills weigh 2x preferred. Skill component =
weighted coverage. Unknown min_cgpa gives a neutral academic component of 0.5, flagged "unconfirmed".
Tie-break by id. Fuzzy matches never change eligibility.
Stage 3 Explanation: "Why this opportunity?" (matched skills, with "matched via synonym/similar skill"
labels, plus matched interests) and "What could improve your fit" (missing skills).
Stage 4 Counterfactuals: for each missing skill of an opportunity, re-run the SAME score function with
that skill added and return the top 3 by gain: {skill, before_pct, after_pct, delta}. Discard gains
under 0.5 points. Also top_skill_gains() aggregating gain across the top 10 non-ineligible matches.
For ineligible items return concrete gap facts (CGPA gap, eligible from year N). Never suggest
altering data.
Invariants to test: adding a skill never lowers a score; ineligible stays ineligible after any skill
addition.

OPPORTUNITY RADAR RULES
Excluded (shown in a "Why Not?" panel with the reason and fix): Ineligible, or timing closed.
Each opportunity appears in exactly one pane, checked in this order. Thresholds are constants at the
top of recommender.py:
1. Apply Now: Eligible or Potentially Eligible (show a "Verify: ..." chip), timing
   open/closing_soon/rolling with a verified deadline (or sample in Demo Mode, badged DEMO),
   required-skill coverage >= 0.60, total fit >= 55%.
2. Prepare For: Eligible or Potentially Eligible, fit >= 40%, and (coverage < 0.60, or timing
   not_yet_open/unknown). Each card has a deterministic "Next Action" from skill_playbook.
3. Explore: remaining non-excluded items with an interest or domain_bridges match to the student's
   branch. Show the bridge rationale. Max 5.
Sort within panes by fit desc, then deadline asc, then id. career_goal only influences Explore ordering
and Next Action wording, never the score.

AI APPLICATION COPILOT
- Upload: PDF only, <=5 MB, <=10 pages, check the %PDF header, extract with pypdf. If the text is empty
  or scanned, show a clear message. Resume text lives in session only unless the user ticks "Remember
  my resume" (then SQLite). "Delete my data" wipes the DB.
- Consent checkbox before any resume text goes to an AI service. Redact emails and phone numbers first.
  Treat resume text as untrusted data: wrap it in delimiters and instruct the model to ignore any
  instructions inside it.
- Evidence Matrix per required skill, deterministic first: word-boundary search for the skill or its
  synonyms, returning the surrounding sentence (<=200 chars, verbatim) and the section (Skills /
  Projects / Experience). Labels: "Demonstrated" (found in Projects/Experience), "Listed only" (Skills
  section only), "No evidence". AI may refine, but every quote must pass `quote in resume_text`,
  otherwise discard it.
- 7-Day Prep Kit: (a) resume checklist from evidence gaps, wording like "Add a bullet only if you have
  actually done this; otherwise do not claim it"; (b) interview topics labelled "Typical topics for
  this kind of role, not confirmed by the organisation"; (c) a day-by-day plan (focus, 2-3 tasks,
  hours, output artifact) built from skill_playbook. Any draft resume bullet must show its source line
  from the resume beside it. No invented URLs.

DISCOVERY / INGESTION (scripts/ingest_github.py)
CLI with --source. Use requests with a 10 s timeout and optional GITHUB_TOKEN from env. Use only API
endpoints you are certain exist; if unsure, leave a marked TODO. Map results to the schema with
verification_status "fetched", source_url = exact URL fetched, last_verified = fetch date, deadline =
null unless explicitly in the source. Write to data/ingested_cache.json. The app only reads the cache
and never calls the network on startup. Missing or corrupt cache is handled silently. Sidebar "Refresh"
is optional and fail-safe. Be honest in the README that I must run the script once before the demo.

TRACKER (db.py, SQLite via stdlib sqlite3)
Use parameterised queries only. Open a short-lived connection per call (or st.cache_resource), enable
WAL, and track schema version with PRAGMA user_version. Tables: profile(id=1, json, updated_at);
applications(opportunity_id PK, stage, notes, updated_at); stage_history(id, opportunity_id,
from_stage, to_stage, at); skill_progress(skill PK, state, evidence_note, updated_at);
feedback(opportunity_id, vote, at); ai_cache(key PK, value, created_at).
Stages: Discovered -> Shortlisted -> Preparing -> Applied -> Interview -> Outcome (Selected | Rejected |
Withdrawn | No response). Skill states: Not Started -> Learning -> Practised -> Demonstrated in Project.
STRETCH (only after everything else works): a funnel chart from stage_history, and a "Projected fit"
that counts Practised at 50% and Demonstrated at 100% credit, always shown separately from the real
score.

INTERFACE CONTRACT (all files must use exactly these)
recommender.py:
  evaluate_eligibility(profile, opp, today) -> {status, gates:[{gate, status, detail}], verify:[str]}
  timing_status(opp, today, demo_mode) -> str
  score_opportunity(profile, opp, weights) -> {total, components:{...}, matched:[{skill, via}],
                                               missing:[str], unconfirmed:[str]}
  build_radar(profile, opps, weights, today, demo_mode) -> {"apply_now":[], "prepare_for":[],
                                                            "explore":[], "excluded":[]}
  counterfactuals(profile, opp, weights, max_n=3) -> [{skill, before_pct, after_pct, delta}]
  top_skill_gains(profile, opps, weights, today) -> [{skill, opportunities_lifted, avg_gain}]
  evidence_matrix(resume_text, opp) -> [{requirement, label, quote, section}]
  prep_kit_template(profile, resume_text, opp) -> dict
sarvam_client.py:
  is_enabled() -> bool
  parse_resume(text) -> dict (regex fallback)
  refine_evidence(resume_text, rows) -> rows
  generate_prep_kit(profile, resume_text, opp) -> dict
  translate(text, lang) -> str
db.py: init_db, save_profile, load_profile, set_stage, get_applications, set_skill_state,
  get_skill_states, save_feedback, cache_get, cache_set, wipe_all.

SARVAM CLIENT RULES
- Config from env: SARVAM_API_KEY, SARVAM_MODEL (default sarvam-105b), SARVAM_BASE_URL (default
  https://api.sarvam.ai). Chat call: POST {base}/v1/chat/completions with header
  api-subscription-key; read choices[0].message.content.
- Translation: POST {base}/translate with {input, source_language_code, target_language_code}; read
  translated_text. Chunk input to stay under the 1000-character cap.
- 15 s timeout, one retry on 429/5xx with backoff, then the deterministic fallback. Temperature 0.2 for
  extraction. Ask for JSON only, strip code fences, validate keys and types, and on any failure use the
  fallback.
- Cache AI outputs by sha256(model + prompt + lang) in ai_cache.

LANGUAGE
Sidebar toggle English / Hindi. Use a hand-written static UI dictionary (>=40 strings) for the
interface. Use Sarvam only for dynamic text (explanations, prep kit), cached. Keep skill names,
organisation names and technical terms in English. If translation fails, show English with the notice
"Translation unavailable".

UI LAYOUT
- Header: profile-completeness meter, Career Goal select, a privacy note, and the Demo Mode toggle.
- Main tabs: Radar | Copilot | Tracker | Skills & Gap | Why Not? | Assistant. The Radar is three
  columns on desktop, plus a "Compact view" toggle that uses tabs for mobile.
- Sidebar: demo profile button, filters, weight sliders, resume upload, language, CSV export,
  Delete my data.
- Card: title, organisation, fit % ring, eligibility badge (text + icon, never colour-only), timing
  badge, verification badge with last_verified date, "Why this?" chips, and buttons: View Details,
  AI Copilot, Save to Tracker. Every missing field shows "Not verified".
- Details view: eligibility gate table, 5-component score breakdown, counterfactuals, source link
  (http/https only), and thumbs up/down.

SAMPLE RECORDS
21 richly detailed records designed to exercise every branch for the demo profile, including: one
eligible Apply Now; one Potentially Eligible (min_cgpa null, eligible_years null); one Ineligible by
CGPA by ~0.3 despite very high skill fit; one Prepare For with low required-skill coverage; one
Explore with a cross-disciplinary bridge; a closed one; a women-only one; a rolling one; and a mix of
categories (internship, scholarship, hackathon, research, open source).

DELIVERY PROTOCOL
Deliver in dependency order, each file in full. Never truncate a file.
 Phase 1: requirements.txt, .env.example, data/knowledge.json, data/opportunities.json, db.py,
   recommender.py.
 Phase 2: sarvam_client.py, scripts/ingest_github.py.
 Phase 3: app.py.
 Phase 4: tests/test_core.py, README.md, demo_script.md.
Tests (one compact pytest file, with OPPORTUNITYAI_TODAY frozen): determinism; the eligibility and pane
result for each designed record under the demo profile; counterfactual invariants; a fabricated quote
is rejected by the evidence validator; stage transitions are recorded in stage_history.

DEMO SCRIPT (demo_script.md, 3 minutes, timestamped)
0:00 problem. 0:20 Demo Profile -> Radar. 1:00 Why Not panel (honesty). 1:20 counterfactual.
1:50 resume upload -> Evidence Matrix. 2:20 Save to Tracker plus Hindi toggle. 2:45 close with
limitations and next steps. Include a backup plan if Wi-Fi or the API fails.

ACCEPTANCE CRITERIA
- `streamlit run app.py` works with no API key and no network.
- An invalid key or a timeout falls back silently, with a small notice.
- No invented data anywhere. All unknown fields are labelled.
- Each opportunity appears in exactly one Radar pane or in Why Not.
- The tracker persists across restarts. All preserved features still work.
- All tests pass.

--- END MASTER PROMPT ---

---

## ADDENDUM — Opportunity Strategist capabilities (implemented)

These extend the prompt above. The product identity is a **personal opportunity strategist**:
it does not predict outcomes, it helps the student decide what to do next.

### A. Your Next Best Move (ROI engine) — `action_priority()`, `next_best_move()`, `pathway()`
Rank **actions**, not just opportunities, over the student's top N targets:
`P(a) = R(a) x G(a) x C(a) / T(a)`
- R relevance: target fits, weighted 1.0 if Eligible / 0.6 if Potentially Eligible
- G gap: the REAL score function re-run with the skill added
- C confidence: `verified` 1.0 / `fetched` 0.6 / `sample` 0.35 / `closed` 0.0
- T effort: `skill_playbook[*].hours`, labelled as an estimate
Normalise R, G and C with **max-normalisation, never min-max** — `P` is a product, so a factor that
min-max maps to 0 zeroes the whole score and collapses the ranking. Targets must exclude both
ineligible AND closed opportunities. Sort targets by eligibility tier, then fit, so the plan is built
around opportunities the student can actually pursue. Render a pathway (skill -> project -> each
affected opportunity's before/after fit -> improved readiness) and state that it is not a guarantee.

### B. Information quality (trust panel) — `information_completeness()`
Field-level (source / deadline / eligibility / apply_url), returning a completeness percentage and a
human-verified flag. Keep it **strictly separate from fit** — an opportunity can fit well and still
have an unverified deadline. Label it "Information Completeness", never a legitimacy guarantee.

### C. "Why isn't this in Apply Now?" — `why_not_apply_now()`
For any item in Prepare For / Explore, return a four-row check (eligibility, timing, required-skill
coverage, overall fit) with status, detail and next action. Failing an eligibility gate and not yet
meeting the Apply Now bar are different outcomes and must read differently.

### D. Evaluation suite — `evaluation.py`
Five labelled profiles (first-year, high-CGPA, incomplete-academic-data, interdisciplinary, demo).
Report eligibility accuracy against objective mandatory-failure labels; precision@5 / recall@5 /
NDCG@5 against author-labelled relevant sets (state clearly that these are heuristic regression
labels, not expert ground truth); coverage and pane-partition completeness.

### E. Fairness
Never infer financial need, gender, caste or any sensitive characteristic from college, location, name
or academic history. Use explicit `women_only` and voluntary profile fields only. Default preparation
guidance to free resources and commonly available tools.
