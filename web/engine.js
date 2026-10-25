/*
 * engine.js — OpportunityAI engine, ported from recommender.py.
 *
 * Kept behaviourally identical to the Python implementation:
 *   eligibility gates · timing status · weighted fit · radar panes ·
 *   counterfactuals · ROI ("Next Best Move") · evidence matrix · prep kit.
 *
 * No AI is used here. Every number comes from the formulas below.
 */
(function (root) {
  "use strict";

  const DEFAULT_WEIGHTS = { skill: 0.35, interest: 0.25, academic: 0.20, workmode: 0.10, experience: 0.10 };

  const RADAR_THRESHOLDS = {
    apply_min_fit: 55.0,
    apply_min_coverage: 0.60,
    prepare_min_fit: 40.0,
    closing_soon_days: 7,
    explore_max: 5
  };

  const FUZZY_THRESHOLD = 92;
  const SYNONYM_CREDIT = 0.9;
  const SIMILAR_CREDIT = 0.7;
  const COUNTERFACTUAL_MIN_DELTA = 0.5;
  const QUOTE_MAX = 200;

  const EXPERIENCE_ORDER = { Beginner: 0, Intermediate: 1, Advanced: 2 };
  const VERIFICATION_WEIGHT = { verified: 1.0, fetched: 0.6, sample: 0.35, closed: 0.0 };

  const MASTER_SKILLS = [
    "Python", "Java", "C++", "JavaScript", "SQL", "R", "HTML/CSS",
    "React", "Node.js", "FastAPI", "Django", "Data Structures",
    "Machine Learning", "Deep Learning", "PyTorch", "TensorFlow",
    "scikit-learn", "Pandas", "NumPy", "NLP", "Computer Vision",
    "Data Visualization", "Process Engineering", "Process Simulation",
    "Aspen Plus", "MATLAB", "Thermodynamics", "Fluid Mechanics",
    "Heat Transfer", "Reaction Engineering", "Git", "Linux", "Docker",
    "Cloud (AWS)", "Excel", "Embedded C", "Verilog", "Communication",
    "Technical Writing"
  ];

  const INTEREST_OPTIONS = [
    "Artificial Intelligence", "Machine Learning", "Data Science",
    "Web Development", "Software Engineering", "Chemical Engineering",
    "Research", "Sustainability", "Energy", "Robotics", "Open Source",
    "Entrepreneurship", "Cybersecurity", "Biotechnology"
  ];

  const CATEGORY_ORDER = [
    "Software Engineering Internship", "Data Science / ML Internship",
    "Chemical Engineering Internship", "Research Internship", "Scholarship",
    "Hackathon", "Innovation Competition", "Open Source Program"
  ];

  const CATEGORY_BADGE = {
    "Software Engineering Internship": "b-blue",
    "Data Science / ML Internship": "b-violet",
    "Chemical Engineering Internship": "b-green",
    "Research Internship": "b-violet",
    "Scholarship": "b-amber",
    "Hackathon": "b-blue",
    "Innovation Competition": "b-green",
    "Open Source Program": "b-grey"
  };

  /* ------------------------------------------------------------------ */
  /* Text / skill normalisation                                          */
  /* ------------------------------------------------------------------ */
  function norm(v) { return v === null || v === undefined ? "" : String(v).trim().toLowerCase(); }

  function normSkill(v) {
    return norm(v).replace(/[^a-z0-9+#./ ]/g, " ").replace(/\s+/g, " ").trim();
  }

  const CANON = {};
  MASTER_SKILLS.forEach(function (s) { CANON[normSkill(s)] = s; });

  function synonymCanon(synonyms) {
    const out = {};
    Object.keys(synonyms || {}).forEach(function (k) { out[normSkill(k)] = normSkill(synonyms[k]); });
    return out;
  }

  function canonicalSkill(value, synonyms) {
    const key = normSkill(value);
    if (CANON[key]) return CANON[key];
    if (synonyms) {
      const mapped = synonyms[key] || synonyms[norm(value)];
      if (mapped) {
        const mk = normSkill(mapped);
        return CANON[mk] || mapped;
      }
    }
    return String(value).trim();
  }

  /* Levenshtein-based ratio, matching rapidfuzz's fuzz.ratio semantics. */
  function levDistance(a, b) {
    a = a || ""; b = b || "";
    const m = a.length, n = b.length;
    if (!m) return n;
    if (!n) return m;
    let prev = new Array(n + 1), cur = new Array(n + 1);
    for (let j = 0; j <= n; j++) prev[j] = j;
    for (let i = 1; i <= m; i++) {
      cur[0] = i;
      for (let j = 1; j <= n; j++) {
        const cost = a[i - 1] === b[j - 1] ? 0 : 1;
        cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost);
      }
      const t = prev; prev = cur; cur = t;
    }
    return prev[n];
  }

  /* Longest common subsequence — the basis of difflib/rapidfuzz's ratio. */
  function lcsLength(a, b) {
    const m = a.length, n = b.length;
    if (!m || !n) return 0;
    let prev = new Array(n + 1).fill(0), cur = new Array(n + 1).fill(0);
    for (let i = 1; i <= m; i++) {
      cur[0] = 0;
      for (let j = 1; j <= n; j++) {
        cur[j] = a[i - 1] === b[j - 1] ? prev[j - 1] + 1 : Math.max(prev[j], cur[j - 1]);
      }
      const t = prev; prev = cur; cur = t;
    }
    return prev[n];
  }

  /* Matches rapidfuzz fuzz.ratio: 100 * 2*M / (len(a)+len(b)). */
  function levRatio(a, b) {
    a = a || ""; b = b || "";
    if (!a.length && !b.length) return 100;
    const m = lcsLength(a, b);
    return (200 * m) / (a.length + b.length);
  }

  function tokenize(s) { return normSkill(s).split(" ").filter(Boolean); }

  /* rapidfuzz token_set_ratio: max of the three canonical set combinations. */
  function tokenSetRatio(a, b) {
    const ta = Array.from(new Set(tokenize(a))).sort();
    const tb = Array.from(new Set(tokenize(b))).sort();
    const inter = ta.filter(function (x) { return tb.indexOf(x) >= 0; });
    const restA = ta.filter(function (x) { return inter.indexOf(x) < 0; });
    const restB = tb.filter(function (x) { return inter.indexOf(x) < 0; });
    const t0 = inter.join(" ");
    const t1 = inter.concat(restA).join(" ");
    const t2 = inter.concat(restB).join(" ");
    return Math.max(levRatio(t0, t1), levRatio(t0, t2), levRatio(t1, t2));
  }

  /* Best credit one target skill gets from the student's skills. */
  function skillCredit(studentSkills, target, synonyms) {
    const t = normSkill(target);
    const syn = synonymCanon(synonyms);
    const tCanon = syn[t] || t;
    let best = 0.0, via = null;
    const list = studentSkills || [];
    for (let i = 0; i < list.length; i++) {
      const s = normSkill(list[i]);
      if (!s) continue;
      if (s === t) return { credit: 1.0, via: "exact" };
      const sCanon = syn[s] || s;
      if (sCanon === tCanon && s !== t) {
        if (SYNONYM_CREDIT > best) { best = SYNONYM_CREDIT; via = "synonym"; }
        continue;
      }
      if (tokenSetRatio(s, t) >= FUZZY_THRESHOLD) {
        if (SIMILAR_CREDIT > best) { best = SIMILAR_CREDIT; via = "similar"; }
      }
    }
    return { credit: best, via: via };
  }

  function canonList(values, synonyms) {
    const out = {};
    (values || []).forEach(function (v) { if (norm(v)) out[canonicalSkill(v, synonyms)] = true; });
    return Object.keys(out).sort();
  }

  function parseCgpa(raw) {
    if (raw === null || raw === undefined) return null;
    const text = String(raw).trim();
    if (text === "") return null;
    const value = Number(text);
    if (!isFinite(value)) throw new Error("CGPA must be a number between 0 and 10.");
    if (value < 0 || value > 10) throw new Error("CGPA must be between 0 and 10.");
    return value;
  }

  /* ------------------------------------------------------------------ */
  /* Time                                                               */
  /* ------------------------------------------------------------------ */
  function today() {
    if (root && root.OPP_TODAY) return asDate(root.OPP_TODAY);
    const d = new Date();
    return new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  }

  function isoDate(v) { return typeof v === "string" && v.trim() ? v : null; }

  function asDate(v) {
    if (!v) return null;
    const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(v));
    if (!m) return null;
    return new Date(Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3])));
  }

  function daysBetween(a, b) { return Math.round((b.getTime() - a.getTime()) / 86400000); }

  function isoOf(d) { return d.toISOString().slice(0, 10); }

  /* ------------------------------------------------------------------ */
  /* Stage 1 — eligibility gates (skills are never gates)               */
  /* ------------------------------------------------------------------ */
  function gateDegree(profile, opp) {
    const allowed = opp.eligible_degrees;
    if (!allowed || !allowed.length) return { gate: "Degree", status: "pass", detail: "No degree restriction stated." };
    if (allowed.map(norm).indexOf("any") >= 0) return { gate: "Degree", status: "pass", detail: "Open to any degree." };
    if (allowed.map(norm).indexOf(norm(profile.degree)) >= 0) return { gate: "Degree", status: "pass", detail: profile.degree + " is listed." };
    return { gate: "Degree", status: "fail", detail: "Requires " + allowed.join("/") + "; you are " + (profile.degree || "unspecified") + "." };
  }

  function gateBranch(profile, opp) {
    const allowed = opp.eligible_branches;
    if (!allowed || !allowed.length) return { gate: "Branch", status: "pass", detail: "No branch restriction stated." };
    const pb = norm(profile.branch);
    for (let i = 0; i < allowed.length; i++) {
      const na = norm(allowed[i]);
      if (na === "any" || (pb && (pb.indexOf(na) >= 0 || na.indexOf(pb) >= 0))) {
        return { gate: "Branch", status: "pass", detail: "Your branch matches '" + allowed[i] + "'." };
      }
    }
    return { gate: "Branch", status: "fail", detail: "Restricted to " + allowed.join("/") + "; you are " + (profile.branch || "unspecified") + "." };
  }

  function gateYear(profile, opp) {
    const years = opp.eligible_years;
    if (!years || !years.length) return { gate: "Year", status: "unknown", detail: "No preferred year stated." };
    if (years.indexOf(profile.year) >= 0) return { gate: "Year", status: "pass", detail: "Year " + profile.year + " is accepted." };
    return { gate: "Year", status: "fail", detail: "Open to year(s) " + years.join(", ") + "; you are year " + profile.year + "." };
  }

  function gateCgpa(profile, opp) {
    const min = opp.min_cgpa, cgpa = profile.cgpa;
    if (min === null || min === undefined) return { gate: "CGPA", status: "unknown", detail: "No minimum CGPA stated." };
    if (cgpa === null || cgpa === undefined) return { gate: "CGPA", status: "unknown", detail: "Requires " + min + "; your CGPA is not provided." };
    if (cgpa >= min) return { gate: "CGPA", status: "pass", detail: "Requires " + min + "; you have " + cgpa + "." };
    return { gate: "CGPA", status: "fail", detail: "Requires " + min + "; you have " + cgpa + " (short by " + (Math.round((min - cgpa) * 100) / 100) + ")." };
  }

  function gateWomen(profile, opp) {
    if (!opp.women_only) return null;
    const g = norm(profile.gender);
    if (g === "female") return { gate: "Women only", status: "pass", detail: "Restricted to women; you qualify." };
    if (g === "male") return { gate: "Women only", status: "fail", detail: "Restricted to women applicants." };
    return { gate: "Women only", status: "unknown", detail: "Restricted to women; your gender is not specified in the profile." };
  }

  function evaluateEligibility(profile, opp, t) {
    const gates = [gateDegree(profile, opp), gateBranch(profile, opp), gateYear(profile, opp), gateCgpa(profile, opp)];
    const wg = gateWomen(profile, opp);
    if (wg) gates.push(wg);
    let status;
    if (gates.some(function (g) { return g.status === "fail"; })) status = "Ineligible";
    else if (gates.some(function (g) { return g.status === "unknown"; })) status = "Potentially Eligible";
    else status = "Eligible";
    const verify = gates.filter(function (g) { return g.status === "unknown"; })
      .map(function (g) { return g.gate + ": " + g.detail; });
    return { status: status, gates: gates, verify: verify };
  }

  /* ------------------------------------------------------------------ */
  /* Stage 2 — timing (separate from eligibility)                        */
  /* ------------------------------------------------------------------ */
  function resolveDeadline(opp, t, demoMode) {
    if (isoDate(opp.deadline)) return opp.deadline;
    const off = opp.demo_deadline_offset_days;
    if (demoMode && off !== null && off !== undefined && opp.verification_status === "sample") {
      return isoOf(new Date(t.getTime() + Number(off) * 86400000));
    }
    return null;
  }

  function timingStatus(opp, t, demoMode) {
    if (norm(opp.verification_status) === "closed") return "closed";
    if (norm(opp.deadline_kind) === "rolling") return "rolling";
    const opens = asDate(isoDate(opp.opens_on));
    if (opens && opens.getTime() > t.getTime()) return "not_yet_open";
    const dl = asDate(resolveDeadline(opp, t, demoMode));
    if (dl) {
      if (dl.getTime() < t.getTime()) return "closed";
      if (daysBetween(t, dl) <= RADAR_THRESHOLDS.closing_soon_days) return "closing_soon";
      return "open";
    }
    return "unknown";
  }

  /* ------------------------------------------------------------------ */
  /* Stage 3 — fit                                                      */
  /* ------------------------------------------------------------------ */
  function skillComponent(profile, opp, synonyms) {
    const student = profile.skills || [];
    const required = opp.required_skills || [];
    const preferred = opp.preferred_skills || [];
    const matched = [], reqCredits = [], prefCredits = [];

    required.forEach(function (s) {
      const r = skillCredit(student, s, synonyms);
      reqCredits.push(r.credit);
      if (r.credit > 0) matched.push({ skill: canonicalSkill(s, synonyms), via: r.via || "exact" });
    });
    preferred.forEach(function (s) {
      const r = skillCredit(student, s, synonyms);
      prefCredits.push(r.credit);
      if (r.credit > 0) matched.push({ skill: canonicalSkill(s, synonyms), via: r.via || "exact" });
    });

    const reqCov = reqCredits.length ? reqCredits.reduce(function (a, b) { return a + b; }, 0) / reqCredits.length : 1.0;
    const num = 2.0 * reqCredits.reduce(function (a, b) { return a + b; }, 0) + prefCredits.reduce(function (a, b) { return a + b; }, 0);
    const den = 2.0 * reqCredits.length + prefCredits.length;
    const coverage = den ? num / den : 0.6;

    const missing = canonList(required.filter(function (s, i) { return reqCredits[i] === 0.0; }), synonyms);
    const seen = {}, dedup = [];
    matched.forEach(function (m) { if (!seen[m.skill]) { seen[m.skill] = 1; dedup.push(m); } });

    return { score: Math.round(coverage * 10000) / 10000, required_coverage: Math.round(reqCov * 10000) / 10000, matched: dedup, missing: missing };
  }

  function interestComponent(profile, opp) {
    const mine = (profile.interests || []).map(norm).filter(Boolean);
    const theirs = (opp.interests || []).map(norm).filter(Boolean);
    if (!mine.length || !theirs.length) return 0.5;
    const overlap = theirs.filter(function (x) { return mine.indexOf(x) >= 0; }).length;
    return Math.round(Math.min(1.0, overlap / Math.min(3, theirs.length)) * 10000) / 10000;
  }

  function academicComponent(profile, opp) {
    const min = opp.min_cgpa, cgpa = profile.cgpa;
    const unconfirmed = [];
    if (min === null || min === undefined || cgpa === null || cgpa === undefined) {
      unconfirmed.push("Minimum CGPA could not be checked (not stated, or not provided).");
      return { score: 0.5, unconfirmed: unconfirmed };
    }
    const parts = [];
    const years = opp.eligible_years;
    parts.push(!years || !years.length || years.indexOf(profile.year) >= 0 ? 1.0 : 0.4);
    parts.push(cgpa >= min ? 1.0 : 0.0);
    const degrees = opp.eligible_degrees;
    if (!degrees || !degrees.length || degrees.map(norm).indexOf("any") >= 0) parts.push(1.0);
    else parts.push(degrees.map(norm).indexOf(norm(profile.degree)) >= 0 ? 1.0 : 0.4);
    const mean = parts.reduce(function (a, b) { return a + b; }, 0) / parts.length;
    return { score: Math.round(mean * 10000) / 10000, unconfirmed: unconfirmed };
  }

  function workmodeComponent(profile, opp) {
    const pref = norm(profile.work_mode), mode = norm(opp.work_mode);
    let modePart;
    if (!pref || pref === "any" || pref === mode) modePart = 1.0;
    else if (pref.indexOf(mode) >= 0 || mode.indexOf(pref) >= 0) modePart = 0.8;
    else modePart = 0.2;
    const pl = norm(profile.location), ol = norm(opp.location);
    const locPart = (!pl || pl === "any" || !ol || pl.indexOf(ol) >= 0 || ol.indexOf(pl) >= 0) ? 1.0 : 0.6;
    return Math.round((0.7 * modePart + 0.3 * locPart) * 10000) / 10000;
  }

  function experienceComponent(profile, opp) {
    const student = EXPERIENCE_ORDER[profile.experience] !== undefined ? EXPERIENCE_ORDER[profile.experience] : 1;
    const required = EXPERIENCE_ORDER[opp.experience_level || "Intermediate"] !== undefined ? EXPERIENCE_ORDER[opp.experience_level || "Intermediate"] : 1;
    const gap = required - student;
    return gap <= 0 ? 1.0 : (gap === 1 ? 0.5 : 0.2);
  }

  function scoreOpportunity(profile, opp, weights, synonyms, t) {
    weights = weights || DEFAULT_WEIGHTS;
    synonyms = synonyms || {};
    const totalWeight = Object.keys(weights).reduce(function (a, k) { return a + weights[k]; }, 0) || 1.0;

    const sk = skillComponent(profile, opp, synonyms);
    const interest = interestComponent(profile, opp);
    const ac = academicComponent(profile, opp);
    const wm = workmodeComponent(profile, opp);
    const ex = experienceComponent(profile, opp);

    const components = { skill: sk.score, interest: interest, academic: ac.score, workmode: wm, experience: ex };
    let total = 0;
    Object.keys(components).forEach(function (k) { total += components[k] * (weights[k] || 0); });
    total = total / totalWeight;

    const unconfirmed = ac.unconfirmed.slice();
    if (!opp.verified && opp.verification_status === "sample") {
      unconfirmed.push("Sample record — verify eligibility and dates on the official site.");
    }
    if (!resolveDeadline(opp, t || today(), true) && opp.deadline_kind !== "rolling") {
      unconfirmed.push("No deadline available to check.");
    }

    const pct = {};
    Object.keys(components).forEach(function (k) { pct[k] = Math.round(components[k] * 1000) / 10; });

    return {
      opportunity: opp,
      total: Math.round(total * 10000) / 10000,
      score_pct: Math.round(total * 1000) / 10,
      components: pct,
      required_coverage: sk.required_coverage,
      matched: sk.matched,
      missing: sk.missing,
      unconfirmed: unconfirmed,
      matched_skills: sk.matched.map(function (m) { return m.skill; }),
      missing_required: sk.missing
    };
  }

  /* ------------------------------------------------------------------ */
  /* Stage 4 — counterfactuals                                          */
  /* ------------------------------------------------------------------ */
  function counterfactuals(profile, opp, weights, synonyms, maxN) {
    synonyms = synonyms || {};
    maxN = maxN || 3;
    const base = scoreOpportunity(profile, opp, weights, synonyms).score_pct;
    const out = [];
    (opp.required_skills || []).forEach(function (skill) {
      if (skillCredit(profile.skills || [], skill, synonyms).credit > 0) return;
      const trial = Object.assign({}, profile, { skills: (profile.skills || []).concat([skill]) });
      const after = scoreOpportunity(trial, opp, weights, synonyms).score_pct;
      const delta = Math.round((after - base) * 10) / 10;
      if (delta >= COUNTERFACTUAL_MIN_DELTA) {
        out.push({ skill: canonicalSkill(skill, synonyms), before_pct: base, after_pct: after, delta: delta });
      }
    });
    out.sort(function (a, b) { return b.delta - a.delta; });
    return out.slice(0, maxN);
  }

  function topSkillGains(profile, opps, weights, t, synonyms, demoMode) {
    synonyms = synonyms || {};
    const pool = opps.filter(function (o) {
      return evaluateEligibility(profile, o, t).status !== "Ineligible" && timingStatus(o, t, demoMode !== false) !== "closed";
    });
    pool.sort(function (a, b) { return scoreOpportunity(profile, b, weights, synonyms).score_pct - scoreOpportunity(profile, a, weights, synonyms).score_pct; });
    const agg = {};
    pool.slice(0, 10).forEach(function (o) {
      counterfactuals(profile, o, weights, synonyms, 99).forEach(function (c) {
        (agg[c.skill] = agg[c.skill] || []).push(c.delta);
      });
    });
    const out = Object.keys(agg).map(function (s) {
      const d = agg[s];
      const avg = d.reduce(function (a, b) { return a + b; }, 0) / d.length;
      return { skill: s, opportunities_lifted: d.length, avg_gain: Math.round(avg * 10) / 10 };
    });
    out.sort(function (a, b) { return (b.avg_gain - a.avg_gain) || (b.opportunities_lifted - a.opportunities_lifted); });
    return out;
  }

  /* ------------------------------------------------------------------ */
  /* Opportunity Radar                                                  */
  /* ------------------------------------------------------------------ */
  function exclusionReason(elig, timing) {
    if (elig.status === "Ineligible") {
      const fails = elig.gates.filter(function (g) { return g.status === "fail"; });
      const reason = fails.length ? fails[0].detail : "Does not meet a stated requirement.";
      const fixes = {
        "CGPA": "Improve your CGPA, or look for a similar role with a lower cutoff.",
        "Year": "Revisit this in a later year of study.",
        "Degree": "Look for an opportunity open to your degree.",
        "Branch": "Look for an opportunity open to your branch.",
        "Women only": "This programme is restricted to women applicants."
      };
      return [reason, fails.length ? (fixes[fails[0].gate] || "Check whether an exception applies.") : ""];
    }
    if (timing === "closed") {
      return ["Applications are closed for this listing.", "Look for the next intake, or a similar currently-open opportunity."];
    }
    return null;
  }

  function bridgeFor(opp, branchBridges) {
    const tags = (opp.interests || []).map(norm);
    for (let i = 0; i < (branchBridges || []).length; i++) {
      const b = branchBridges[i];
      const area = norm(b.area);
      if (!area) continue;
      if (tags.some(function (t) { return area.indexOf(t) >= 0 || t.indexOf(area) >= 0; })) return b;
    }
    return null;
  }

  function nextActionFor(profile, opp, sc, knowledge) {
    const playbook = (knowledge || {}).skill_playbook || {};
    const missing = sc.missing || [];
    if (missing.length) {
      const skill = missing[0];
      const entry = playbook[norm(skill)] || playbook._generic || {};
      return "Build the missing skill '" + skill + "': " + (entry.project || "start a small project using it.");
    }
    if (sc.required_coverage >= RADAR_THRESHOLDS.apply_min_coverage) {
      return "You already cover the required skills — polish your CV and apply.";
    }
    return "Strengthen your profile with one portfolio project in this area.";
  }

  function buildRadar(profile, opps, weights, t, demoMode, knowledge) {
    weights = weights || DEFAULT_WEIGHTS;
    t = t || today();
    knowledge = knowledge || {};
    const synonyms = knowledge.skill_synonyms || {};
    const bridges = knowledge.domain_bridges || {};
    const branchBridges = bridges[norm(profile.branch)] || [];

    const panes = { apply_now: [], prepare_for: [], explore: [], excluded: [] };

    opps.forEach(function (opp) {
      const elig = evaluateEligibility(profile, opp, t);
      const timing = timingStatus(opp, t, demoMode);
      const sc = scoreOpportunity(profile, opp, weights, synonyms, t);
      const fit = sc.score_pct;
      const cov = sc.required_coverage;

      const reason = exclusionReason(elig, timing);
      if (reason) {
        panes.excluded.push({
          opportunity: opp, eligibility: elig, timing: timing, score: sc, fit: fit,
          required_coverage: cov, deadline: resolveDeadline(opp, t, demoMode),
          reason: reason[0], fix: reason[1]
        });
        return;
      }

      const deadline = resolveDeadline(opp, t, demoMode);
      const hasSignal = !!deadline || norm(opp.deadline_kind) === "rolling";
      const eligibleish = elig.status === "Eligible" || elig.status === "Potentially Eligible";
      const openish = timing === "open" || timing === "closing_soon" || timing === "rolling";

      const item = {
        opportunity: opp, eligibility: elig, timing: timing, score: sc, fit: fit,
        required_coverage: cov, deadline: deadline
      };

      if (eligibleish && openish && hasSignal && cov >= RADAR_THRESHOLDS.apply_min_coverage && fit >= RADAR_THRESHOLDS.apply_min_fit) {
        item.next_action = "Apply now — check the official listing for the current dates.";
        panes.apply_now.push(item);
        return;
      }
      if (eligibleish && fit >= RADAR_THRESHOLDS.prepare_min_fit &&
          (cov < RADAR_THRESHOLDS.apply_min_coverage || timing === "not_yet_open" || timing === "unknown")) {
        item.next_action = nextActionFor(profile, opp, sc, knowledge);
        panes.prepare_for.push(item);
        return;
      }
      item.bridge = bridgeFor(opp, branchBridges);
      item.next_action = nextActionFor(profile, opp, sc, knowledge);
      panes.explore.push(item);
    });

    function sortPane(items) {
      return items.sort(function (a, b) {
        if (b.fit !== a.fit) return b.fit - a.fit;
        const da = a.deadline || "9999-12-31", db = b.deadline || "9999-12-31";
        if (da !== db) return da < db ? -1 : 1;
        return a.opportunity.id < b.opportunity.id ? -1 : 1;
      });
    }
    panes.apply_now = sortPane(panes.apply_now);
    panes.prepare_for = sortPane(panes.prepare_for);
    panes.explore = sortPane(panes.explore);
    panes.excluded.sort(function (a, b) { return a.opportunity.id < b.opportunity.id ? -1 : 1; });
    return panes;
  }

  /* ------------------------------------------------------------------ */
  /* Information quality — never mixed with fit                          */
  /* ------------------------------------------------------------------ */
  function informationCompleteness(opp) {
    const present = {
      source: !!opp.source_url,
      deadline: !!opp.deadline || norm(opp.deadline_kind) === "rolling",
      eligibility: !!(opp.eligibility && opp.eligibility.length),
      apply_url: !!opp.apply_url
    };
    const keys = Object.keys(present);
    const n = keys.filter(function (k) { return present[k]; }).length;
    const status = opp.verification_status || "sample";
    return {
      fields: present, present_count: n, total: keys.length,
      completeness_pct: Math.round(100 * n / keys.length),
      verification_status: status, human_verified: status === "verified",
      last_verified: opp.last_verified, label: "Information completeness",
      note: "Measures how much of this record is actually stated, and whether a human has checked it. It is NOT a guarantee of legitimacy and is NOT part of your fit score."
    };
  }

  /* ------------------------------------------------------------------ */
  /* ROI engine — Your Next Best Move                                    */
  /* ------------------------------------------------------------------ */
  function maxnorm(values) {
    const hi = values.length ? Math.max.apply(null, values) : 0;
    if (hi <= 1e-9) return values.map(function () { return 1.0; });
    return values.map(function (v) { return v / hi; });
  }

  function targetOpportunities(profile, opps, weights, t, synonyms, n, demoMode) {
    const scored = [];
    opps.forEach(function (o) {
      const st = evaluateEligibility(profile, o, t).status;
      if (st === "Ineligible") return;
      if (timingStatus(o, t, demoMode !== false) === "closed") return;
      scored.push([st === "Eligible" ? 0 : 1, -scoreOpportunity(profile, o, weights, synonyms).score_pct, o.id, o]);
    });
    scored.sort(function (a, b) { return (a[0] - b[0]) || (a[1] - b[1]) || (a[2] < b[2] ? -1 : 1); });
    return scored.slice(0, n).map(function (s) { return s[3]; });
  }

  function actionPriority(profile, opps, weights, t, knowledge, demoMode, targetN) {
    knowledge = knowledge || {};
    const synonyms = knowledge.skill_synonyms || {};
    const playbook = knowledge.skill_playbook || {};
    weights = weights || DEFAULT_WEIGHTS;
    t = t || today();
    targetN = targetN || 5;

    const targets = targetOpportunities(profile, opps, weights, t, synonyms, targetN, demoMode);
    if (!targets.length) return [];

    const cand = {};
    targets.forEach(function (opp) {
      const base = scoreOpportunity(profile, opp, weights, synonyms).score_pct;
      const eligStatus = evaluateEligibility(profile, opp, t).status;
      (opp.required_skills || []).forEach(function (skill) {
        if (skillCredit(profile.skills || [], skill, synonyms).credit > 0) return;
        const trial = Object.assign({}, profile, { skills: (profile.skills || []).concat([skill]) });
        const after = scoreOpportunity(trial, opp, weights, synonyms).score_pct;
        const gain = after - base;
        if (gain < COUNTERFACTUAL_MIN_DELTA) return;
        const canon = canonicalSkill(skill, synonyms);
        const e = cand[canon] || (cand[canon] = { skill: canon, targets: [], gains: [], conf: [], eligWeights: [] });
        e.targets.push({ id: opp.id, title: opp.title, before: base, after: after, eligibility: eligStatus });
        e.gains.push(gain);
        e.conf.push(VERIFICATION_WEIGHT[opp.verification_status] !== undefined ? VERIFICATION_WEIGHT[opp.verification_status] : 0.35);
        e.eligWeights.push(eligStatus === "Eligible" ? 1.0 : 0.6);
      });
    });

    const items = Object.keys(cand).map(function (k) { return cand[k]; });
    if (!items.length) return [];

    const rRaw = items.map(function (it) {
      let s = 0;
      it.targets.forEach(function (tt, i) { s += tt.before * it.eligWeights[i]; });
      return s / 100.0;
    });
    const gRaw = items.map(function (it) { return it.gains.reduce(function (a, b) { return a + b; }, 0) / it.gains.length; });
    const cRaw = items.map(function (it) { return it.conf.reduce(function (a, b) { return a + b; }, 0) / it.conf.length; });
    const hours = items.map(function (it) {
      const entry = playbook[norm(it.skill)] || playbook._generic || {};
      return Number(entry.hours !== undefined ? entry.hours : 16);
    });

    const rN = maxnorm(rRaw), gN = maxnorm(gRaw), cN = maxnorm(cRaw);
    const tMax = Math.max.apply(null, hours) || 1.0;

    items.forEach(function (it, i) {
      const tN = Math.max(0.05, hours[i] / tMax);
      it.relevance = Math.round(rRaw[i] * 1000) / 1000;
      it.needs_verification = it.targets.some(function (tt) { return tt.eligibility === "Potentially Eligible"; });
      it.gap = Math.round(gRaw[i] * 100) / 100;
      it.confidence = Math.round(cRaw[i] * 100) / 100;
      it.hours = Math.round(hours[i]);
      it.opportunities_lifted = it.targets.length;
      it.priority = Math.round(((rN[i] * gN[i] * cN[i]) / tN) * 10000) / 10000;
      const entry = playbook[norm(it.skill)] || playbook._generic || {};
      it.project = entry.project || "Start a small project that uses it end to end.";
      it.task = entry.task || "Spend focused sessions on the basics.";
      it.resource_type = entry.resource_type || "Official documentation.";
      const caveat = it.needs_verification ? " One of these still needs its eligibility confirmed — check that first." : "";
      it.why = it.skill + " is asked for by " + it.targets.length + " of your top " + targets.length +
        " target opportunities. Learning it lifts your fit by an average of +" + it.gap.toFixed(1) +
        " points on " + it.opportunities_lifted + " of them. Estimated effort: " + it.hours + " hours (estimate)." + caveat;
    });

    items.sort(function (a, b) {
      return (b.priority - a.priority) || (b.gap - a.gap) || (a.hours - b.hours) || (a.skill < b.skill ? -1 : 1);
    });
    return items;
  }

  function nextBestMove(profile, opps, weights, t, knowledge, demoMode, targetN) {
    const acts = actionPriority(profile, opps, weights, t, knowledge, demoMode, targetN);
    return acts.length ? acts[0] : null;
  }

  function pathway(action) {
    const steps = [
      { stage: "You now", detail: action.skill + " is not yet on your profile." },
      { stage: "Learn " + action.skill, detail: action.task + " (~" + action.hours + " hours)." },
      { stage: "Show it", detail: action.project }
    ];
    action.targets.slice(0, 3).forEach(function (t) {
      steps.push({
        stage: t.title,
        detail: "Fit moves " + Math.round(t.before) + "% → " + Math.round(t.after) + "% (+" + (Math.round((t.after - t.before) * 10) / 10) + " pts)."
      });
    });
    steps.push({ stage: "Improved readiness", detail: "A stronger profile for the roles you are already targeting." });
    return steps;
  }

  /* ------------------------------------------------------------------ */
  /* Why isn't this in Apply Now?                                        */
  /* ------------------------------------------------------------------ */
  function whyNotApplyNow(item) {
    const reasons = [];
    const elig = item.eligibility || {}, timing = item.timing, cov = item.required_coverage || 0, fit = item.fit || 0;
    const thr = RADAR_THRESHOLDS;

    if (elig.status === "Potentially Eligible") {
      reasons.push({ check: "Eligibility", status: "Potentially eligible",
        detail: "Not a failure — these still need confirming: " + (elig.verify || []).slice(0, 2).join("; "),
        action: "Verify the listed fields on the official page." });
    } else {
      reasons.push({ check: "Eligibility", status: elig.status || "unknown", detail: "All stated gates passed.", action: "No action needed." });
    }

    if (timing === "unknown" || timing === "not_yet_open") {
      reasons.push({ check: "Timing", status: timing === "unknown" ? "Window not verified" : "Opens later",
        detail: "No verified open application window, so it cannot sit in Apply Now.",
        action: "Check the official page for the current window." });
    } else if (timing === "closed") {
      reasons.push({ check: "Timing", status: "Closed", detail: "The deadline has passed.", action: "Look for the next intake." });
    } else {
      reasons.push({ check: "Timing", status: timing.replace(/_/g, " ").replace(/\b\w/g, function (c) { return c.toUpperCase(); }),
        detail: "There is a live window.", action: "Apply once the other checks pass." });
    }

    reasons.push({
      check: "Required-skill coverage",
      status: Math.round(cov * 100) + "% (needs " + Math.round(thr.apply_min_coverage * 100) + "%)",
      detail: cov < thr.apply_min_coverage ? "You do not yet cover enough of the listed required skills." : "You cover enough of the required skills.",
      action: cov < thr.apply_min_coverage ? "See the Next Move tab for the highest-value skill to add." : "No action needed."
    });
    reasons.push({
      check: "Overall fit",
      status: Math.round(fit) + "% (needs " + Math.round(thr.apply_min_fit) + "%)",
      detail: fit < thr.apply_min_fit ? "Below the Apply Now threshold." : "Above the Apply Now threshold.",
      action: fit < thr.apply_min_fit ? "Raise your fit by closing skill gaps." : "No action needed."
    });
    return reasons;
  }

  /* ------------------------------------------------------------------ */
  /* Resume → Evidence Matrix                                            */
  /* ------------------------------------------------------------------ */
  const SECTION_HEADINGS = {
    skills: ["skills", "technical skills", "technologies", "tech stack"],
    projects: ["projects", "personal projects", "academic projects"],
    experience: ["experience", "work experience", "internship", "internships", "employment"],
    education: ["education", "academics"]
  };

  function splitSentences(text) {
    if (!text) return [];
    const parts = [];
    text.split("\n").forEach(function (line) {
      line = line.trim();
      if (!line) return;
      line.split(/(?<=[.!?;])\s+/).forEach(function (chunk) {
        chunk = chunk.trim();
        if (chunk) parts.push(chunk);
      });
    });
    return parts;
  }

  function sectionOf(line) {
    const low = norm(line).replace(/:$/, "");
    const keys = Object.keys(SECTION_HEADINGS);
    for (let i = 0; i < keys.length; i++) {
      const section = keys[i];
      const list = SECTION_HEADINGS[section];
      for (let j = 0; j < list.length; j++) {
        const k = list[j];
        if (low === k || low.indexOf(k + ":") === 0 || (low.length < 30 && low.indexOf(k) >= 0)) return section;
      }
    }
    return null;
  }

  function evidenceMatrix(resumeText, opp, synonyms) {
    synonyms = synonyms || {};
    const rows = [];
    const sentences = splitSentences(resumeText || "");
    const sectionFor = {};
    let current = "Other";
    (resumeText || "").split("\n").forEach(function (line) {
      const s = sectionOf(line);
      if (s) current = s;
      sectionFor[line.trim()] = current;
    });
    const syn = synonymCanon(synonyms);

    (opp.required_skills || []).forEach(function (req) {
      const canon = canonicalSkill(req, synonyms);
      const candidates = {};
      candidates[normSkill(req)] = 1;
      candidates[normSkill(canon)] = 1;
      if (syn[normSkill(req)]) candidates[syn[normSkill(req)]] = 1;
      Object.keys(syn).forEach(function (k) { if (syn[k] === normSkill(canon)) candidates[k] = 1; });

      let quote = null, section = "Other";
      for (let i = 0; i < sentences.length && !quote; i++) {
        const ns = normSkill(sentences[i]);
        const keys = Object.keys(candidates).filter(Boolean);
        for (let j = 0; j < keys.length; j++) {
          const re = new RegExp("(?<![a-z0-9])" + keys[j].replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "(?![a-z0-9])");
          if (re.test(ns)) {
            quote = sentences[i].slice(0, QUOTE_MAX);
            const lineKeys = Object.keys(sectionFor);
            for (let k = 0; k < lineKeys.length; k++) {
              if (lineKeys[k].indexOf(sentences[i]) >= 0) { section = sectionFor[lineKeys[k]]; break; }
            }
            break;
          }
        }
      }

      let label;
      if (!quote) label = "No evidence";
      else if (section === "projects" || section === "experience") label = "Demonstrated";
      else label = "Listed only";

      rows.push({
        requirement: canon, label: label, quote: quote,
        section: (section || "Other").replace(/\b\w/g, function (c) { return c.toUpperCase(); })
      });
    });
    return rows;
  }

  function validateQuote(quote, resumeText) {
    if (!quote) return false;
    if ((resumeText || "").indexOf(quote) >= 0) return true;
    const nq = quote.replace(/\s+/g, " ").trim().toLowerCase();
    const nr = (resumeText || "").replace(/\s+/g, " ").trim().toLowerCase();
    return !!nq && nr.indexOf(nq) >= 0;
  }

  function prepKitTemplate(profile, resumeText, opp, knowledge, synonyms) {
    knowledge = knowledge || {};
    const playbook = knowledge.skill_playbook || {};
    synonyms = synonyms !== undefined ? synonyms : (knowledge.skill_synonyms || {});
    const rows = evidenceMatrix(resumeText, opp, synonyms);

    const checklist = [];
    rows.forEach(function (r) {
      if (r.label === "No evidence") {
        checklist.push("Add evidence for **" + r.requirement + "** — add a bullet only if you have actually done this work; otherwise do not claim it.");
      } else if (r.label === "Listed only") {
        checklist.push("**" + r.requirement + "** is listed but not shown in a project. Add a project bullet only if it is real; otherwise build one small project first.");
      }
    });

    const missing = rows.filter(function (r) { return r.label !== "Demonstrated"; }).map(function (r) { return r.requirement; });
    const topics = [
      "Typical topics for " + (opp.category || "this kind of role") + " — not confirmed by the organisation:",
      "Fundamentals of the required skills listed above.",
      "One walkthrough of a project from your resume, end to end.",
      "How you would approach a small task typical of the role."
    ];

    const focusPool = missing.length ? missing : rows.map(function (r) { return r.requirement; });
    const plan = [];
    for (let day = 1; day <= 7; day++) {
      const skill = focusPool.length ? focusPool[(day - 1) % focusPool.length] : "General preparation";
      const entry = playbook[norm(skill)] || playbook._generic || {};
      plan.push({
        day: day, focus: skill,
        tasks: [entry.task || "Spend a focused session on the basics.", entry.project || "Start a small project using it."],
        hours: 2,
        output: entry.project || "A small artefact you can show."
      });
    }

    return {
      evidence: rows, resume_checklist: checklist, interview_topics: topics, plan: plan,
      note: "Guidance only. This does not predict selection and is not confirmed by the organisation."
    };
  }

  /* ------------------------------------------------------------------ */
  /* Skill-gap analyzer + roadmap                                        */
  /* ------------------------------------------------------------------ */
  function skillGap(profile, selected, knowledge) {
    knowledge = knowledge || {};
    const synonyms = knowledge.skill_synonyms || {};
    const have = {};
    (profile.skills || []).forEach(function (s) { have[normSkill(s)] = 1; });
    const requiredUnion = {}, matched = {};
    selected.forEach(function (item) {
      const opp = item.opportunity || item;
      (opp.required_skills || []).forEach(function (s) { requiredUnion[normSkill(s)] = 1; });
      (item.matched || []).forEach(function (m) { matched[normSkill(m.skill)] = 1; });
    });
    const missing = Object.keys(requiredUnion).filter(function (s) { return !have[s]; });
    return {
      matching_skills: canonList(Object.keys(matched), synonyms),
      missing_skills: canonList(missing, synonyms),
      learning_plan: learningPlan(canonList(missing, synonyms), knowledge)
    };
  }

  function learningPlan(missing, knowledge) {
    const playbook = (knowledge || {}).skill_playbook || {};
    const rank = { python: 0, git: 1, sql: 2, "data structures": 3, excel: 4, linux: 5, communication: 6, "technical writing": 7 };
    const ordered = missing.slice().sort(function (a, b) {
      const ra = rank[a.toLowerCase()] !== undefined ? rank[a.toLowerCase()] : 50;
      const rb = rank[b.toLowerCase()] !== undefined ? rank[b.toLowerCase()] : 50;
      return (ra - rb) || (a < b ? -1 : 1);
    });
    return ordered.map(function (skill, i) {
      const entry = playbook[norm(skill)] || playbook._generic || {};
      return {
        priority: String(i + 1), skill: skill, estimated_time: "2-4 weeks",
        practice_project: entry.project || ("Build one small project using " + skill + " end to end."),
        resource_type: entry.resource_type || "Official documentation."
      };
    });
  }

  function buildRoadmap(plan) {
    if (!plan.length) {
      return ["Your skill set already covers the requirements of the selected opportunities. Focus on building one strong portfolio project and applying widely."];
    }
    const perPhase = Math.max(1, Math.floor(plan.length / 4) || 1);
    const chunks = [];
    for (let i = 0; i < plan.length; i += perPhase) chunks.push(plan.slice(i, i + perPhase));
    const roadmap = [];
    let week = 1;
    const step = Math.max(1, Math.floor(12 / Math.max(1, chunks.length)));
    chunks.forEach(function (chunk) {
      const names = chunk.map(function (c) { return c.skill; }).join(", ");
      const end = Math.min(week + step - 1, 12);
      roadmap.push("Weeks " + week + "-" + end + ": Build foundations in " + names + ". Finish at least one practice project.");
      week = end + 1;
    });
    roadmap.push("Final 2 weeks: polish one flagship project, write a short report, and prepare your applications.");
    return roadmap;
  }

  function strongMatchCount(items, threshold) {
    threshold = threshold === undefined ? 70.0 : threshold;
    return items.filter(function (it) { return (it.fit !== undefined ? it.fit : it.score_pct) >= threshold; }).length;
  }

  const API = {
    DEFAULT_WEIGHTS, RADAR_THRESHOLDS, FUZZY_THRESHOLD, EXPERIENCE_ORDER, VERIFICATION_WEIGHT,
    MASTER_SKILLS, INTEREST_OPTIONS, CATEGORY_ORDER, CATEGORY_BADGE,
    norm, normSkill, canonicalSkill, skillCredit, canonList, parseCgpa,
    today, asDate, isoOf, daysBetween,
    evaluateEligibility, resolveDeadline, timingStatus,
    scoreOpportunity, counterfactuals, topSkillGains,
    buildRadar, informationCompleteness,
    actionPriority, nextBestMove, pathway, whyNotApplyNow,
    splitSentences, evidenceMatrix, validateQuote, prepKitTemplate,
    skillGap, learningPlan, buildRoadmap, strongMatchCount,
    levRatio, tokenSetRatio
  };

  if (typeof module !== "undefined" && module.exports) module.exports = API;
  root.OppEngine = API;
})(typeof window !== "undefined" ? window : globalThis);
