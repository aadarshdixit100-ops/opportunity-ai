"""
test_core.py — compact core tests. Time is frozen via OPPORTUNITYAI_TODAY.

Run:  python -m pytest tests -q
"""

import datetime as dt
import os

os.environ.setdefault("OPPORTUNITYAI_TODAY", "2026-10-25")
os.environ.setdefault("OPPORTUNITYAI_DB", "/tmp/opportunityai_test.db")

import pytest

import db
import recommender as R

TODAY = dt.date(2026, 10, 25)

DEMO = {
    "name": "Aarav", "college": "IIT (BHU)", "degree": "B.Tech",
    "branch": "Chemical Engineering", "year": 2, "cgpa": 8.2,
    "skills": ["Python", "Pandas", "Excel", "Thermodynamics", "Git", "SQL", "Data Visualization"],
    "interests": ["Data Science", "Machine Learning", "Chemical Engineering", "Research"],
    "work_mode": "Any", "location": "Any", "experience": "Beginner", "gender": "Prefer not to say",
}


@pytest.fixture(scope="module")
def opps():
    return R.load_opportunities()


@pytest.fixture(scope="module")
def know():
    return R.load_knowledge()


@pytest.fixture(scope="module")
def radar(opps, know):
    return R.build_radar(DEMO, opps, R.DEFAULT_WEIGHTS, TODAY, True, knowledge=know)


def _by_id(opps, oid):
    return next(o for o in opps if o["id"] == oid)


# --------------------------------------------------------------------------- #
def test_determinism(opps, know):
    a = [R.score_opportunity(DEMO, o, R.DEFAULT_WEIGHTS, know["skill_synonyms"])["score_pct"] for o in opps]
    b = [R.score_opportunity(DEMO, o, R.DEFAULT_WEIGHTS, know["skill_synonyms"])["score_pct"] for o in opps]
    assert a == b


def test_every_opportunity_in_exactly_one_pane(radar, opps):
    seen = []
    for pane in ("apply_now", "prepare_for", "explore", "excluded"):
        seen.extend(it["opportunity"]["id"] for it in radar[pane])
    assert len(seen) == len(opps)
    assert len(set(seen)) == len(seen)


def test_designed_record_1_eligible_apply_now(radar):
    ids = [it["opportunity"]["id"] for it in radar["apply_now"]]
    assert "OPP001" in ids
    it = next(i for i in radar["apply_now"] if i["opportunity"]["id"] == "OPP001")
    assert it["eligibility"]["status"] == "Eligible"
    assert it["required_coverage"] >= R.RADAR_THRESHOLDS["apply_min_coverage"]


def test_designed_record_2_potentially_eligible(radar):
    it = next(i for i in radar["apply_now"] if i["opportunity"]["id"] == "OPP002")
    assert it["eligibility"]["status"] == "Potentially Eligible"
    assert it["eligibility"]["verify"], "unknown gates must be listed for verification"


def test_designed_record_3_ineligible_by_cgpa(radar):
    it = next(i for i in radar["excluded"] if i["opportunity"]["id"] == "OPP003")
    assert it["eligibility"]["status"] == "Ineligible"
    assert "8.5" in it["reason"]
    # very high skill fit, but still ineligible
    assert it["fit"] > 70


def test_designed_record_4_prepare_for(radar):
    ids = [it["opportunity"]["id"] for it in radar["prepare_for"]]
    assert "OPP005" in ids


def test_designed_record_5_explore_with_bridge(radar):
    it = next(i for i in radar["explore"] if i["opportunity"]["id"] == "OPP021")
    assert it["bridge"] is not None
    assert it["bridge"]["area"]


def test_closed_is_not_ineligibility(radar):
    it = next(i for i in radar["excluded"] if i["opportunity"]["id"] == "OPP006")
    assert it["timing"] == "closed"
    assert it["eligibility"]["status"] != "Ineligible"   # closed != ineligible
    assert "closed" in it["reason"].lower()


def test_unknown_requirement_is_not_a_failure(opps):
    opp = dict(_by_id(opps, "OPP002"))       # min_cgpa None, eligible_years None
    elig = R.evaluate_eligibility(DEMO, opp, TODAY)
    assert elig["status"] == "Potentially Eligible"
    assert all(g["status"] != "fail" for g in elig["gates"])


# --------------------------------------------------------------------------- #
def test_counterfactual_invariants(opps, know):
    syn = know["skill_synonyms"]
    for oid in ("OPP001", "OPP009", "OPP020"):
        opp = _by_id(opps, oid)
        base = R.score_opportunity(DEMO, opp, R.DEFAULT_WEIGHTS, syn)["score_pct"]
        for skill in (opp.get("required_skills") or []):
            trial = dict(DEMO)
            trial["skills"] = list(DEMO["skills"]) + [skill]
            after = R.score_opportunity(trial, opp, R.DEFAULT_WEIGHTS, syn)["score_pct"]
            assert after >= base - 1e-9, "adding a skill must never lower the fit"


def test_ineligible_stays_ineligible_after_skill_added(opps, know):
    syn = know["skill_synonyms"]
    opp = _by_id(opps, "OPP003")             # needs CGPA 8.5
    assert R.evaluate_eligibility(DEMO, opp, TODAY)["status"] == "Ineligible"
    trial = dict(DEMO)
    trial["skills"] = list(DEMO["skills"]) + ["Machine Learning", "Data Visualization"]
    assert R.evaluate_eligibility(trial, opp, TODAY)["status"] == "Ineligible"


def test_counterfactual_returns_gain(opps, know):
    cf = R.counterfactuals(DEMO, _by_id(opps, "OPP001"), R.DEFAULT_WEIGHTS, know["skill_synonyms"])
    assert cf, "OPP001 has a missing required skill for the demo profile"
    assert all(c["delta"] >= R.COUNTERFACTUAL_MIN_DELTA for c in cf)
    assert all(c["after_pct"] > c["before_pct"] for c in cf)


# --------------------------------------------------------------------------- #
RESUME = """Aarav Sharma
Email: aarav@example.com

Skills
Python, SQL, Excel, Git

Projects
Built a sales dashboard using Python and SQL that cut reporting time by half.
"""


def test_evidence_labels(opps, know):
    rows = R.evidence_matrix(RESUME, _by_id(opps, "OPP001"), know["skill_synonyms"])
    by = {r["requirement"]: r for r in rows}
    assert by["Excel"]["label"] == "Listed only"
    assert by["Data Visualization"]["label"] == "No evidence"
    assert by["Excel"]["quote"] and by["Excel"]["quote"] in RESUME


def test_fabricated_quote_is_rejected():
    assert R.validate_quote("I led a team of 50 engineers at Google", RESUME) is False
    assert R.validate_quote("Built a sales dashboard using Python and SQL", RESUME) is True


def test_prep_kit_is_deterministic_and_safe(opps, know):
    kit = R.prep_kit_template(DEMO, RESUME, _by_id(opps, "OPP001"), know)
    assert len(kit["plan"]) == 7
    assert all("http" not in d["output"] for d in kit["plan"])   # no invented URLs
    assert any("only if" in c.lower() for c in kit["resume_checklist"])


# --------------------------------------------------------------------------- #
def test_timing_status(opps):
    assert R.timing_status(_by_id(opps, "OPP006"), TODAY, True) == "closed"
    assert R.timing_status(_by_id(opps, "OPP002"), TODAY, True) == "rolling"
    assert R.timing_status(_by_id(opps, "OPP004"), TODAY, True) == "not_yet_open"
    assert R.timing_status(_by_id(opps, "OPP008"), TODAY, True) == "closing_soon"


def test_demo_mode_controls_illustrative_deadlines(opps):
    opp = _by_id(opps, "OPP001")
    assert R.resolve_deadline(opp, TODAY, True) is not None      # demo mode on
    assert R.resolve_deadline(opp, TODAY, False) is None         # off -> unknown


def test_cgpa_validation():
    assert R.parse_cgpa("8.2") == 8.2
    assert R.parse_cgpa("") is None
    for bad in ("11", "abc", "-1"):
        with pytest.raises(ValueError):
            R.parse_cgpa(bad)


# --------------------------------------------------------------------------- #
def test_stage_transitions_recorded():
    os.environ["OPPORTUNITYAI_DB"] = "/tmp/opportunityai_test.db"
    if os.path.exists("/tmp/opportunityai_test.db"):
        os.remove("/tmp/opportunityai_test.db")
    db.init_db()
    db.set_stage("OPP001", "Shortlisted")
    db.set_stage("OPP001", "Preparing")
    hist = db.get_stage_history("OPP001")
    assert len(hist) == 2
    assert hist[0]["from_stage"] is None and hist[0]["to_stage"] == "Shortlisted"
    assert hist[1]["from_stage"] == "Shortlisted" and hist[1]["to_stage"] == "Preparing"
    apps = db.get_applications()
    assert apps[0]["opportunity_id"] == "OPP001" and apps[0]["stage"] == "Preparing"


def test_wipe_all_clears_data():
    db.set_stage("OPP002", "Applied")
    db.set_skill_state("Docker", "Learning", "notes")
    db.wipe_all()
    assert db.get_applications() == []
    assert db.get_skill_states() == {}


# --------------------------------------------------------------------------- #
# Your Next Best Move (ROI engine)
# --------------------------------------------------------------------------- #
def test_next_best_move_is_ranked_and_explainable(opps, know):
    acts = R.action_priority(DEMO, opps, R.DEFAULT_WEIGHTS, TODAY, know, True, target_n=5)
    assert acts, "the demo profile has gaps in its top targets"
    top = acts[0]
    for key in ("skill", "priority", "hours", "gap", "confidence", "why", "project", "targets"):
        assert key in top, f"missing {key}"
    assert top["hours"] > 0 and top["gap"] > 0 and top["priority"] > 0
    assert "estimated" in top["why"].lower() or "estimate" in top["why"].lower()
    # ranked descending by priority
    assert [a["priority"] for a in acts] == sorted([a["priority"] for a in acts], reverse=True)


def test_priority_never_collapses_to_zero(opps, know):
    """Regression: min-max normalisation used to zero the worst candidate and kill the ranking."""
    acts = R.action_priority(DEMO, opps, R.DEFAULT_WEIGHTS, TODAY, know, True, target_n=5)
    assert len(acts) >= 2
    assert all(a["priority"] > 0 for a in acts), "every ranked action must have a positive priority"


def test_closed_opportunities_are_not_targets(opps, know):
    closed_ids = {o["id"] for o in opps if R.timing_status(o, TODAY, True) == "closed"}
    targets = R._target_opportunities(DEMO, opps, R.DEFAULT_WEIGHTS, TODAY, know["skill_synonyms"], 8, True)
    assert closed_ids
    assert not (closed_ids & {o["id"] for o in targets})


def test_adding_recommended_skill_improves_targets(opps, know):
    """The gain quoted by the engine must be reproducible from the score function."""
    acts = R.action_priority(DEMO, opps, R.DEFAULT_WEIGHTS, TODAY, know, True, target_n=5)
    top = acts[0]
    for t in top["targets"]:
        opp = next(o for o in opps if o["id"] == t["id"])
        trial = dict(DEMO)
        trial["skills"] = list(DEMO["skills"]) + [top["skill"]]
        after = R.score_opportunity(trial, opp, R.DEFAULT_WEIGHTS, know["skill_synonyms"])["score_pct"]
        assert abs(after - t["after"]) < 0.05, "quoted 'after' fit must match the engine"


# --------------------------------------------------------------------------- #
# Information quality (trust panel) — separate from fit
# --------------------------------------------------------------------------- #
def test_information_completeness_is_separate_from_fit(opps, know):
    opp = _by_id(opps, "OPP003")          # high fit, low information completeness
    ic = R.information_completeness(opp)
    assert 0 <= ic["completeness_pct"] <= 100
    assert ic["human_verified"] is False          # sample records are not human-verified
    assert "not part of your fit score" in ic["note"].lower()
    assert "total" in ic and ic["total"] == 4


def test_why_not_apply_now_explains_without_calling_it_ineligible(opps, know):
    radar = R.build_radar(DEMO, opps, R.DEFAULT_WEIGHTS, TODAY, True, knowledge=know)
    item = next(i for i in radar["prepare_for"] if i["opportunity"]["id"] == "OPP020")
    checks = {r["check"]: r for r in R.why_not_apply_now(item, know)}
    assert "Required-skill coverage" in checks
    assert "Overall fit" in checks
    # coverage below the threshold is the reason, not an eligibility failure
    assert "needs 60%" in checks["Required-skill coverage"]["status"]
    assert item["eligibility"]["status"] != "Ineligible"


# --------------------------------------------------------------------------- #
# Evaluation suite
# --------------------------------------------------------------------------- #
def test_engine_evaluation_suite(opps, know):
    import evaluation
    rows = evaluation.run_all(opps, know)
    assert len(rows) == len(evaluation.EVAL_PROFILES)
    for r in rows:
        assert r["eligibility_accuracy"] == 1.0, f"{r['profile']}: eligibility mismatch"
        assert r["partition_complete"] is True, f"{r['profile']}: pane partition broken"
        assert r["coverage"] == 1.0
    mean_p5 = sum(r["precision_at_5"] for r in rows) / len(rows)
    assert mean_p5 >= 0.5, f"mean precision@5 too low: {mean_p5}"
