# OpportunityAI — 3-Minute Demo Script

**The one-line pitch:** *"OpportunityAI doesn't predict your future — it tells you what to do next."*

**Setup (before you present):**
```bash
cd opportunity-ai && pip install -r requirements.txt
export OPPORTUNITYAI_TODAY=2026-10-25     # freeze the demo so dates are stable
streamlit run app.py
```

**Backup plan:** the app needs **no network and no API key**. If Wi-Fi or Sarvam fails, everything still
works from the deterministic engine and templates — you lose only AI prose. Have the local URL open in a
second tab before you start. If a live resume upload is risky, have a PDF ready in a local folder.

---

**[0:00–0:20] The problem**

> "Students miss opportunities they were actually eligible for. And even when they find them, nobody
> tells them what to do first. OpportunityAI covers the whole loop — discovery, eligibility,
> preparation, application, tracking."

Show the hero and the metric strip (completeness, opportunities analysed, strong matches, tracked).

**[0:20–0:50] Demo Profile → Radar**

- Click **Try Demo Profile** — a second-year Chemical Engineering student, CGPA 8.2.
- Point at the three columns: **Apply Now (6) · Prepare For (5) · Explore (3)**.
- Open the top card: score ring, five component bars, eligibility badges.
- Say: *"The percentage is computed by the rule engine. The AI only explains it — it never invents it."*

**[0:50–1:15] Why Not? — the honesty panel**

- Switch to **Why Not?**.
- Show the merit scholarship at **90% fit** that is *excluded*: "requires 8.5; you have 8.2, short by
  0.3" — and the closed hackathon.
- Say: *"A closed deadline is not ineligibility, and an unverified field is never treated as a failure.
  Every exclusion shows the reason and what would help."*

**[1:15–1:55] Your Next Best Move — the centrepiece 🚀**

- Switch to **Next Move**.
- Read the hero card: *"**Learn Machine Learning** — asked for by 3 of your top 5 target opportunities;
  lifts your fit by +8 points on average; estimated effort 50 hours."*
- Point at the four metrics: **effort · fit gap · targets affected · evidence confidence**.
- Walk the **Pathway**: *You now → Learn it → Show it (train and compare 3 models) → Data Science & ML
  Intern 83%→91% → Data Analytics Intern 78%→84% → improved readiness.*
- Say: *"This is P = relevance × gap × confidence ÷ effort. The gains come from re-running the actual
  scoring function, not from a language model. And note the wording — improved readiness, not
  guaranteed selection."*
- Show the **Other actions, ranked** table to prove the ranking is mechanical.

**[1:55–2:25] Resume → Evidence Matrix**

- In the sidebar upload a PDF resume, tick **consent**.
- On **Copilot**, pick an opportunity, click **Build Evidence Matrix**.
- Show the three labels — **Demonstrated / Listed only / No evidence** — each with a verbatim quote.
- Say: *"Every quote is checked against the resume in code. A quote that isn't there is discarded, so
  the model cannot fabricate a bullet. Emails and phone numbers are redacted before anything is sent."*
- Click **Generate 7-Day Prep Kit** — checklist, interview topics labelled "typical, not confirmed by
  the organisation", day-by-day plan.

**[2:25–2:45] Tracker + Hindi**

- **Save to Tracker**, open **Tracker**, move the stage to *Applied* — stage history and funnel update.
  *"This persists across restarts."*
- Switch **Language → Hindi**: the interface translates; dynamic text goes through Sarvam `/translate`.

**[2:45–3:00] Close**

> "It runs with no API key, no database server and no network. It keeps eligibility, timing and fit as
> three separate facts, labels every unknown, and turns a match list into one prioritised action.
> Next: a verified data source instead of sample records."

---

**If asked**

- *Is the data real?* No — 21 labelled sample records with fictional organisations. No invented
  deadlines or links.
- *How is fit computed?* A configurable weighted sum, 35/25/20/10/10, with the breakdown on every card.
- *How do you know the engine works?* `evaluation.py` reports eligibility accuracy 1.00 and mean
  precision@5 0.76 over five labelled profiles, plus partition completeness.
- *What if the AI fails?* Every call is timeout-guarded with one retry, then a deterministic fallback.
- *Why is that 90%-fit scholarship excluded?* CGPA gate failed — and the fix is shown, not hidden.
- *Does the Next Move guarantee an internship?* No. It ranks actions by relevance, gap, confidence and
  effort, and says "improved readiness", not "guaranteed selection".
