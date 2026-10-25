"""
make_reference.py — generate the Python reference used by web/crosscheck.js.

Run from the project root, then run the Node cross-check:

    python3 web/make_reference.py     # writes web/py_ref.json from the Python engine
    cd web && node crosscheck.js      # exits non-zero on any JS/Python divergence

Keeping the two engines honest matters: the website must not quietly disagree with the
Streamlit app about a fit score or an eligibility verdict.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
sys.path.insert(0, PROJ)

import recommender as R  # noqa: E402

DEMO = {
    "name": "Aarav", "degree": "B.Tech", "branch": "Chemical Engineering", "year": 2, "cgpa": 8.2,
    "skills": ["Python", "Pandas", "Excel", "Thermodynamics", "Git", "SQL", "Data Visualization"],
    "interests": ["Data Science", "Machine Learning", "Chemical Engineering", "Research"],
    "work_mode": "Any", "location": "Any", "experience": "Beginner", "gender": "Prefer not to say",
}

RESUME = """Aarav Sharma
Email: aarav@example.com

Skills
Python, SQL, Excel, Git

Projects
Built a sales dashboard using Python and SQL that cut reporting time by half.
"""


def main() -> int:
    os.environ.setdefault("OPPORTUNITYAI_TODAY", "2026-10-25")
    opps = R.load_opportunities()
    K = R.load_knowledge()
    syn = K["skill_synonyms"]
    t = R.today()

    ref = {"fits": {}, "elig": {}, "timing": {}, "panes": {}, "actions": [], "evidence": []}
    for o in opps:
        ref["fits"][o["id"]] = R.score_opportunity(DEMO, o, R.DEFAULT_WEIGHTS, syn)["score_pct"]
        ref["elig"][o["id"]] = R.evaluate_eligibility(DEMO, o, t)["status"]
        ref["timing"][o["id"]] = R.timing_status(o, t, True)

    radar = R.build_radar(DEMO, opps, R.DEFAULT_WEIGHTS, t, True, knowledge=K)
    for pane in ("apply_now", "prepare_for", "explore", "excluded"):
        ref["panes"][pane] = [it["opportunity"]["id"] for it in radar[pane]]

    for a in R.action_priority(DEMO, opps, R.DEFAULT_WEIGHTS, t, K, True, 5):
        ref["actions"].append({"skill": a["skill"], "priority": a["priority"], "hours": a["hours"],
                               "gap": a["gap"], "lifted": a["opportunities_lifted"]})

    o1 = next(o for o in opps if o["id"] == "OPP001")
    for r in R.evidence_matrix(RESUME, o1, syn):
        ref["evidence"].append({"requirement": r["requirement"], "label": r["label"],
                                "section": r["section"]})

    out = os.path.join(HERE, "py_ref.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(ref, fh, indent=1)
    print(f"wrote {out}: {len(ref['fits'])} fits, {len(ref['actions'])} actions, "
          f"{len(ref['evidence'])} evidence rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
