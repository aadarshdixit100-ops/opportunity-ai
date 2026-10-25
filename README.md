# OpportunityAI — Personal Opportunity Intelligence Platform

A working Streamlit MVP for Indian college students:
**discovery → eligibility → preparation → application → tracking.**

Runs fully **offline with no API key**. Sarvam AI is optional and only ever *explains*, never scores.

The product's identity is a **personal opportunity strategist**, not a search box: it does not try to
predict your future, it helps you decide what to do next.

---

## 0. Two ways to run this

| | Browser website | Python app |
|---|---|---|
| **Entry point** | `index.html` — double-click it | `streamlit run app.py` |
| **Needs** | nothing (no Python, no server, no install) | Python 3.10+ and `pip install -r requirements.txt` |
| **Hosting** | any static host (GitHub Pages, Netlify, Cloudflare Pages) | needs a Python host |
| **Engine** | the same engine, ported to JavaScript | Python |
| **AI features** | off — deterministic engine only | Sarvam AI explanations, `/translate`, PDF resume parsing |
| **Storage** | browser `localStorage` | SQLite |

The website is a single self-contained file: no external requests, no dependencies, works offline.
Its engine is a faithful port of `recommender.py` — a Node cross-check (`web/crosscheck.js`)
compares every fit score, eligibility verdict, timing status, radar pane, ranked action and
evidence label against the Python output, and currently reports **max delta 0.0000 across all 21
records with zero mismatches**. Rebuild it after editing the sources with `python3 web/build.py`.

See `WEBSITE.md` for local use and deploy steps.

---

## 1. The three concerns are kept separate

Mixing them is what makes such apps dishonest.

| Concern | What it answers | Values | Effect |
|---|---|---|---|
| **Eligibility** | Do you *qualify*? | `pass` / `fail` / `unknown` per gate (degree, branch, year, CGPA, women-only) | Any `fail` → **Ineligible**. Else any `unknown` → **Potentially Eligible** (with exactly what to verify). |
| **Timing** | Is it *open*? | `open` / `closing_soon` / `rolling` / `not_yet_open` / `closed` / `unknown` | Excluded from the Radar if `closed`. |
| **Fit** | How *well* does it match? | 0–100% weighted score | Computed for every non-ineligible opportunity. |

**Skills are never eligibility gates** — a missing skill lowers fit and creates a learning action.
**A closed deadline is not ineligibility.** **Unknown is never a failure.**

### Fit formula (configurable in the sidebar)

```
fit = 0.35·skill + 0.25·interest + 0.20·academic + 0.10·workmode + 0.10·experience
```

Skill credit: exact = 1.0, synonym-map hit = 0.9, fuzzy (rapidfuzz `token_set_ratio` ≥ 92 on
normalised text) = 0.7, else 0. **Required skills weigh 2× preferred.** Fuzzy matches never change
eligibility.

---

## 2. The Opportunity Radar

Every opportunity lands in **exactly one** pane or in *Why Not?*. Thresholds live in
`RADAR_THRESHOLDS` in `recommender.py`, not in the UI.

1. **Apply Now** — Eligible/Potentially Eligible, live window with a deadline signal, required-skill
   coverage ≥ 0.60, fit ≥ 55%.
2. **Prepare For** — Eligible/Potentially Eligible, fit ≥ 40%, and (coverage < 0.60 **or** timing
   not_yet_open/unknown).
3. **Explore** — the explicit **catch-all**; shows the `domain_bridges` rationale when your branch has
   an adjacent area.
4. **Excluded → Why Not?** — the reason *and* what would help.

A test asserts the panes partition the dataset exactly.

**"Why isn't this in Apply Now?"** — for anything in Prepare For / Explore, a four-row table shows the
eligibility status, timing, required-skill coverage and overall fit against their thresholds. Failing
an eligibility gate and *not yet meeting the Apply Now bar* are different outcomes, and the UI says so.

---

## 3. Your Next Best Move (ROI engine) 🚀

The centrepiece. Students have limited time, so the app ranks **actions**, not just opportunities:

```
P(a) = R(a) × G(a) × C(a) / T(a)
```

| Term | Meaning | How it is derived |
|---|---|---|
| **R** relevance | how many of your top targets ask for this skill | target fits, weighted 1.0 if Eligible / 0.6 if Potentially Eligible |
| **G** gap | average fit gain from adding the skill | the **real** score function re-run with the skill added |
| **C** confidence | source-verification weight of the records driving it | `verified` 1.0 · `fetched` 0.6 · `sample` 0.35 · `closed` 0.0 |
| **T** effort | labelled hours estimate | `skill_playbook[*].hours`, shown as an *estimate* |

R, G and C are **max-normalised** (not min-max: `P` is a product, so a factor mapped to exactly 0
would zero the whole score and collapse the ranking — this was a real bug, now regression-tested).
Targets are actionable only: **closed and ineligible opportunities are never targets.**

For the demo profile the engine returns:

> **Learn Machine Learning** — asked for by 3 of your top 5 target opportunities; lifts your fit by an
> average of +8.0 points on 3 of them; estimated effort 50 hours.

A **Pathway** panel renders the chain: *You now → Learn it → Show it (a project) → each affected
opportunity with its before/after fit → improved readiness*. Nothing here claims an internship is
guaranteed.

---

## 4. Information quality (trust panel) 🛡️

Deliberately **separate from fit**. An opportunity can fit you well *and* have an unverified deadline —
three different facts, shown as three different things.

Every card carries an **Information quality** chip; the detail view breaks it down field by field
(source / deadline / eligibility / apply link → stated or not stated), plus whether a human has checked
the record. `information_completeness()` returns a completeness percentage that is labelled
**Information Completeness** — *not* a guarantee of legitimacy.

---

## 5. Evaluation suite 📊

`evaluation.py` measures the engine rather than asserting it is good, over five labelled profiles
(first-year, high-CGPA, incomplete-academic-data, interdisciplinary, and the demo profile):

- **Eligibility accuracy** against objectively labelled mandatory-failure sets.
- **Precision@5 / Recall@5 / NDCG@5** against author-labelled relevant sets (heuristic labels for
  regression, *not* expert ground truth — stated in the module docstring).
- **Coverage** and **partition completeness** (every opportunity in exactly one pane).

Current results:

```
profile                                                elig    P@5    R@5   NDCG  cover  part
Demo — 2nd year Chemical Engineering                   1.00   0.80   0.57   0.87   1.00  True
First year, CS, low experience                         1.00   0.60   1.00   1.00   1.00  True
Third year, high CGPA, strong skills                   1.00   0.80   0.57   0.87   1.00  True
Strong skills but no CGPA given                        1.00   1.00   1.00   1.00   1.00  True
Interdisciplinary — Mechanical, robotics               1.00   0.60   0.75   0.79   1.00  True

mean eligibility accuracy: 1.000   mean precision@5: 0.760
```

---

## 6. Project structure

```
opportunity-ai/
├── app.py                     # Radar | Next Move | Copilot | Tracker | Skills & Gap | Why Not? | Assistant
├── recommender.py             # gates, timing, fit, radar, counterfactuals, ROI engine, evidence, prep kit
├── evaluation.py              # labelled evaluation harness (metrics + report)
├── sarvam_client.py           # Sarvam chat + /translate (chunked), resume parsing, safe fallbacks
├── db.py                      # SQLite tracker (profile, applications, stage_history, skills, feedback, cache)
├── data/
│   ├── opportunities.json     # 21 illustrative SAMPLE records (fictional organisations)
│   └── knowledge.json         # skill_synonyms, skill_playbook (+hours), domain_bridges
├── scripts/ingest_github.py   # OPTIONAL discovery → data/ingested_cache.json (app never calls the network)
├── web/                       # browser website sources (engine.js, app.js, styles.css, template.html, build.py)
├── index.html                 # the built website — self-contained, no dependencies
├── .streamlit/config.toml     # pins theme.base=light (fixes the contrast defect)
├── tests/
│   ├── test_core.py           # engine, tracker, evidence
│   └── test_ui_theme.py       # contrast/theme regression guards
├── requirements.txt · .env.example · README.md · demo_script.md · master_prompt.md
```

---

## 6b. UI theme and the contrast fix

**The defect.** The dashboard rendered unreadable text on some machines: tab labels came out as
empty boxes, sidebar labels and captions vanished, and metric values were barely visible. It only
affected users whose OS/browser prefers dark.

**Why it happened** — three causes, all now fixed:

1. **No `.streamlit/config.toml`.** `theme.base` defaults to `auto`, which follows the viewer's
   colour preference. On a dark-preferring machine Streamlit applied its dark theme — near-white
   text (`#FAFAFA`) — while `app.py` painted its own light backgrounds. Light text on light
   surfaces. **Fix:** `base = "light"` plus an explicit palette, so the framework and the stylesheet
   agree instead of fighting.
2. **A dead selector.** `html, body, [class*="css"]{color:…}` — `[class*="css"]` was a pre-emotion
   Streamlit hack and matches nothing in Streamlit 1.66 (classes are `st-emotion-cache-*`), so the
   intended colour never applied. **Fix:** the selector is gone; colour is now set on the containers
   Streamlit actually paints (`.stApp`, `[data-testid="stAppViewContainer"]`, the sidebar).
3. **Repainted backgrounds with no explicit colour.** The app forced a white sidebar and white cards
   but never set the text colour inside them, so they inherited the theme's. **Fix:** every surface
   the app repaints now sets its own colour.

Also hardened: tabs are coloured with both `.stTabs [data-baseweb="tab"]` and a defensive
`[role="tab"]` rule (Streamlit has shipped more than one tab markup); primary buttons are covered
under both `kind="primary"` and `data-testid="stBaseButton-primary"`; muted slate was darkened to
`#5b6b82` to clear WCAG AA on white; hover, focus-visible, selected and disabled states are styled;
and no blanket white-text rule exists anywhere.

**How it was verified.** `tests/test_ui_theme.py` pins each cause as a regression guard — including
a computed WCAG contrast check on the muted colour — so the defect cannot silently return. Visually,
the shipped stylesheet was rendered under harnesses mimicking Streamlit's light *and* dark theme
text colours: before the fix the dark harness showed blank tab labels and invisible sidebar labels;
after it, every label is legible in both.

---

## 7. Setup and run

```bash
cd opportunity-ai
python3 -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

No API key needed. Tests: `python -m pytest tests -q`. Evaluation report: `python3 evaluation.py`.

---

## 8. Enabling Sarvam AI (optional)

1. Create a key on the Sarvam AI dashboard (shown only once).
2. `cp .env.example .env`, set `SARVAM_API_KEY=...`, restart.

Verified against the current Sarvam docs:

| Purpose | Endpoint | Model | Notes |
|---|---|---|---|
| Chat | `POST {base}/v1/chat/completions` | `sarvam-105b` | header `api-subscription-key`; read `choices[0].message.content` |
| Translate | `POST {base}/translate` | `mayura:v1` | body `{input, source_language_code, target_language_code}`; read `translated_text` |

- **`sarvam-m` is deprecated** and rejected — this project uses `sarvam-105b`.
- **`/translate` caps `input` at 1000 characters** and returns **422** beyond that, so
  `SarvamClient.translate()` chunks on sentence boundaries.
- Auth failures return **403**, not 401 — handled as a fallback, never a crash.

Secrets come from environment variables only. Keys are never hardcoded or logged.

---

## 9. Reliability, privacy and fairness

| Situation | Behaviour |
|---|---|
| No API key | Everything runs: engine, templates, built-in assistant. |
| Timeout / 403 / 429 / 422 / bad JSON | One retry on 429/5xx, then a deterministic fallback. Never crashes. |
| Invalid CGPA (`abc`, `11`, `-1`) | Inline error; the profile is not overwritten. |
| No resume / scanned PDF | Clear message; every evidence row reads "No evidence". |
| Missing/corrupt ingestion cache | Ignored silently. |

**Resume handling.** PDF only, ≤ 5 MB, ≤ 10 pages, `%PDF` header checked, `pypdf` extraction. Resume
text is treated as **untrusted**: emails and phone numbers are redacted before anything is sent to an
AI service, the text is wrapped in delimiters, and the model is told to ignore any instructions inside
it. Consent is required first. The resume stays in the session unless you tick *Remember my resume*.
**Delete my data** wipes the SQLite contents.

**Evidence quotes are gated in code.** Every quote must pass `validate_quote()`; an AI-refined quote not
found in the resume is discarded, so a fabricated bullet cannot reach the table.

**Fairness.** The app never infers financial need, gender, caste or any sensitive characteristic from a
college, location, name or academic history. Restricted programmes use an explicit `women_only` field,
and when gender is unstated the gate returns `unknown` → *Potentially Eligible*, never a silent pass.
Low-cost preparation is the default: the playbook names resource **types** and projects runnable with
common tools, never paid courses.

---

## 10. Honesty notes

- All 21 seed records are **illustrative sample data with fictional organisations** marked `(sample)`.
- **Deadlines and application links are not asserted.** Unknown fields are `null`, shown as
  "Not verified". Sample records use `demo_deadline_offset_days`, materialised **only in Demo Mode**
  and badged **DEMO deadline**.
- `verification_status` ∈ `verified` (human-checked) / `fetched` (auto-ingested, not human-checked) /
  `sample` (fictional demo) / `closed`.
- The assistant does **not** claim to have searched the internet.
- Fit is guidance, **not a prediction of selection**; the Next Move tab repeats this.
- A rejection does not prove a recommendation was wrong, and an offer does not prove the formula is
  accurate. The app does not claim to learn a reliable selection predictor from personal outcomes.

---

## 11. Demo stability

`recommender.today()` reads `OPPORTUNITYAI_TODAY` (ISO date) if set, else the real date. Set it in
`.env` to freeze the demo: `OPPORTUNITYAI_TODAY=2026-10-25`.

---

## 12. Feature status

**Implemented:** three-concern engine; eligibility gate table; timing badges; Radar with three panes +
Why Not; per-component score breakdown; **Your Next Best Move ROI engine with pathway**; counterfactuals
and `top_skill_gains`; **field-level Information quality panel**; **"Why isn't this in Apply Now?"**;
Evidence Matrix; 7-Day Prep Kit; SQLite tracker with stage history and funnel; Skills & Gap with
learning plan, roadmap and skill-state tracking; CSV export; profile-completeness meter; Career Goal;
Demo Mode; English/Hindi UI with Sarvam translation for dynamic text; delete-my-data; **evaluation
suite**; 34 tests.

**Not implemented (deliberately deferred):** the full Opportunity Graph as a separate structure (the
ROI engine's pathway is its first version); *Projected fit* from skill states (states are tracked and
persisted, but no projected score is shown); Proof-of-Skill portfolio with a `Verified` skill state;
per-opportunity thumbs up/down (the `feedback` table exists and is wired, but no UI control);
deadline-aware scheduling; document translation of whole files.

---

## 13. Limitations

- The dataset is small and illustrative — a demo, not a live opportunity feed.
- Fuzzy skill matching is token-based, deliberately conservative, and never affects eligibility.
- Effort estimates in `skill_playbook` are **labelled estimates**, not measured data.
- Evaluation labels for ranking metrics are the author's judgement, for regression purposes.
- `scripts/ingest_github.py` maps GitHub repositories to "Open Source Program" records; a repository is
  not an internship with a deadline, so fetched rows carry a null deadline and the "fetched" status.
  Run it once before a demo if you want those rows — the app itself never calls the network.
