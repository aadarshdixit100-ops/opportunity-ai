"""
recommender.py — OpportunityAI engine.

Deterministic and explainable. Three concerns are kept strictly separate:

  * ELIGIBILITY  — gates (degree, branch, year, CGPA, women-only). Skills are NEVER gates.
                   Result is pass | fail | unknown per gate. Unknown is not a failure.
  * TIMING       — open | closing_soon | rolling | not_yet_open | closed | unknown.
                   A closed deadline is NOT ineligibility.
  * FIT          — the weighted score. Computed for every non-ineligible opportunity.

Scoring components (default weights, configurable):
    skill overlap 0.35 · interest 0.25 · academic 0.20 · work-mode 0.10 · experience 0.10

No AI is used here. Every percentage comes from the formula below.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

try:
    from rapidfuzz import fuzz
except ImportError:  # pragma: no cover
    fuzz = None

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #
DEFAULT_WEIGHTS: Dict[str, float] = {
    "skill": 0.35, "interest": 0.25, "academic": 0.20, "workmode": 0.10, "experience": 0.10,
}

# Radar thresholds — tune here, not in the UI.
RADAR_THRESHOLDS = {
    "apply_min_fit": 55.0,
    "apply_min_coverage": 0.60,
    "prepare_min_fit": 40.0,
    "closing_soon_days": 7,
    "explore_max": 5,
}

FUZZY_THRESHOLD = 92          # token_set_ratio on normalised strings
SYNONYM_CREDIT = 0.9
SIMILAR_CREDIT = 0.7
COUNTERFACTUAL_MIN_DELTA = 0.5  # percentage points

EXPERIENCE_ORDER = {"Beginner": 0, "Intermediate": 1, "Advanced": 2}
QUOTE_MAX = 200

MASTER_SKILLS: List[str] = [
    "Python", "Java", "C++", "JavaScript", "SQL", "R", "HTML/CSS",
    "React", "Node.js", "FastAPI", "Django", "Data Structures",
    "Machine Learning", "Deep Learning", "PyTorch", "TensorFlow",
    "scikit-learn", "Pandas", "NumPy", "NLP", "Computer Vision",
    "Data Visualization", "Process Engineering", "Process Simulation",
    "Aspen Plus", "MATLAB", "Thermodynamics", "Fluid Mechanics",
    "Heat Transfer", "Reaction Engineering", "Git", "Linux", "Docker",
    "Cloud (AWS)", "Excel", "Embedded C", "Verilog", "Communication",
    "Technical Writing",
]

INTEREST_OPTIONS: List[str] = [
    "Artificial Intelligence", "Machine Learning", "Data Science",
    "Web Development", "Software Engineering", "Chemical Engineering",
    "Research", "Sustainability", "Energy", "Robotics", "Open Source",
    "Entrepreneurship", "Cybersecurity", "Biotechnology",
]

CATEGORY_ORDER: List[str] = [
    "Software Engineering Internship", "Data Science / ML Internship",
    "Chemical Engineering Internship", "Research Internship", "Scholarship",
    "Hackathon", "Innovation Competition", "Open Source Program",
]

CATEGORY_BADGE = {
    "Software Engineering Internship": "b-blue",
    "Data Science / ML Internship": "b-violet",
    "Chemical Engineering Internship": "b-green",
    "Research Internship": "b-violet",
    "Scholarship": "b-amber",
    "Hackathon": "b-blue",
    "Innovation Competition": "b-green",
    "Open Source Program": "b-grey",
}

_HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(_HERE, "data")


# --------------------------------------------------------------------------- #
# Time — frozen "today" for reproducible demos and tests
# --------------------------------------------------------------------------- #
def today() -> _dt.date:
    """Read OPPORTUNITYAI_TODAY (ISO date) if set, else the real date."""
    raw = os.environ.get("OPPORTUNITYAI_TODAY", "").strip()
    if raw:
        try:
            return _dt.date.fromisoformat(raw)
        except ValueError:
            pass
    return _dt.date.today()


def _iso(value: Any) -> Optional[str]:
    return value if isinstance(value, str) and value.strip() else None


def _as_date(value: Optional[str]) -> Optional[_dt.date]:
    if not value:
        return None
    try:
        return _dt.date.fromisoformat(value)
    except ValueError:
        return None


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #
def _read_json(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {}


def load_opportunities(path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Seed dataset + optional extra/ingested files. Never touches the network.

    A missing or corrupt extra cache is ignored silently, so the app always works.
    """
    payload = _read_json(path or os.path.join(DATA_DIR, "opportunities.json"))
    records = list(payload.get("opportunities", []))
    for name in ("opportunities_extra.json", "ingested_cache.json"):
        extra = _read_json(os.path.join(DATA_DIR, name))
        records.extend(extra.get("opportunities", []))
    return records


def load_knowledge(path: Optional[str] = None) -> Dict[str, Any]:
    payload = _read_json(path or os.path.join(DATA_DIR, "knowledge.json"))
    return {
        "skill_synonyms": payload.get("skill_synonyms", {}),
        "skill_playbook": payload.get("skill_playbook", {}),
        "domain_bridges": payload.get("domain_bridges", {}),
    }


def dataset_notice(path: Optional[str] = None) -> str:
    payload = _read_json(path or os.path.join(DATA_DIR, "opportunities.json"))
    return payload.get("_meta", {}).get("important_notice", "")


# --------------------------------------------------------------------------- #
# Text / skill normalisation
# --------------------------------------------------------------------------- #
def _norm(value: Any) -> str:
    return str(value).strip().lower() if value is not None else ""


def _norm_skill(value: Any) -> str:
    """Lowercase, strip punctuation (keeping + # . /), collapse whitespace."""
    s = _norm(value)
    s = re.sub(r"[^a-z0-9+#./ ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


_CANON = {_norm_skill(s): s for s in MASTER_SKILLS}


def canonical_skill(value: Any, synonyms: Optional[Dict[str, str]] = None) -> str:
    """Map a raw skill string to its display name."""
    key = _norm_skill(value)
    if key in _CANON:
        return _CANON[key]
    if synonyms:
        mapped = synonyms.get(key) or synonyms.get(_norm(value))
        if mapped:
            mk = _norm_skill(mapped)
            return _CANON.get(mk, mapped)
    return str(value).strip()


def _synonym_canon(synonyms: Dict[str, str]) -> Dict[str, str]:
    out = {}
    for k, v in (synonyms or {}).items():
        out[_norm_skill(k)] = _norm_skill(v)
    return out


def skill_credit(student_skills: List[str], target: str, synonyms: Dict[str, str]) -> Tuple[float, Optional[str]]:
    """Best credit one target skill gets from the student's skill list."""
    t = _norm_skill(target)
    syn = _synonym_canon(synonyms)
    t_canon = syn.get(t, t)
    best, via = 0.0, None
    for raw in student_skills or []:
        s = _norm_skill(raw)
        if not s:
            continue
        if s == t:
            return 1.0, "exact"
        s_canon = syn.get(s, s)
        if s_canon == t_canon and s != t:
            if 0.9 > best:
                best, via = SYNONYM_CREDIT, "synonym"
            continue
        if fuzz is not None and fuzz.token_set_ratio(s, t) >= FUZZY_THRESHOLD:
            if SIMILAR_CREDIT > best:
                best, via = SIMILAR_CREDIT, "similar"
    return best, via


def _canon_list(values, synonyms: Optional[Dict[str, str]] = None) -> List[str]:
    return sorted({canonical_skill(v, synonyms) for v in values if _norm(v)})


def parse_cgpa(raw: Any) -> Optional[float]:
    """None when blank; ValueError when not a number in 0-10."""
    if raw is None:
        return None
    text = str(raw).strip()
    if text == "":
        return None
    try:
        value = float(text)
    except ValueError:
        raise ValueError("CGPA must be a number between 0 and 10.")
    if value < 0 or value > 10:
        raise ValueError("CGPA must be between 0 and 10.")
    return value


# --------------------------------------------------------------------------- #
# STAGE 1 — Eligibility gates (skills are never gates)
# --------------------------------------------------------------------------- #
def _gate_degree(profile: Dict[str, Any], opp: Dict[str, Any]) -> Dict[str, str]:
    allowed = opp.get("eligible_degrees")
    if not allowed:
        # No stated restriction means the opportunity is open on this gate.
        return {"gate": "Degree", "status": "pass", "detail": "No degree restriction stated."}
    if "any" in {_norm(a) for a in allowed}:
        return {"gate": "Degree", "status": "pass", "detail": "Open to any degree."}
    if _norm(profile.get("degree")) in {_norm(a) for a in allowed}:
        return {"gate": "Degree", "status": "pass", "detail": f"{profile.get('degree')} is listed."}
    return {"gate": "Degree", "status": "fail",
            "detail": f"Requires {'/'.join(allowed)}; you are {profile.get('degree') or 'unspecified'}."}


def _gate_branch(profile: Dict[str, Any], opp: Dict[str, Any]) -> Dict[str, str]:
    allowed = opp.get("eligible_branches")
    if not allowed:
        return {"gate": "Branch", "status": "pass", "detail": "No branch restriction stated."}
    pb = _norm(profile.get("branch"))
    for a in allowed:
        na = _norm(a)
        if na == "any" or (pb and (pb in na or na in pb)):
            return {"gate": "Branch", "status": "pass", "detail": f"Your branch matches '{a}'."}
    return {"gate": "Branch", "status": "fail",
            "detail": f"Restricted to {'/'.join(allowed)}; you are {profile.get('branch') or 'unspecified'}."}


def _gate_year(profile: Dict[str, Any], opp: Dict[str, Any]) -> Dict[str, str]:
    years = opp.get("eligible_years")
    if not years:
        return {"gate": "Year", "status": "unknown", "detail": "No preferred year stated."}
    if profile.get("year") in years:
        return {"gate": "Year", "status": "pass", "detail": f"Year {profile.get('year')} is accepted."}
    return {"gate": "Year", "status": "fail",
            "detail": f"Open to year(s) {', '.join(str(y) for y in years)}; you are year {profile.get('year')}."}


def _gate_cgpa(profile: Dict[str, Any], opp: Dict[str, Any]) -> Dict[str, str]:
    min_cgpa = opp.get("min_cgpa")
    cgpa = profile.get("cgpa")
    if min_cgpa is None:
        return {"gate": "CGPA", "status": "unknown", "detail": "No minimum CGPA stated."}
    if cgpa is None:
        return {"gate": "CGPA", "status": "unknown", "detail": f"Requires {min_cgpa}; your CGPA is not provided."}
    if cgpa >= min_cgpa:
        return {"gate": "CGPA", "status": "pass", "detail": f"Requires {min_cgpa}; you have {cgpa}."}
    return {"gate": "CGPA", "status": "fail", "detail": f"Requires {min_cgpa}; you have {cgpa} (short by {round(min_cgpa - cgpa, 2)})."}


def _gate_women(profile: Dict[str, Any], opp: Dict[str, Any]) -> Optional[Dict[str, str]]:
    if not opp.get("women_only"):
        return None
    gender = _norm(profile.get("gender"))
    if gender == "female":
        return {"gate": "Women only", "status": "pass", "detail": "Restricted to women; you qualify."}
    if gender in ("male",):
        return {"gate": "Women only", "status": "fail", "detail": "Restricted to women applicants."}
    return {"gate": "Women only", "status": "unknown",
            "detail": "Restricted to women; your gender is not specified in the profile."}


def evaluate_eligibility(profile: Dict[str, Any], opp: Dict[str, Any], today: _dt.date) -> Dict[str, Any]:
    """Gate-by-gate eligibility. fail -> Ineligible; else unknown -> Potentially Eligible."""
    gates = [_gate_degree(profile, opp), _gate_branch(profile, opp),
             _gate_year(profile, opp), _gate_cgpa(profile, opp)]
    wg = _gate_women(profile, opp)
    if wg:
        gates.append(wg)

    if any(g["status"] == "fail" for g in gates):
        status = "Ineligible"
    elif any(g["status"] == "unknown" for g in gates):
        status = "Potentially Eligible"
    else:
        status = "Eligible"

    verify = [f"{g['gate']}: {g['detail']}" for g in gates if g["status"] == "unknown"]
    return {"status": status, "gates": gates, "verify": verify}


# --------------------------------------------------------------------------- #
# STAGE 2 — Timing (separate from eligibility)
# --------------------------------------------------------------------------- #
def resolve_deadline(opp: Dict[str, Any], today: _dt.date, demo_mode: bool) -> Optional[str]:
    """A sample record's illustrative deadline is only materialised in Demo Mode."""
    if _iso(opp.get("deadline")):
        return opp["deadline"]
    offset = opp.get("demo_deadline_offset_days")
    if demo_mode and offset is not None and opp.get("verification_status") == "sample":
        return (today + _dt.timedelta(days=int(offset))).isoformat()
    return None


def timing_status(opp: Dict[str, Any], today: _dt.date, demo_mode: bool = False) -> str:
    if _norm(opp.get("verification_status")) == "closed":
        return "closed"
    if _norm(opp.get("deadline_kind")) == "rolling":
        return "rolling"

    opens = _as_date(_iso(opp.get("opens_on")))
    if opens and opens > today:
        return "not_yet_open"

    deadline = _as_date(resolve_deadline(opp, today, demo_mode))
    if deadline:
        if deadline < today:
            return "closed"
        if (deadline - today).days <= RADAR_THRESHOLDS["closing_soon_days"]:
            return "closing_soon"
        return "open"
    return "unknown"


# --------------------------------------------------------------------------- #
# STAGE 3 — Fit
# --------------------------------------------------------------------------- #
def _skill_component(profile: Dict[str, Any], opp: Dict[str, Any], synonyms: Dict[str, str]) -> Dict[str, Any]:
    student = profile.get("skills") or []
    required = opp.get("required_skills") or []
    preferred = opp.get("preferred_skills") or []

    matched: List[Dict[str, str]] = []
    req_credits: List[float] = []
    for s in required:
        c, via = skill_credit(student, s, synonyms)
        req_credits.append(c)
        if c > 0:
            matched.append({"skill": canonical_skill(s, synonyms), "via": via or "exact"})

    pref_credits: List[float] = []
    for s in preferred:
        c, via = skill_credit(student, s, synonyms)
        pref_credits.append(c)
        if c > 0:
            matched.append({"skill": canonical_skill(s, synonyms), "via": via or "exact"})

    required_coverage = (sum(req_credits) / len(req_credits)) if req_credits else 1.0

    # Required skills weigh 2x preferred.
    num = 2.0 * sum(req_credits) + 1.0 * sum(pref_credits)
    den = 2.0 * len(req_credits) + 1.0 * len(pref_credits)
    coverage = (num / den) if den else 0.6

    missing = _canon_list([s for s, c in zip(required, req_credits) if c == 0.0], synonyms)
    # de-duplicate matched by skill
    seen, dedup = set(), []
    for m in matched:
        if m["skill"] not in seen:
            seen.add(m["skill"])
            dedup.append(m)

    return {"score": round(coverage, 4), "required_coverage": round(required_coverage, 4),
            "matched": dedup, "missing": missing}


def _interest_component(profile: Dict[str, Any], opp: Dict[str, Any]) -> float:
    mine = {_norm(i) for i in (profile.get("interests") or [])}
    theirs = [_norm(i) for i in (opp.get("interests") or []) if _norm(i)]
    if not mine or not theirs:
        return 0.5
    overlap = len(mine & set(theirs))
    return round(min(1.0, overlap / min(3, len(theirs))), 4)


def _academic_component(profile: Dict[str, Any], opp: Dict[str, Any]) -> Dict[str, Any]:
    min_cgpa = opp.get("min_cgpa")
    cgpa = profile.get("cgpa")
    unconfirmed: List[str] = []

    if min_cgpa is None or cgpa is None:
        unconfirmed.append("Minimum CGPA could not be checked (not stated, or not provided).")
        return {"score": 0.5, "unconfirmed": unconfirmed}   # neutral, never penalised

    parts = []
    years = opp.get("eligible_years")
    parts.append(1.0 if (not years or profile.get("year") in years) else 0.4)
    parts.append(1.0 if cgpa >= min_cgpa else 0.0)
    degrees = opp.get("eligible_degrees")
    if not degrees or "any" in {_norm(d) for d in degrees}:
        parts.append(1.0)
    else:
        parts.append(1.0 if _norm(profile.get("degree")) in {_norm(d) for d in degrees} else 0.4)
    return {"score": round(sum(parts) / len(parts), 4), "unconfirmed": unconfirmed}


def _workmode_component(profile: Dict[str, Any], opp: Dict[str, Any]) -> float:
    pref, mode = _norm(profile.get("work_mode")), _norm(opp.get("work_mode"))
    if not pref or pref == "any" or pref == mode:
        mode_part = 1.0
    elif pref in mode or mode in pref:
        mode_part = 0.8
    else:
        mode_part = 0.2
    pl, ol = _norm(profile.get("location")), _norm(opp.get("location"))
    if not pl or pl == "any" or not ol or pl in ol or ol in pl:
        loc_part = 1.0
    else:
        loc_part = 0.6
    return round(0.7 * mode_part + 0.3 * loc_part, 4)


def _experience_component(profile: Dict[str, Any], opp: Dict[str, Any]) -> float:
    student = EXPERIENCE_ORDER.get(profile.get("experience"), 1)
    required = EXPERIENCE_ORDER.get(opp.get("experience_level", "Intermediate"), 1)
    gap = required - student
    return 1.0 if gap <= 0 else (0.5 if gap == 1 else 0.2)


def score_opportunity(profile: Dict[str, Any], opp: Dict[str, Any],
                      weights: Optional[Dict[str, float]] = None,
                      synonyms: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    weights = weights or DEFAULT_WEIGHTS
    total_weight = sum(weights.values()) or 1.0
    synonyms = synonyms or {}

    sk = _skill_component(profile, opp, synonyms)
    interest = _interest_component(profile, opp)
    ac = _academic_component(profile, opp)
    wm = _workmode_component(profile, opp)
    ex = _experience_component(profile, opp)

    components = {"skill": sk["score"], "interest": interest, "academic": ac["score"],
                  "workmode": wm, "experience": ex}
    total = sum(components[k] * weights.get(k, 0.0) for k in components) / total_weight

    unconfirmed = list(ac["unconfirmed"])
    if not opp.get("verified") and opp.get("verification_status") == "sample":
        unconfirmed.append("Sample record — verify eligibility and dates on the official site.")
    if not resolve_deadline(opp, today(), True) and opp.get("deadline_kind") != "rolling":
        unconfirmed.append("No deadline available to check.")

    return {
        "opportunity": opp,
        "total": round(total, 4),
        "score_pct": round(total * 100, 1),
        "components": {k: round(v * 100, 1) for k, v in components.items()},
        "required_coverage": sk["required_coverage"],
        "matched": sk["matched"],
        "missing": sk["missing"],
        "unconfirmed": unconfirmed,
        # kept for backwards-compatible callers
        "matched_skills": [m["skill"] for m in sk["matched"]],
        "missing_required": sk["missing"],
    }


# --------------------------------------------------------------------------- #
# STAGE 4 — Counterfactuals
# --------------------------------------------------------------------------- #
def counterfactuals(profile: Dict[str, Any], opp: Dict[str, Any],
                    weights: Optional[Dict[str, float]] = None,
                    synonyms: Optional[Dict[str, str]] = None,
                    max_n: int = 3) -> List[Dict[str, Any]]:
    """Re-run the SAME score function with each missing skill added."""
    synonyms = synonyms or {}
    base = score_opportunity(profile, opp, weights, synonyms)["score_pct"]
    out = []
    for skill in (opp.get("required_skills") or []):
        if skill_credit(profile.get("skills") or [], skill, synonyms)[0] > 0:
            continue
        trial = dict(profile)
        trial["skills"] = list(profile.get("skills") or []) + [skill]
        after = score_opportunity(trial, opp, weights, synonyms)["score_pct"]
        delta = round(after - base, 1)
        if delta >= COUNTERFACTUAL_MIN_DELTA:
            out.append({"skill": canonical_skill(skill, synonyms), "before_pct": base,
                        "after_pct": after, "delta": delta})
    out.sort(key=lambda x: x["delta"], reverse=True)
    return out[:max_n]


def top_skill_gains(profile: Dict[str, Any], opps: List[Dict[str, Any]],
                    weights: Optional[Dict[str, float]] = None,
                    today: Optional[_dt.date] = None,
                    synonyms: Optional[Dict[str, str]] = None,
                    demo_mode: bool = True) -> List[Dict[str, Any]]:
    """Aggregate counterfactual gain across the top 10 non-ineligible matches."""
    synonyms = synonyms or {}
    today = today or globals()["today"]()
    pool = [o for o in opps
            if evaluate_eligibility(profile, o, today)["status"] != "Ineligible"
            and timing_status(o, today, demo_mode) != "closed"]
    pool = sorted(pool, key=lambda o: score_opportunity(profile, o, weights, synonyms)["score_pct"],
                  reverse=True)[:10]
    agg: Dict[str, List[float]] = {}
    for o in pool:
        for c in counterfactuals(profile, o, weights, synonyms, max_n=99):
            agg.setdefault(c["skill"], []).append(c["delta"])
    out = [{"skill": s, "opportunities_lifted": len(d), "avg_gain": round(sum(d) / len(d), 1)}
           for s, d in agg.items()]
    out.sort(key=lambda x: (x["avg_gain"], x["opportunities_lifted"]), reverse=True)
    return out


# --------------------------------------------------------------------------- #
# Opportunity Radar — each opportunity lands in exactly one pane or Why Not
# --------------------------------------------------------------------------- #
def _exclusion_reason(elig: Dict[str, Any], timing: str) -> Optional[Tuple[str, str]]:
    if elig["status"] == "Ineligible":
        fails = [g for g in elig["gates"] if g["status"] == "fail"]
        reason = fails[0]["detail"] if fails else "Does not meet a stated requirement."
        fixes = {
            "CGPA": "Improve your CGPA, or look for a similar role with a lower cutoff.",
            "Year": "Revisit this in a later year of study.",
            "Degree": "Look for an opportunity open to your degree.",
            "Branch": "Look for an opportunity open to your branch.",
            "Women only": "This programme is restricted to women applicants.",
        }
        fix = fixes.get(fails[0]["gate"], "Check whether an exception applies.") if fails else ""
        return reason, fix
    if timing == "closed":
        return ("Applications are closed for this listing.",
                "Look for the next intake, or a similar currently-open opportunity.")
    return None


def build_radar(profile: Dict[str, Any], opps: List[Dict[str, Any]],
                weights: Optional[Dict[str, float]] = None,
                today: Optional[_dt.date] = None,
                demo_mode: bool = True,
                synonyms: Optional[Dict[str, str]] = None,
                knowledge: Optional[Dict[str, Any]] = None) -> Dict[str, List[Dict[str, Any]]]:
    weights = weights or DEFAULT_WEIGHTS
    today = today or globals()["today"]()
    knowledge = knowledge or {}
    synonyms = synonyms if synonyms is not None else knowledge.get("skill_synonyms", {})
    bridges = knowledge.get("domain_bridges", {})

    panes: Dict[str, List[Dict[str, Any]]] = {"apply_now": [], "prepare_for": [], "explore": [], "excluded": []}
    branch_key = _norm(profile.get("branch"))
    branch_bridges = bridges.get(branch_key, [])

    for opp in opps:
        elig = evaluate_eligibility(profile, opp, today)
        timing = timing_status(opp, today, demo_mode)
        sc = score_opportunity(profile, opp, weights, synonyms)
        fit = sc["score_pct"]
        cov = sc["required_coverage"]

        reason = _exclusion_reason(elig, timing)
        if reason:
            panes["excluded"].append({"opportunity": opp, "eligibility": elig, "timing": timing,
                                      "score": sc, "fit": fit, "required_coverage": cov,
                                      "deadline": resolve_deadline(opp, today, demo_mode),
                                      "reason": reason[0], "fix": reason[1]})
            continue

        deadline = resolve_deadline(opp, today, demo_mode)
        has_timing_signal = bool(deadline) or _norm(opp.get("deadline_kind")) == "rolling"
        eligibleish = elig["status"] in ("Eligible", "Potentially Eligible")
        openish = timing in ("open", "closing_soon", "rolling")

        item = {"opportunity": opp, "eligibility": elig, "timing": timing, "score": sc,
                "fit": fit, "required_coverage": cov, "deadline": deadline}

        if eligibleish and openish and has_timing_signal \
                and cov >= RADAR_THRESHOLDS["apply_min_coverage"] and fit >= RADAR_THRESHOLDS["apply_min_fit"]:
            item["next_action"] = "Apply now — check the official listing for the current dates."
            panes["apply_now"].append(item)
            continue

        if eligibleish and fit >= RADAR_THRESHOLDS["prepare_min_fit"] and \
                (cov < RADAR_THRESHOLDS["apply_min_coverage"] or timing in ("not_yet_open", "unknown")):
            item["next_action"] = _next_action_for(profile, opp, sc, knowledge)
            panes["prepare_for"].append(item)
            continue

        # Explore is the explicit catch-all so nothing silently disappears.
        matched_bridge = _bridge_for(opp, branch_bridges)
        item["bridge"] = matched_bridge
        item["next_action"] = _next_action_for(profile, opp, sc, knowledge)
        panes["explore"].append(item)

    def _sort(items):
        return sorted(items, key=lambda x: (-x["fit"],
                                            x["deadline"] or "9999-12-31",
                                            x["opportunity"]["id"]))

    panes["apply_now"] = _sort(panes["apply_now"])
    panes["prepare_for"] = _sort(panes["prepare_for"])
    panes["explore"] = _sort(panes["explore"])
    panes["excluded"] = sorted(panes["excluded"], key=lambda x: x["opportunity"]["id"])
    return panes


def _bridge_for(opp: Dict[str, Any], branch_bridges: List[Dict[str, str]]) -> Optional[Dict[str, str]]:
    """Return the first domain bridge whose area overlaps the opportunity's interests."""
    opp_tags = {_norm(i) for i in (opp.get("interests") or [])}
    for b in branch_bridges:
        area = _norm(b.get("area"))
        if not area:
            continue
        if any(area in t or t in area for t in opp_tags):
            return b
    return None


def _next_action_for(profile: Dict[str, Any], opp: Dict[str, Any], sc: Dict[str, Any],
                     knowledge: Dict[str, Any]) -> str:
    playbook = knowledge.get("skill_playbook", {})
    missing = sc.get("missing") or []
    if missing:
        skill = missing[0]
        entry = playbook.get(_norm(skill), playbook.get("_generic", {}))
        return f"Build the missing skill '{skill}': {entry.get('project', 'start a small project using it.')}"
    if sc["required_coverage"] >= RADAR_THRESHOLDS["apply_min_coverage"]:
        return "You already cover the required skills — polish your CV and apply."
    return "Strengthen your profile with one portfolio project in this area."


# --------------------------------------------------------------------------- #
# Resume → Evidence Matrix (deterministic first)
# --------------------------------------------------------------------------- #
_SECTION_HEADINGS = {
    "skills": ["skills", "technical skills", "technologies", "tech stack"],
    "projects": ["projects", "personal projects", "academic projects"],
    "experience": ["experience", "work experience", "internship", "internships", "employment"],
    "education": ["education", "academics"],
}


def split_sentences(text: str) -> List[str]:
    """Split into sentences that remain verbatim substrings of the input."""
    if not text:
        return []
    parts: List[str] = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        for chunk in re.split(r"(?<=[.!?;])\s+", line):
            chunk = chunk.strip()
            if chunk:
                parts.append(chunk)
    return parts


def _section_of(line: str) -> Optional[str]:
    low = _norm(line).rstrip(":")
    for section, keys in _SECTION_HEADINGS.items():
        for k in keys:
            if low == k or low.startswith(k + ":") or (len(low) < 30 and k in low):
                return section
    return None


def evidence_matrix(resume_text: str, opp: Dict[str, Any],
                    synonyms: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
    """Word-boundary search for each required skill; returns verbatim quotes."""
    synonyms = synonyms or {}
    rows: List[Dict[str, Any]] = []
    sentences = split_sentences(resume_text or "")

    # Track the current section as we walk the resume.
    section_for: Dict[str, str] = {}
    current = "Other"
    for line in (resume_text or "").split("\n"):
        s = _section_of(line)
        if s:
            current = s
        section_for[line.strip()] = current

    for req in (opp.get("required_skills") or []):
        canon = canonical_skill(req, synonyms)
        candidates = {_norm_skill(req), _norm_skill(canon)}
        syn = _synonym_canon(synonyms)
        if syn.get(_norm_skill(req)):
            candidates.add(syn[_norm_skill(req)])
        for k, v in syn.items():
            if v == _norm_skill(canon):
                candidates.add(k)
        candidates = {c for c in candidates if c}

        found_quote, found_section = None, "Other"
        for sent in sentences:
            ns = _norm_skill(sent)
            for cand in candidates:
                if re.search(r"(?<![a-z0-9])" + re.escape(cand) + r"(?![a-z0-9])", ns):
                    found_quote = sent[:QUOTE_MAX]
                    # section of the line this sentence came from
                    for line, sec in section_for.items():
                        if sent in line:
                            found_section = sec
                            break
                    break
            if found_quote:
                break

        if not found_quote:
            label = "No evidence"
        elif found_section in ("projects", "experience"):
            label = "Demonstrated"
        elif found_section == "skills":
            label = "Listed only"
        else:
            label = "Listed only"

        rows.append({
            "requirement": canon,
            "label": label,
            "quote": found_quote,
            "section": (found_section or "Other").title(),
        })
    return rows


def validate_quote(quote: Optional[str], resume_text: str) -> bool:
    """A quote is only accepted if it really appears in the resume."""
    if not quote:
        return False
    if quote in (resume_text or ""):
        return True
    # tolerate whitespace reflow, but require the words to match in order
    norm_q = re.sub(r"\s+", " ", quote).strip().lower()
    norm_r = re.sub(r"\s+", " ", resume_text or "").strip().lower()
    return bool(norm_q) and norm_q in norm_r


def prep_kit_template(profile: Dict[str, Any], resume_text: str, opp: Dict[str, Any],
                      knowledge: Optional[Dict[str, Any]] = None,
                      synonyms: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    knowledge = knowledge or {}
    playbook = knowledge.get("skill_playbook", {})
    synonyms = synonyms if synonyms is not None else knowledge.get("skill_synonyms", {})

    rows = evidence_matrix(resume_text, opp, synonyms)
    checklist = []
    for r in rows:
        if r["label"] == "No evidence":
            checklist.append(f"Add evidence for **{r['requirement']}** — add a bullet only if you have "
                             f"actually done this work; otherwise do not claim it.")
        elif r["label"] == "Listed only":
            checklist.append(f"**{r['requirement']}** is listed but not shown in a project. Add a project "
                             f"bullet only if it is real; otherwise build one small project first.")

    missing = [r["requirement"] for r in rows if r["label"] != "Demonstrated"]
    topics = [f"Typical topics for {opp.get('category', 'this kind of role')} — not confirmed by the organisation:",
              "Fundamentals of the required skills listed above.",
              "One walkthrough of a project from your resume, end to end.",
              "How you would approach a small task typical of the role."]

    plan = []
    focus_pool = missing or [r["requirement"] for r in rows]
    for day in range(1, 8):
        skill = focus_pool[(day - 1) % len(focus_pool)] if focus_pool else "General preparation"
        entry = playbook.get(_norm(skill), playbook.get("_generic", {}))
        plan.append({
            "day": day,
            "focus": skill,
            "tasks": [entry.get("task", "Spend a focused session on the basics."),
                      entry.get("project", "Start a small project using it.")],
            "hours": 2,
            "output": entry.get("project", "A small artefact you can show."),
        })

    return {"evidence": rows, "resume_checklist": checklist,
            "interview_topics": topics, "plan": plan,
            "note": "Guidance only. This does not predict selection and is not confirmed by the organisation."}


# --------------------------------------------------------------------------- #
# Skill-gap analyzer + roadmap (preserved)
# --------------------------------------------------------------------------- #
def skill_gap(profile: Dict[str, Any], selected: List[Dict[str, Any]],
              knowledge: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    knowledge = knowledge or {}
    synonyms = knowledge.get("skill_synonyms", {})
    have = {_norm_skill(s) for s in (profile.get("skills") or [])}
    required_union, matched = set(), set()
    for item in selected:
        opp = item.get("opportunity", item)
        for s in opp.get("required_skills", []):
            required_union.add(_norm_skill(s))
        for m in item.get("matched", []):
            matched.add(_norm_skill(m["skill"]))
    missing = sorted(required_union - have)
    return {"matching_skills": _canon_list(matched, synonyms),
            "missing_skills": _canon_list(missing, synonyms),
            "learning_plan": _learning_plan(_canon_list(missing, synonyms), knowledge)}


def _learning_plan(missing: List[str], knowledge: Dict[str, Any]) -> List[Dict[str, str]]:
    playbook = knowledge.get("skill_playbook", {})
    priority_rank = {"python": 0, "git": 1, "sql": 2, "data structures": 3,
                     "excel": 4, "linux": 5, "communication": 6, "technical writing": 7}
    ordered = sorted(missing, key=lambda s: (priority_rank.get(s.lower(), 50), s))
    plan = []
    for i, skill in enumerate(ordered, start=1):
        entry = playbook.get(_norm(skill), playbook.get("_generic", {}))
        plan.append({"priority": str(i), "skill": skill,
                     "estimated_time": "2-4 weeks",
                     "practice_project": entry.get("project", f"Build one small project using {skill} end to end."),
                     "resource_type": entry.get("resource_type", "Official documentation.")})
    return plan


def build_roadmap(plan: List[Dict[str, str]], weeks: int = 12) -> List[str]:
    if not plan:
        return ["Your skill set already covers the requirements of the selected opportunities. "
                "Focus on building one strong portfolio project and applying widely."]
    per_phase = max(1, len(plan) // 4 or 1)
    chunks = [plan[i:i + per_phase] for i in range(0, len(plan), per_phase)]
    roadmap, week = [], 1
    step = max(1, 12 // max(1, len(chunks)))
    for chunk in chunks:
        names = ", ".join(c["skill"] for c in chunk)
        end = min(week + step - 1, 12)
        roadmap.append(f"Weeks {week}-{end}: Build foundations in {names}. Finish at least one practice project.")
        week = end + 1
    roadmap.append("Final 2 weeks: polish one flagship project, write a short report, and prepare your applications.")
    return roadmap


def fit_of(item: Dict[str, Any]) -> float:
    """Fit for either a radar item or a raw score dict."""
    if "fit" in item:
        return float(item["fit"])
    if isinstance(item.get("score"), dict):
        return float(item["score"].get("score_pct", 0.0))
    return float(item.get("score_pct", 0.0))


def strong_match_count(items: List[Dict[str, Any]], threshold: float = 70.0) -> int:
    return sum(1 for it in items if fit_of(it) >= threshold)


# --------------------------------------------------------------------------- #
# Information quality — field-level, and NEVER mixed with the fit score
# --------------------------------------------------------------------------- #
VERIFICATION_WEIGHT = {"verified": 1.0, "fetched": 0.6, "sample": 0.35, "closed": 0.0}


def information_completeness(opp: Dict[str, Any]) -> Dict[str, Any]:
    """Which fields are actually present, and whether the record is human-verified.

    Deliberately separate from fit: an opportunity can fit you well AND have an
    unverified deadline. These are different facts.
    """
    present = {
        "source": bool(opp.get("source_url")),
        "deadline": bool(opp.get("deadline")) or _norm(opp.get("deadline_kind")) == "rolling",
        "eligibility": bool(opp.get("eligibility")),
        "apply_url": bool(opp.get("apply_url")),
    }
    n = sum(1 for v in present.values() if v)
    status = opp.get("verification_status") or "sample"
    return {
        "fields": present,
        "present_count": n,
        "total": len(present),
        "completeness_pct": round(100 * n / len(present)),
        "verification_status": status,
        "human_verified": status == "verified",
        "last_verified": opp.get("last_verified"),
        "label": "Information completeness",
        "note": ("Measures how much of this record is actually stated, and whether a human has "
                 "checked it. It is NOT a guarantee of legitimacy and is NOT part of your fit score."),
    }


def _maxnorm(values: List[float]) -> List[float]:
    """Scale to (0, 1] by dividing by the maximum.

    Max-normalisation (not min-max) is deliberate: P is a product, so a factor that
    min-max maps to exactly 0 would zero the whole score for the worst candidate and
    collapse the ranking.
    """
    hi = max(values) if values else 0.0
    if hi <= 1e-9:
        return [1.0 for _ in values]
    return [v / hi for v in values]


def _target_opportunities(profile: Dict[str, Any], opps: List[Dict[str, Any]],
                          weights: Optional[Dict[str, float]], today: _dt.date,
                          synonyms: Dict[str, str], n: int,
                          demo_mode: bool = True) -> List[Dict[str, Any]]:
    # Actionable targets only: not ineligible, and not closed. Fully eligible ones
    # rank above "Potentially Eligible" ones, so the plan is built around opportunities
    # the student can actually pursue.
    scored = []
    for o in opps:
        if evaluate_eligibility(profile, o, today)["status"] == "Ineligible":
            continue
        if timing_status(o, today, demo_mode) == "closed":
            continue
        elig_rank = 0 if evaluate_eligibility(profile, o, today)["status"] == "Eligible" else 1
        scored.append((elig_rank, -score_opportunity(profile, o, weights, synonyms)["score_pct"], o["id"], o))
    scored.sort(key=lambda x: (x[0], x[1], x[2]))
    return [s[3] for s in scored[:n]]


# --------------------------------------------------------------------------- #
# ROI engine — "Your Next Best Move"
# --------------------------------------------------------------------------- #
def action_priority(profile: Dict[str, Any], opps: List[Dict[str, Any]],
                    weights: Optional[Dict[str, float]] = None,
                    today: Optional[_dt.date] = None,
                    knowledge: Optional[Dict[str, Any]] = None,
                    demo_mode: bool = True,
                    target_n: int = 5) -> List[Dict[str, Any]]:
    """Rank learning actions by  P = (R x G x C) / T  over the student's top targets.

        R = relevance: how many of your top targets ask for this skill, weighted by their fit
        G = gap:       average fit gain from actually re-running the score with the skill added
        C = confidence: source-verification weight of the records driving the action
        T = effort:    labelled estimate in hours from the skill playbook

    R, G and C are min-max normalised; T is normalised by the largest estimate. Every number
    is derived from the dataset and the real scoring function — nothing is model-generated.
    """
    knowledge = knowledge or {}
    synonyms = knowledge.get("skill_synonyms", {})
    playbook = knowledge.get("skill_playbook", {})
    weights = weights or DEFAULT_WEIGHTS
    today = today or globals()["today"]()

    targets = _target_opportunities(profile, opps, weights, today, synonyms, target_n, demo_mode)
    if not targets:
        return []

    cand: Dict[str, Dict[str, Any]] = {}
    for opp in targets:
        base = score_opportunity(profile, opp, weights, synonyms)["score_pct"]
        elig_status = evaluate_eligibility(profile, opp, today)["status"]
        for skill in (opp.get("required_skills") or []):
            if skill_credit(profile.get("skills") or [], skill, synonyms)[0] > 0:
                continue
            trial = dict(profile)
            trial["skills"] = list(profile.get("skills") or []) + [skill]
            after = score_opportunity(trial, opp, weights, synonyms)["score_pct"]
            gain = after - base
            if gain < COUNTERFACTUAL_MIN_DELTA:
                continue
            canon = canonical_skill(skill, synonyms)
            entry = cand.setdefault(canon, {"skill": canon, "targets": [], "gains": [], "conf": []})
            # A potentially-eligible target counts for less: you may not be able to act on it.
            elig_weight = 1.0 if elig_status == "Eligible" else 0.6
            entry["targets"].append({"id": opp["id"], "title": opp["title"], "before": base,
                                     "after": after, "eligibility": elig_status})
            entry["gains"].append(gain)
            entry["conf"].append(VERIFICATION_WEIGHT.get(opp.get("verification_status"), 0.35))
            entry.setdefault("elig_weights", []).append(elig_weight)

    if not cand:
        return []

    items = list(cand.values())
    r_raw = [sum(t["before"] * w for t, w in zip(it["targets"], it["elig_weights"])) / 100.0
             for it in items]
    g_raw = [sum(it["gains"]) / len(it["gains"]) for it in items]
    c_raw = [sum(it["conf"]) / len(it["conf"]) for it in items]
    hours = [float(playbook.get(_norm(it["skill"]), playbook.get("_generic", {})).get("hours", 16))
             for it in items]

    r_n, g_n, c_n = _maxnorm(r_raw), _maxnorm(g_raw), _maxnorm(c_raw)
    t_max = max(hours) or 1.0

    for i, it in enumerate(items):
        t_n = max(0.05, hours[i] / t_max)
        it["relevance"] = round(r_raw[i], 3)
        it["needs_verification"] = any(t.get("eligibility") == "Potentially Eligible"
                                       for t in it["targets"])
        it["gap"] = round(g_raw[i], 2)
        it["confidence"] = round(c_raw[i], 2)
        it["hours"] = int(hours[i])
        it["opportunities_lifted"] = len(it["targets"])
        it["priority"] = round((r_n[i] * g_n[i] * c_n[i]) / t_n, 4)
        entry = playbook.get(_norm(it["skill"]), playbook.get("_generic", {}))
        it["project"] = entry.get("project", "Start a small project that uses it end to end.")
        it["task"] = entry.get("task", "Spend focused sessions on the basics.")
        it["resource_type"] = entry.get("resource_type", "Official documentation.")
        caveat = (" One of these still needs its eligibility confirmed — check that first."
                  if it.get("needs_verification") else "")
        it["why"] = (
            f"{it['skill']} is asked for by {len(it['targets'])} of your top {len(targets)} target "
            f"opportunities. Learning it lifts your fit by an average of +{it['gap']:.1f} points on "
            f"{it['opportunities_lifted']} of them. Estimated effort: {it['hours']} hours (estimate)."
            + caveat
        )

    items.sort(key=lambda x: (-x["priority"], -x["gap"], x["hours"], x["skill"]))
    return items


def next_best_move(profile: Dict[str, Any], opps: List[Dict[str, Any]],
                   weights: Optional[Dict[str, float]] = None,
                   today: Optional[_dt.date] = None,
                   knowledge: Optional[Dict[str, Any]] = None,
                   demo_mode: bool = True, target_n: int = 5) -> Optional[Dict[str, Any]]:
    """The single highest-priority action, or None when there is nothing to improve."""
    actions = action_priority(profile, opps, weights, today, knowledge, demo_mode, target_n)
    return actions[0] if actions else None


def pathway(action: Dict[str, Any]) -> List[Dict[str, str]]:
    """A small skill -> project -> improved-fit chain for the top action."""
    steps = [
        {"stage": "You now", "detail": f"{action['skill']} is not yet on your profile."},
        {"stage": f"Learn {action['skill']}", "detail": f"{action['task']} (~{action['hours']} hours)."},
        {"stage": "Show it", "detail": action["project"]},
    ]
    for t in action["targets"][:3]:
        steps.append({"stage": f"{t['title']}",
                      "detail": f"Fit moves {t['before']:.0f}% → {t['after']:.0f}% "
                                f"(+{t['after'] - t['before']:.1f} pts)."})
    steps.append({"stage": "Improved readiness",
                  "detail": "A stronger profile for the roles you are already targeting."})
    return steps


# --------------------------------------------------------------------------- #
# "Why isn't this in Apply Now?" — a different outcome from failing eligibility
# --------------------------------------------------------------------------- #
def why_not_apply_now(item: Dict[str, Any],
                      knowledge: Optional[Dict[str, Any]] = None) -> List[Dict[str, str]]:
    """Explain why an item sits in Prepare For / Explore rather than Apply Now."""
    knowledge = knowledge or {}
    reasons: List[Dict[str, str]] = []
    elig = item.get("eligibility", {})
    timing = item.get("timing", "unknown")
    cov = item.get("required_coverage", 0.0)
    fit = item.get("fit", 0.0)

    if elig.get("status") == "Potentially Eligible":
        reasons.append({"check": "Eligibility", "status": "Potentially eligible",
                        "detail": "Not a failure — these still need confirming: "
                                  + "; ".join(elig.get("verify", [])[:2]),
                        "action": "Verify the listed fields on the official page."})
    else:
        reasons.append({"check": "Eligibility", "status": elig.get("status", "unknown"),
                        "detail": "All stated gates passed.", "action": "No action needed."})

    if timing in ("unknown", "not_yet_open"):
        reasons.append({"check": "Timing", "status": "Window not verified" if timing == "unknown" else "Opens later",
                        "detail": "No verified open application window, so it cannot sit in Apply Now.",
                        "action": "Check the official page for the current window."})
    elif timing == "closed":
        reasons.append({"check": "Timing", "status": "Closed",
                        "detail": "The deadline has passed.", "action": "Look for the next intake."})
    else:
        reasons.append({"check": "Timing", "status": timing.replace("_", " ").title(),
                        "detail": "There is a live window.", "action": "Apply once the other checks pass."})

    thr = RADAR_THRESHOLDS
    reasons.append({
        "check": "Required-skill coverage",
        "status": f"{cov * 100:.0f}% (needs {thr['apply_min_coverage'] * 100:.0f}%)",
        "detail": "You do not yet cover enough of the listed required skills."
                  if cov < thr["apply_min_coverage"] else "You cover enough of the required skills.",
        "action": "See the Next Move tab for the highest-value skill to add."
                  if cov < thr["apply_min_coverage"] else "No action needed.",
    })
    reasons.append({
        "check": "Overall fit",
        "status": f"{fit:.0f}% (needs {thr['apply_min_fit']:.0f}%)",
        "detail": "Below the Apply Now threshold." if fit < thr["apply_min_fit"]
                  else "Above the Apply Now threshold.",
        "action": "Raise your fit by closing skill gaps." if fit < thr["apply_min_fit"] else "No action needed.",
    })
    return reasons
