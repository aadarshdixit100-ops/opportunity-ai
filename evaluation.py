"""
evaluation.py — a small, explicit evaluation harness for the recommendation engine.

What this measures, and against what labels:

  * Eligibility classification — labelled `ineligible_ids` are the opportunities whose
    STATED mandatory requirements (CGPA, year, degree, women-only) the profile fails.
    This label is objective: it follows directly from the record fields. Accuracy is
    reported as "does the engine's Ineligible set match the labelled set".
  * Ranking quality — labelled `relevant_ids` are the AUTHOR'S judgement of which
    opportunities suit that profile. These are heuristic author labels for regression
    purposes, NOT expert ground truth. Precision/Recall/NDCG@5 are reported against them.
  * Structural properties — every opportunity must land in exactly one Radar pane
    (partition completeness) and the panes must cover the whole dataset (coverage).

Run:  python -m pytest tests -q     (the suite is asserted in tests/test_core.py)
      python3 evaluation.py          (prints a report)
"""

from __future__ import annotations

import datetime as _dt
import math
from typing import Any, Dict, List, Optional, Sequence

import recommender as R

TODAY = _dt.date(2026, 10, 25)


def _p(**kw) -> Dict[str, Any]:
    base = {"name": "eval", "degree": "B.Tech", "branch": "Computer Science", "year": 3,
            "cgpa": 8.0, "skills": [], "interests": [], "work_mode": "Any", "location": "Any",
            "experience": "Intermediate", "gender": "Prefer not to say"}
    base.update(kw)
    return base


EVAL_PROFILES: List[Dict[str, Any]] = [
    {
        "name": "Demo — 2nd year Chemical Engineering",
        "profile": _p(branch="Chemical Engineering", year=2, cgpa=8.2, experience="Beginner",
                      skills=["Python", "Pandas", "Excel", "Thermodynamics", "Git", "SQL", "Data Visualization"],
                      interests=["Data Science", "Machine Learning", "Chemical Engineering", "Research"]),
        "ineligible_ids": ["OPP003", "OPP004", "OPP011", "OPP014", "OPP019"],
        "relevant_ids": ["OPP001", "OPP002", "OPP005", "OPP009", "OPP010", "OPP017", "OPP020"],
    },
    {
        "name": "First year, CS, low experience",
        "profile": _p(year=1, cgpa=7.5, experience="Beginner", gender="Male",
                      skills=["Python"], interests=["Software Engineering", "Web Development", "Open Source"]),
        "ineligible_ids": ["OPP001", "OPP003", "OPP004", "OPP005", "OPP007", "OPP008", "OPP009",
                           "OPP010", "OPP011", "OPP012", "OPP014", "OPP017", "OPP018", "OPP019",
                           "OPP020", "OPP021"],
        "relevant_ids": ["OPP002", "OPP013", "OPP016"],
    },
    {
        "name": "Third year, high CGPA, strong skills",
        "profile": _p(year=3, cgpa=9.0, gender="Female", experience="Intermediate",
                      skills=["Python", "SQL", "Pandas", "Machine Learning"],
                      interests=["Data Science", "Research", "Machine Learning"]),
        "ineligible_ids": [],
        "relevant_ids": ["OPP001", "OPP002", "OPP003", "OPP004", "OPP009", "OPP011", "OPP017"],
    },
    {
        "name": "Strong skills but no CGPA given (incomplete academic data)",
        "profile": _p(branch="Chemical Engineering", year=3, cgpa=None, experience="Intermediate",
                      skills=["Python", "Process Simulation", "Aspen Plus", "Thermodynamics", "MATLAB"],
                      interests=["Chemical Engineering", "Energy", "Sustainability"]),
        # No CGPA means the CGPA gate is UNKNOWN, never a failure — so nothing is ineligible here.
        "ineligible_ids": [],
        "relevant_ids": ["OPP005", "OPP010", "OPP017", "OPP020", "OPP021"],
    },
    {
        "name": "Interdisciplinary — Mechanical, robotics interest",
        "profile": _p(branch="Mechanical Engineering", year=3, cgpa=8.0, gender="Male",
                      skills=["Python", "C++", "Embedded C"],
                      interests=["Robotics", "Software Engineering", "Artificial Intelligence"]),
        "ineligible_ids": ["OPP003", "OPP007", "OPP014"],
        "relevant_ids": ["OPP008", "OPP016", "OPP019", "OPP002"],
    },
]


# --------------------------------------------------------------------------- #
def _dcg(gains: Sequence[float]) -> float:
    return sum(g / math.log2(i + 2) for i, g in enumerate(gains))


def _ndcg_at_k(ranked_ids: List[str], relevant: set, k: int) -> float:
    gains = [1.0 if oid in relevant else 0.0 for oid in ranked_ids[:k]]
    ideal = [1.0] * min(len(relevant), k)
    idcg = _dcg(ideal)
    return (_dcg(gains) / idcg) if idcg > 0 else 0.0


def evaluate_profile(entry: Dict[str, Any], opps: List[Dict[str, Any]],
                     weights: Optional[Dict[str, float]] = None,
                     today: _dt.date = TODAY,
                     knowledge: Optional[Dict[str, Any]] = None,
                     k: int = 5) -> Dict[str, Any]:
    knowledge = knowledge or {}
    profile = entry["profile"]
    radar = R.build_radar(profile, opps, weights, today, True, knowledge=knowledge)

    labelled_ineligible = set(entry["ineligible_ids"])
    predicted_ineligible = {it["opportunity"]["id"] for it in radar["excluded"]
                            if it["eligibility"]["status"] == "Ineligible"}

    tp = len(labelled_ineligible & predicted_ineligible)
    fp = len(predicted_ineligible - labelled_ineligible)
    fn = len(labelled_ineligible - predicted_ineligible)
    accuracy = (tp + (len(opps) - len(labelled_ineligible | predicted_ineligible))) / len(opps)

    # Ranking: eligible items ordered by fit, the way the Radar presents them.
    ranked = sorted(
        [it for it in (radar["apply_now"] + radar["prepare_for"] + radar["explore"])],
        key=lambda x: -x["fit"])
    ranked_ids = [it["opportunity"]["id"] for it in ranked]
    relevant = set(entry["relevant_ids"])
    top_k = ranked_ids[:k]
    hits = [i for i in top_k if i in relevant]
    precision = len(hits) / k if k else 0.0
    recall = len(hits) / len(relevant) if relevant else 0.0

    all_ids = [o["id"] for o in opps]
    panes = radar["apply_now"] + radar["prepare_for"] + radar["explore"] + radar["excluded"]
    pane_ids = [it["opportunity"]["id"] for it in panes]
    partition_complete = len(pane_ids) == len(set(pane_ids)) == len(all_ids)

    return {
        "profile": entry["name"],
        "eligibility_accuracy": round(accuracy, 4),
        "ineligible_tp": tp, "ineligible_fp": fp, "ineligible_fn": fn,
        "precision_at_5": round(precision, 4),
        "recall_at_5": round(recall, 4),
        "ndcg_at_5": round(_ndcg_at_k(ranked_ids, relevant, k), 4),
        "coverage": round(len(set(pane_ids)) / len(all_ids), 4) if all_ids else 0.0,
        "partition_complete": partition_complete,
        "pane_sizes": {p: len(radar[p]) for p in ("apply_now", "prepare_for", "explore", "excluded")},
    }


def run_all(opps: Optional[List[Dict[str, Any]]] = None,
            knowledge: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    opps = opps if opps is not None else R.load_opportunities()
    knowledge = knowledge if knowledge is not None else R.load_knowledge()
    return [evaluate_profile(e, opps, R.DEFAULT_WEIGHTS, TODAY, knowledge) for e in EVAL_PROFILES]


if __name__ == "__main__":
    rows = run_all()
    hdr = f"{'profile':52}{'elig':>7}{'P@5':>7}{'R@5':>7}{'NDCG':>7}{'cover':>7}{'part':>6}"
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        print(f"{r['profile'][:50]:52}{r['eligibility_accuracy']:>7.2f}"
              f"{r['precision_at_5']:>7.2f}{r['recall_at_5']:>7.2f}"
              f"{r['ndcg_at_5']:>7.2f}{r['coverage']:>7.2f}{str(r['partition_complete']):>6}")
    avg_p = sum(r["precision_at_5"] for r in rows) / len(rows)
    avg_e = sum(r["eligibility_accuracy"] for r in rows) / len(rows)
    print(f"\nmean eligibility accuracy: {avg_e:.3f}   mean precision@5: {avg_p:.3f}")
