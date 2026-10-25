/*
 * app.js — OpportunityAI website UI.
 * Vanilla JS, no build step, no dependencies. Uses OppEngine (engine.js) and
 * DATA (embedded opportunities + knowledge). Runs entirely in the browser.
 */
(function () {
  "use strict";

  const E = window.OppEngine;
  const OPPS = DATA.opportunities;
  const KNOW = DATA.knowledge;
  const NOTICE = DATA.notice;
  const SYN = KNOW.skill_synonyms || {};
  const LS_KEY = "opportunityai.v1";

  const DEMO_PROFILE = {
    name: "Aarav Sharma", college: "Indian Institute of Technology (BHU), Varanasi",
    degree: "B.Tech", branch: "Chemical Engineering", year: 2, cgpa: 8.2,
    skills: ["Python", "Pandas", "Excel", "Thermodynamics", "Git", "SQL", "Data Visualization"],
    interests: ["Data Science", "Machine Learning", "Chemical Engineering", "Research"],
    work_mode: "Any", location: "Any", experience: "Beginner", gender: "Prefer not to say"
  };

  const UI = {
    English: {
      tagline: "Personal Opportunity Intelligence Platform",
      radar: "Radar", nextmove: "Next Move", copilot: "Copilot", tracker: "Tracker",
      skills: "Skills & Gap", whynot: "Why Not?", assistant: "Assistant",
      apply_now: "Apply Now", prepare_for: "Prepare For", explore: "Explore",
      eligible: "Eligible", potentially: "Potentially Eligible", ineligible: "Ineligible",
      fit: "Fit", why_matches: "Why this opportunity?", matching_skills: "Matching skills",
      missing_skills: "Missing skills", gates: "Eligibility gates", breakdown: "Score breakdown",
      counterfactual: "If you learn one skill", next_action: "Next action",
      info_quality: "Information quality", why_not_apply: "Why isn't this in Apply Now?",
      top_action: "Recommended action", why: "Why", pathway: "Pathway",
      alternatives: "Other actions, ranked", effort: "Estimated effort", gap: "Fit gap addressed",
      relevance: "Relevance", confidence: "Evidence confidence",
      evidence: "Evidence Matrix", prep_kit: "7-Day Prep Kit",
      learning_plan: "Prioritised learning plan", roadmap: "12-week roadmap",
      disclaimer: "This is guidance based on your profile and the dataset — it is not a prediction of selection.",
      no_profile: "Set your profile in the panel, or press “Try Demo Profile”.",
      ask: "Ask about opportunities, skills or your profile…",
      view_details: "View details", save_tracker: "Save to Tracker", remove: "Remove",
      strong: "Strong matches", analysed: "Opportunities analysed", completeness: "Profile completeness",
      tracked: "Tracked", verified_sample: "Sample data", not_verified: "Not verified",
      nav_language: "Language", name: "Name", college: "College", degree: "Degree",
      branch: "Branch", year: "Year", cgpa: "CGPA (0-10)", experience: "Experience level",
      gender: "Gender (optional)", work_mode: "Preferred work mode", location: "Preferred location",
      skills_pick: "Technical skills", interests_pick: "Areas of interest",
      find_opportunities: "Find My Opportunities", preferences: "Preferences",
      reset_weights: "Reset weights", filter_mode: "Work mode", min_fit: "Minimum fit",
      resume_title: "Resume", consent: "I consent to sending redacted resume text to an AI service",
      data_title: "Data", export_csv: "Export Radar as CSV", delete_data: "Delete my data",
      ai_off: "AI features off. This website runs the deterministic engine only. Sarvam AI explanations, translation and PDF parsing are available in the Python app.",
      hero_title: "Find the opportunities that fit you - and know what to do next.",
      hero_body: "Internships, scholarships, hackathons, research programmes and competitions, matched to your skills, interests, academics and goals. Eligibility, timing and fit are kept as three separate facts, every unknown field is labelled, and one prioritised action is put in front of you.",
      hero_cta1: "Try Demo Profile", hero_cta2: "Open the app",
      tag1: "Explainable matching", tag2: "Next-best-move planner", tag3: "Resume evidence",
      tag4: "Runs offline", tag5: "No sign-up",
      profile: "Your profile", demo_profile: "Try Demo Profile", career_goal: "Career goal",
      demo_mode: "Demo Mode", weights: "Matching weights", filters: "Filters",
      category: "Category", required_skill: "Required skill",
    },
    Hindi: {
      tagline: "व्यक्तिगत अवसर इंटेलिजेंस प्लेटफ़ॉर्म",
      radar: "रडार", nextmove: "अगला कदम", copilot: "कोपायलट", tracker: "ट्रैकर",
      skills: "कौशल व अंतराल", whynot: "क्यों नहीं?", assistant: "सहायक",
      apply_now: "अभी आवेदन करें", prepare_for: "तैयारी करें", explore: "खोजें",
      eligible: "पात्र", potentially: "संभावित पात्र", ineligible: "अपात्र",
      fit: "फ़िट", why_matches: "यह अवसर क्यों?", matching_skills: "मेल खाते कौशल",
      missing_skills: "अनुपस्थित कौशल", gates: "पात्रता शर्तें", breakdown: "स्कोर विवरण",
      counterfactual: "यदि एक कौशल सीखें", next_action: "अगला कदम",
      info_quality: "सूचना गुणवत्ता", why_not_apply: "यह 'अभी आवेदन करें' में क्यों नहीं है?",
      top_action: "अनुशंसित कदम", why: "क्यों", pathway: "मार्ग",
      alternatives: "अन्य कदम, क्रम में", effort: "अनुमानित प्रयास", gap: "संबोधित फ़िट अंतराल",
      relevance: "प्रासंगिकता", confidence: "प्रमाण विश्वास",
      evidence: "प्रमाण मैट्रिक्स", prep_kit: "7-दिवसीय तैयारी किट",
      learning_plan: "प्राथमिकता सीखने की योजना", roadmap: "12-सप्ताह का रोडमैप",
      disclaimer: "यह आपकी प्रोफ़ाइल और डेटासेट पर आधारित मार्गदर्शन है — चयन की भविष्यवाणी नहीं।",
      no_profile: "पैनल में अपनी प्रोफ़ाइल भरें, या “डेमो प्रोफ़ाइल आज़माएँ” दबाएँ।",
      ask: "अवसरों, कौशल या प्रोफ़ाइल के बारे में पूछें…",
      view_details: "विवरण देखें", save_tracker: "ट्रैकर में सहेजें", remove: "हटाएँ",
      strong: "मज़बूत मिलान", analysed: "विश्लेषित अवसर", completeness: "प्रोफ़ाइल पूर्णता",
      tracked: "ट्रैक किए गए", verified_sample: "नमूना डेटा", not_verified: "सत्यापित नहीं",
      nav_language: "भाषा", name: "नाम", college: "कॉलेज", degree: "डिग्री",
      branch: "शाखा", year: "वर्ष", cgpa: "सीजीपीए (0-10)", experience: "अनुभव स्तर",
      gender: "लिंग (वैकल्पिक)", work_mode: "पसंदीदा कार्य मोड", location: "पसंदीदा स्थान",
      skills_pick: "तकनीकी कौशल", interests_pick: "रुचि के क्षेत्र",
      find_opportunities: "मेरे अवसर खोजें", preferences: "प्राथमिकताएँ",
      reset_weights: "भार रीसेट करें", filter_mode: "कार्य मोड", min_fit: "न्यूनतम फ़िट",
      resume_title: "रिज़्यूमे", consent: "मैं संपादित रिज़्यूमे पाठ AI सेवा को भेजने की सहमति देता/देती हूँ",
      data_title: "डेटा", export_csv: "रडार CSV निर्यात करें", delete_data: "मेरा डेटा हटाएँ",
      ai_off: "AI सुविधाएँ बंद। यह वेबसाइट केवल नियतात्मक इंजन चलाती है। Sarvam AI व्याख्या, अनुवाद और PDF पार्सिंग Python ऐप में उपलब्ध हैं।",
      hero_title: "वे अवसर खोजें जो आपके अनुरूप हैं - और जानें आगे क्या करें।",
      hero_body: "इंटर्नशिप, छात्रवृत्ति, हैकाथॉन, शोध कार्यक्रम और प्रतियोगिताएँ — आपके कौशल, रुचियों, अंकों और लक्ष्यों से मिलान। पात्रता, समय और फ़िट तीन अलग तथ्य हैं; हर अज्ञात फ़ील्ड चिह्नित है, और आपके सामने एक प्राथमिक कदम रखा जाता है।",
      hero_cta1: "डेमो प्रोफ़ाइल आज़माएँ", hero_cta2: "ऐप खोलें",
      tag1: "व्याख्यायोग्य मिलान", tag2: "अगला-कदम योजनाकार", tag3: "रिज़्यूमे प्रमाण",
      tag4: "ऑफ़लाइन चलता है", tag5: "साइन-अप नहीं",
      profile: "आपकी प्रोफ़ाइल", demo_profile: "डेमो प्रोफ़ाइल आज़माएँ", career_goal: "करियर लक्ष्य",
      demo_mode: "डेमो मोड", weights: "मिलान भार", filters: "फ़िल्टर",
      category: "श्रेणी", required_skill: "आवश्यक कौशल",
    }
  };

  const TIMING_BADGE = {
    open: ["Open", "b-green"], closing_soon: ["Closing soon", "b-amber"], rolling: ["Rolling", "b-blue"],
    not_yet_open: ["Opens later", "b-violet"], closed: ["Closed", "b-red"], unknown: ["Timing not verified", "b-grey"]
  };

  const STAGES = ["Discovered", "Shortlisted", "Preparing", "Applied", "Interview",
    "Selected", "Rejected", "Withdrawn", "No response"];

  /* ------------------------------------------------------------------ */
  /* state                                                              */
  /* ------------------------------------------------------------------ */
  let state = {
    profile: {}, weights: Object.assign({}, E.DEFAULT_WEIGHTS), demoMode: true,
    lang: "English", tab: "radar", careerGoal: "Undecided",
    resume: "", consent: false, tracker: {}, chat: [], detailId: null,
    evidence: null, prepKit: null, evidenceId: null,
    filters: { cat: "All", skill: "Any", mode: "All", min: 0 }
  };

  function load() {
    try {
      const raw = localStorage.getItem(LS_KEY);
      if (raw) {
        const s = JSON.parse(raw);
        state = Object.assign(state, s);
        state.weights = Object.assign({}, E.DEFAULT_WEIGHTS, s.weights || {});
        state.filters = Object.assign({ cat: "All", skill: "Any", mode: "All", min: 0 }, s.filters || {});
        state.tracker = s.tracker || {};
        state.chat = s.chat || [];
        state.resume = "";           // never persist resume text
        state.evidence = null; state.prepKit = null;
      }
    } catch (e) { /* ignore corrupt storage */ }
  }

  function save() {
    try {
      localStorage.setItem(LS_KEY, JSON.stringify({
        profile: state.profile, weights: state.weights, demoMode: state.demoMode,
        lang: state.lang, careerGoal: state.careerGoal, tracker: state.tracker,
        chat: state.chat.slice(-12), filters: state.filters
      }));
    } catch (e) { /* ignore quota errors */ }
  }

  const T = function (k) { return (UI[state.lang] || UI.English)[k] || UI.English[k] || k; };

  /* ------------------------------------------------------------------ */
  /* helpers                                                            */
  /* ------------------------------------------------------------------ */
  function esc(s) {
    return String(s === null || s === undefined ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }
  function badge(text, cls) { return '<span class="badge ' + (cls || "b-grey") + '">' + esc(text) + "</span>"; }
  function ring(pct, uid, size, stroke) {
    size = size || 78; stroke = stroke || 8;
    pct = Math.max(0, Math.min(100, Number(pct) || 0));
    const r = (size - stroke) / 2, c = 2 * Math.PI * r, off = c * (1 - pct / 100);
    const gid = "g_" + uid;
    return '<svg width="' + size + '" height="' + size + '" viewBox="0 0 ' + size + " " + size + '">' +
      '<defs><linearGradient id="' + gid + '" x1="0" y1="0" x2="1" y2="1">' +
      '<stop offset="0%" stop-color="#2563eb"/><stop offset="100%" stop-color="#7c3aed"/></linearGradient></defs>' +
      '<circle cx="' + size / 2 + '" cy="' + size / 2 + '" r="' + r + '" fill="none" stroke="#eaeff9" stroke-width="' + stroke + '"/>' +
      '<circle cx="' + size / 2 + '" cy="' + size / 2 + '" r="' + r + '" fill="none" stroke="url(#' + gid + ')" ' +
      'stroke-width="' + stroke + '" stroke-linecap="round" stroke-dasharray="' + c.toFixed(1) + '" ' +
      'stroke-dashoffset="' + off.toFixed(1) + '" transform="rotate(-90 ' + size / 2 + " " + size / 2 + ')"/>' +
      '<text x="50%" y="50%" text-anchor="middle" dominant-baseline="central" font-size="19" ' +
      'font-weight="800" fill="#0b1220">' + Math.round(pct) + "%</text></svg>";
  }
  const COMP_LABELS = [["skill", "Skill"], ["interest", "Interest"], ["academic", "Academic"],
    ["workmode", "Work mode"], ["experience", "Experience"]];
  function compBars(comp) {
    return COMP_LABELS.map(function (p) {
      const v = Math.max(0, Math.min(100, comp[p[0]] || 0));
      return '<div class="cbrow"><div class="cblab">' + p[1] + "</div>" +
        '<div class="cbtrack"><span style="width:' + v.toFixed(0) + '%"></span></div>' +
        '<div class="cbval">' + v.toFixed(0) + "%</div></div>";
    }).join("");
  }
  function eligBadge(status) {
    const map = { Eligible: ["b-green", T("eligible")], "Potentially Eligible": ["b-amber", T("potentially")], Ineligible: ["b-red", T("ineligible")] };
    const m = map[status] || ["b-grey", status];
    return badge(m[1], m[0]);
  }
  function verifBadge(opp) {
    if (opp.verification_status === "closed") return badge("Closed", "b-red");
    if (opp.verification_status === "verified") return badge("Verified " + (opp.last_verified || ""), "b-green");
    if (opp.verification_status === "fetched") return badge("Fetched (not human-checked)", "b-amber");
    return badge(T("verified_sample"), "b-amber");
  }
  function completeness(p) {
    if (!p || !p.name && !p.degree) return 0;
    const checks = [!!p.name, !!p.college, !!p.degree, !!p.branch, !!p.year,
      p.cgpa !== null && p.cgpa !== undefined, !!(p.skills || []).length,
      !!(p.interests || []).length, !!p.work_mode, !!p.experience];
    return Math.round(100 * checks.filter(Boolean).length / checks.length);
  }
  function hasProfile() { return !!(state.profile && state.profile.degree && state.profile.year); }

  function card(item, uidSuffix, rank) {
    const opp = item.opportunity, sc = item.score, fit = item.fit;
    const tb = TIMING_BADGE[item.timing] || ["Timing not verified", "b-grey"];
    const catCls = E.CATEGORY_BADGE[opp.category] || "b-grey";
    const ic = E.informationCompleteness(opp);
    const saved = !!state.tracker[opp.id];
    const demoB = (item.deadline && !opp.deadline) ? badge("DEMO deadline", "b-violet") : "";
    let verifyChip = "";
    if (item.eligibility.status === "Potentially Eligible" && item.eligibility.verify.length) {
      verifyChip = badge("Verify: " + item.eligibility.verify[0].slice(0, 44), "b-amber");
    }
    const matched = (sc.matched || []).slice(0, 5).map(function (m) {
      return '<span class="chip chip-have">' + esc(m.skill) + "</span>";
    }).join("");
    const missing = (sc.missing || []).slice(0, 5).map(function (s) {
      return '<span class="chip chip-miss">' + esc(s) + "</span>";
    }).join("");
    return '<div class="card"><div class="card-top">' +
      '<div style="flex:0 0 auto">' + ring(fit, opp.id + (uidSuffix || "")) + "</div>" +
      '<div style="flex:1 1 auto;min-width:0">' +
      '<div class="opp-title">' + esc(opp.title) + "</div>" +
      '<div class="opp-org">' + esc(opp.organization) + "</div>" +
      "<div>" + (rank ? badge("#" + rank, "b-violet") : "") + badge(opp.category, catCls) +
      badge(tb[0], tb[1]) + eligBadge(item.eligibility.status) + verifBadge(opp) +
      badge(T("info_quality") + " " + ic.completeness_pct + "%", "b-grey") + demoB +
      (saved ? badge(T("tracked"), "b-blue") : "") + "</div>" +
      (verifyChip ? '<div style="margin-top:8px">' + verifyChip + "</div>" : "") +
      "</div></div>" +
      '<div style="margin-top:8px">' + compBars(sc.components) + "</div>" +
      '<div style="margin-top:8px">' + matched + missing + "</div>" +
      '<div class="muted" style="margin-top:6px">' + esc(item.next_action || "") + "</div>" +
      "</div>";
  }

  function table(headers, rows) {
    if (!rows.length) return '<div class="empty">No rows.</div>';
    return "<table><thead><tr>" + headers.map(function (h) { return "<th>" + esc(h) + "</th>"; }).join("") +
      "</tr></thead><tbody>" + rows.map(function (r) {
        return "<tr>" + r.map(function (c) { return "<td>" + esc(c) + "</td>"; }).join("") + "</tr>";
      }).join("") + "</tbody></table>";
  }

  /* ------------------------------------------------------------------ */
  /* derived data                                                       */
  /* ------------------------------------------------------------------ */
  let cache = {};
  function radar() {
    if (!hasProfile()) return { apply_now: [], prepare_for: [], explore: [], excluded: [] };
    const key = JSON.stringify([state.profile, state.weights, state.demoMode]);
    if (cache.radarKey !== key) {
      cache.radar = E.buildRadar(state.profile, OPPS, state.weights, E.today(), state.demoMode, KNOW);
      cache.radarKey = key;
    }
    return cache.radar;
  }
  function allItems() {
    const r = radar();
    return r.apply_now.concat(r.prepare_for, r.explore);
  }
  function actions() {
    if (!hasProfile()) return [];
    const key = JSON.stringify([state.profile, state.weights, state.demoMode]);
    if (cache.actKey !== key) {
      cache.actions = E.actionPriority(state.profile, OPPS, state.weights, E.today(), KNOW, state.demoMode, 5);
      cache.actKey = key;
    }
    return cache.actions;
  }
  function applyFilters(items) {
    const f = state.filters;
    return items.filter(function (it) {
      const o = it.opportunity;
      if (f.cat !== "All" && o.category !== f.cat) return false;
      if (f.mode !== "All" && o.work_mode !== f.mode) return false;
      if (f.skill !== "Any" &&
        (o.required_skills || []).concat(o.preferred_skills || []).indexOf(f.skill) < 0) return false;
      if (it.fit < f.min) return false;
      return true;
    });
  }

  /* ------------------------------------------------------------------ */
  /* tab renderers                                                      */
  /* ------------------------------------------------------------------ */
  function renderRadar() {
    if (!hasProfile()) return '<div class="panel">' + T("no_profile") + "</div>";
    const r = radar();
    const panes = [["apply_now", T("apply_now")], ["prepare_for", T("prepare_for")], ["explore", T("explore")]];
    let html = '<div class="cols3">';
    panes.forEach(function (p) {
      const items = applyFilters(r[p[0]]);
      const cap = p[0] === "explore" ? E.RADAR_THRESHOLDS.explore_max : null;
      const shown = cap ? items.slice(0, cap) : items;
      html += '<div><div class="col-head"><span class="dot"></span>' + esc(p[1]) + " (" + items.length + ")</div>";
      if (cap && items.length > cap) html += '<div class="muted" style="margin-bottom:8px">Showing ' + cap + " of " + items.length + ".</div>";
      if (!shown.length) html += '<div class="empty">Nothing here with the current filters.</div>';
      shown.forEach(function (it, i) {
        html += card(it, p[0], p[0] === "apply_now" ? i + 1 : null);
        html += '<div class="row" style="margin:-6px 0 12px">' +
          '<button class="btn sm" data-action="detail" data-id="' + it.opportunity.id + '">' + T("view_details") + "</button>" +
          '<button class="btn sm" data-action="track" data-id="' + it.opportunity.id + '">+ ' + T("save_tracker") + "</button></div>";
      });
      html += "</div>";
    });
    html += "</div>";

    if (state.detailId) html += renderDetail(state.detailId);
    return html;
  }

  function renderDetail(id) {
    const it = allItems().filter(function (x) { return x.opportunity.id === id; })[0];
    if (!it) return "";
    const opp = it.opportunity, sc = it.score;
    const cf = E.counterfactuals(state.profile, opp, state.weights, SYN);
    const ic = E.informationCompleteness(opp);
    const needsWhyNot = ["open", "closing_soon", "rolling"].indexOf(it.timing) < 0 ||
      it.required_coverage < E.RADAR_THRESHOLDS.apply_min_coverage ||
      it.fit < E.RADAR_THRESHOLDS.apply_min_fit ||
      it.eligibility.status === "Potentially Eligible";

    let html = '<div class="panel" style="margin-top:16px"><h3><span class="dot"></span>' + esc(opp.title) + "</h3>" +
      '<div class="muted" style="margin-bottom:10px">' + esc(opp.organization) + " · " + esc(opp.category) +
      " · " + esc(opp.work_mode) + " · " + esc(opp.location) + "</div>" +
      '<div class="cols3"><div>' +
      '<div class="col-head">' + T("why_matches") + "</div>" + compBars(sc.components) +
      '<div class="small" style="margin-top:8px"><b>' + T("fit") + ":</b> " + it.fit.toFixed(1) + "%</div>" +
      ((sc.matched || []).length ? '<div style="margin-top:8px"><div class="muted">' + T("matching_skills") + "</div>" +
        sc.matched.map(function (m) {
          const tag = m.via === "synonym" ? " (synonym)" : (m.via === "similar" ? " (similar)" : "");
          return '<span class="chip chip-have">' + esc(m.skill + tag) + "</span>";
        }).join("") + "</div>" : "") +
      ((sc.missing || []).length ? '<div style="margin-top:8px"><div class="muted">' + T("missing_skills") + "</div>" +
        sc.missing.map(function (s) { return '<span class="chip chip-miss">' + esc(s) + "</span>"; }).join("") + "</div>" : "") +
      (cf.length ? '<div style="margin-top:10px"><div class="col-head">' + T("counterfactual") + "</div>" +
        cf.map(function (c) {
          return "<div class=\"small\">Learn <b>" + esc(c.skill) + "</b>: " + c.before_pct + "% → <b>" +
            c.after_pct + "%</b> (+" + c.delta + " pts)</div>";
        }).join("") + "</div>" : "") +
      "</div><div>" +
      '<div class="col-head">' + T("gates") + "</div>" +
      table(["Gate", "Result", "Detail"], it.eligibility.gates.map(function (g) { return [g.gate, g.status, g.detail]; })) +
      '<div class="small" style="margin-top:8px"><b>' + T("next_action") + ":</b> " + esc(it.next_action || "") + "</div>" +
      ((sc.unconfirmed || []).length ? '<div style="margin-top:8px"><div class="muted">' + T("not_verified") + "</div>" +
        sc.unconfirmed.map(function (u) { return '<div class="small">• ' + esc(u) + "</div>"; }).join("") + "</div>" : "") +
      "</div><div>" +
      '<div class="col-head">' + T("info_quality") + "</div>" +
      Object.keys(ic.fields).map(function (k) {
        return badge(k + ": " + (ic.fields[k] ? "stated" : "not stated"), ic.fields[k] ? "b-green" : "b-grey");
      }).join("") +
      '<div class="muted" style="margin-top:8px">' + esc(ic.label) + ": " + ic.completeness_pct + "% (" +
      ic.present_count + "/" + ic.total + " fields stated) · " +
      (ic.human_verified ? "human-verified" : "not human-verified") + ". " + esc(ic.note) + "</div>" +
      "</div></div>";

    if (needsWhyNot) {
      html += '<div style="margin-top:14px"><div class="col-head"><span class="dot"></span>' + T("why_not_apply") + "</div>" +
        table(["Check", "Status", "Detail", "Next"],
          E.whyNotApplyNow(it).map(function (r) { return [r.check, r.status, r.detail, r.action]; })) + "</div>";
    }
    html += '<div class="row" style="margin-top:14px">' +
      '<button class="btn sm" data-action="close-detail">Close</button></div></div>';
    return html;
  }

  function renderNextMove() {
    if (!hasProfile()) return '<div class="panel">' + T("no_profile") + "</div>";
    const acts = actions();
    if (!acts.length) {
      return '<div class="panel">Nothing to improve — you already cover the required skills for your top targets.</div>';
    }
    const top = acts[0];
    let html = '<div class="card" style="border-left:5px solid #2563eb">' +
      '<div class="muted" style="text-transform:uppercase;letter-spacing:.08em;font-weight:700">' + T("top_action") + "</div>" +
      '<div style="font-size:1.4rem;font-weight:800;margin:6px 0 4px">Learn ' + esc(top.skill) + "</div>" +
      '<div class="small">' + esc(top.why) + "</div></div>";

    html += '<div class="metrics">' +
      metric(T("effort"), top.hours + "h", "estimate") +
      metric(T("gap"), "+" + top.gap.toFixed(1), "points on average") +
      metric(T("relevance"), String(top.opportunities_lifted), "targets affected") +
      metric(T("confidence"), top.confidence.toFixed(2), "source weight") + "</div>";

    html += '<div class="cols3"><div class="panel"><h3><span class=\"dot\"></span>' + T("pathway") + "</h3>" +
      E.pathway(top).map(function (s, i) {
        return '<div class="path-step"><div class="n">' + (i + 1) + '</div><div class="small"><b>' +
          esc(s.stage) + "</b> — " + esc(s.detail) + "</div></div>";
      }).join("") + "</div>" +
      '<div class="panel" style="grid-column:span 2"><h3><span class="dot"></span>' + T("alternatives") + "</h3>" +
      table(["Action", "Priority", "Hours", "Avg gain", "Targets"], acts.map(function (a) {
        return ["Learn " + a.skill, a.priority.toFixed(3), a.hours, "+" + a.gap.toFixed(1), a.opportunities_lifted];
      })) + "</div></div>";

    if (top.needs_verification) {
      html += '<div class="note" style="margin-top:12px">One of the affected opportunities is only ' +
        "<i>Potentially Eligible</i> — confirm its eligibility before investing time.</div>";
    }
    html += '<div class="muted" style="margin-top:10px">' + esc(T("disclaimer")) + "</div>";
    return html;
  }

  function metric(label, value, sub) {
    return '<div class="metric"><div class="label">' + esc(label) + '</div><div class="value">' + esc(value) +
      '</div><div class="sub">' + esc(sub) + "</div></div>";
  }

  function renderCopilot() {
    if (!hasProfile()) return '<div class="panel">' + T("no_profile") + "</div>";
    const items = allItems();
    const options = items.map(function (it) {
      return '<option value="' + it.opportunity.id + '"' +
        (state.evidenceId === it.opportunity.id ? " selected" : "") + ">" +
        esc(it.opportunity.title) + "</option>";
    }).join("");
    const opp = items.filter(function (it) { return it.opportunity.id === state.evidenceId; })[0] ||
      items[0] || { opportunity: OPPS[0] };

    let html = '<div class="panel"><h3><span class="dot"></span>AI Application Copilot</h3>' +
      '<div class="muted">Built deterministically from your resume text. Every quote is checked against the ' +
      "resume in code — a quote that is not there is discarded.</div>" +
      '<label for="cop-opp">Opportunity</label><select id="cop-opp">' + options + "</select>" +
      '<div class="row" style="margin-top:12px">' +
      '<button class="btn primary" data-action="build-evidence">Build Evidence Matrix</button>' +
      '<button class="btn" data-action="build-prep">Generate 7-Day Prep Kit</button></div></div>';

    if (!state.resume) {
      html += '<div class="note">No resume text yet — paste it in the panel on the left. ' +
        "Everything works offline; PDF parsing needs the Python app or an internet connection.</div>";
    }

    if (state.evidence) {
      html += '<div class="panel"><h3><span class="dot"></span>' + T("evidence") + "</h3>";
      html += state.evidence.map(function (r) {
        const cls = r.label === "Demonstrated" ? "b-green" : (r.label === "Listed only" ? "b-amber" : "b-grey");
        return "<div style=\"margin-bottom:10px\"><b>" + esc(r.requirement) + "</b> " + badge(r.label, cls) +
          " " + badge(r.section, "b-grey") +
          (r.quote ? '<div class="q">' + esc(r.quote) + "</div>" : '<div class="muted">No evidence found.</div>') +
          "</div>";
      }).join("") + "</div>";
    }

    if (state.prepKit) {
      const kit = state.prepKit;
      html += '<div class="panel"><h3><span class="dot"></span>' + T("prep_kit") + "</h3>" +
        "<b>Resume checklist</b>" + kit.resume_checklist.map(function (c) {
          return '<div class="small">• ' + esc(c).replace(/\*\*/g, "") + "</div>";
        }).join("") +
        '<div style="margin-top:10px"><b>Interview topics</b>' + kit.interview_topics.map(function (c) {
          return '<div class="small">• ' + esc(c) + "</div>";
        }).join("") + "</div>" +
        '<div style="margin-top:10px"><b>7-day plan</b>' +
        table(["Day", "Focus", "Hours", "Tasks", "Output"], kit.plan.map(function (d) {
          return [d.day, d.focus, d.hours, d.tasks.join(" · "), d.output];
        })) + "</div>" +
        '<div class="muted" style="margin-top:8px">' + esc(kit.note) + "</div>" +
        '<div class="row" style="margin-top:10px"><button class="btn sm" data-action="track" data-id="' +
        esc(opp.opportunity.id) + '">+ ' + T("save_tracker") + "</button></div></div>";
    }
    return html;
  }

  function renderSkills() {
    if (!hasProfile()) return '<div class="panel">' + T("no_profile") + "</div>";
    const pool = allItems();
    if (!pool.length) return '<div class="panel">No eligible opportunities yet.</div>';
    const chosen = pool.slice(0, 3);
    const gap = E.skillGap(state.profile, chosen, KNOW);
    return '<div class="cols3"><div class="panel"><h3><span class="dot"></span>' + T("matching_skills") + "</h3>" +
      (gap.matching_skills.length ? gap.matching_skills.map(function (s) {
        return '<span class="chip chip-have">' + esc(s) + "</span>";
      }).join("") : '<div class="empty">None yet.</div>') + "</div>" +
      '<div class="panel" style="grid-column:span 2"><h3><span class="dot"></span>' + T("missing_skills") + "</h3>" +
      (gap.missing_skills.length ? gap.missing_skills.map(function (s) {
        return '<span class="chip chip-miss">' + esc(s) + "</span>";
      }).join("") : '<div class="empty">No gaps against your top matches.</div>') + "</div></div>" +
      '<div class="panel"><h3><span class="dot"></span>' + T("learning_plan") + "</h3>" +
      table(["Priority", "Skill", "Practice project", "Resource type"], gap.learning_plan.map(function (p) {
        return [p.priority, p.skill, p.practice_project, p.resource_type];
      })) + "</div>" +
      '<div class="panel"><h3><span class="dot"></span>' + T("roadmap") + "</h3>" +
      E.buildRoadmap(gap.learning_plan).map(function (l) { return '<div class="small">• ' + esc(l) + "</div>"; }).join("") +
      '<div class="muted" style="margin-top:8px">Practical suggestions only — they do not guarantee selection.</div></div>';
  }

  function renderWhyNot() {
    if (!hasProfile()) return '<div class="panel">' + T("no_profile") + "</div>";
    const ex = radar().excluded;
    if (!ex.length) return '<div class="panel">Nothing is excluded for this profile.</div>';
    return '<div class="panel"><h3><span class="dot"></span>' + T("whynot") + "</h3>" +
      '<div class="muted" style="margin-bottom:10px">An unverified field is never a failure — only a stated ' +
      "requirement that is not met, or a closed deadline.</div>" +
      ex.map(function (it) {
        const o = it.opportunity;
        const tb = TIMING_BADGE[it.timing] || ["unknown", "b-grey"];
        return '<div class="card"><div class="opp-title">' + esc(o.title) + "</div>" +
          '<div class="opp-org">' + esc(o.organization) + "</div><div>" +
          badge(o.category, E.CATEGORY_BADGE[o.category] || "b-grey") + eligBadge(it.eligibility.status) +
          badge(tb[0], tb[1]) + verifBadge(o) + "</div>" +
          '<div class="small" style="margin-top:8px"><b>Reason:</b> ' + esc(it.reason) + "</div>" +
          '<div class="muted" style="margin-top:4px"><b>What would help:</b> ' + esc(it.fix) + "</div>" +
          '<div style="margin-top:8px">' + table(["Gate", "Result", "Detail"],
            it.eligibility.gates.map(function (g) { return [g.gate, g.status, g.detail]; })) + "</div></div>";
      }).join("") + "</div>";
  }

  function renderTracker() {
    const ids = Object.keys(state.tracker);
    if (!ids.length) {
      return '<div class="panel">Nothing tracked yet. Use <b>' + T("save_tracker") + "</b> on a Radar card.</div>";
    }
    let html = '<div class="panel"><h3><span class="dot"></span>' + T("tracker") + "</h3>" +
      '<div class="muted">Stored in your browser (localStorage). It persists across reloads on this device.</div>';
    ids.forEach(function (id) {
      const opp = OPPS.filter(function (o) { return o.id === id; })[0];
      const entry = state.tracker[id];
      html += '<div class="row" style="margin-top:12px;flex-wrap:wrap">' +
        '<div style="flex:1 1 240px"><b>' + esc(opp ? opp.title : id) + "</b>" +
        '<div class="muted">' + esc(opp ? opp.organization : "") + " · " + esc(entry.stage) + "</div></div>" +
        '<select data-action="stage" data-id="' + esc(id) + '" style="max-width:190px">' +
        STAGES.map(function (s) {
          return '<option value="' + s + '"' + (entry.stage === s ? " selected" : "") + ">" + s + "</option>";
        }).join("") + "</select>" +
        '<button class="btn sm" data-action="untrack" data-id="' + esc(id) + '">' + T("remove") + "</button></div>";
    });
    html += "</div>";
    const counts = {};
    Object.keys(state.tracker).forEach(function (id) {
      const s = state.tracker[id].stage;
      counts[s] = (counts[s] || 0) + 1;
    });
    html += '<div class="panel"><h3><span class="dot\"></span>Funnel</h3>' +
      STAGES.filter(function (s) { return counts[s]; }).map(function (s) {
        return '<div class="small">• <b>' + esc(s) + "</b>: " + counts[s] + "</div>";
      }).join("") + "</div>";
    return html;
  }

  function renderAssistant() {
    let html = '<div class="panel"><h3><span class="dot"></span>' + T("assistant") + "</h3>" +
      '<div class="muted">Answers come from your profile and the local dataset. It has not searched the internet.</div>' +
      '<div class="chat" id="chat">' +
      (state.chat.length ? state.chat : [{ role: "bot", text: "Ask me: “Which opportunities are best for my profile?”, “What should I learn?”, “Show beginner-friendly options”, or “Opportunities for a second-year student”." }])
        .map(function (m) {
          return '<div class="msg ' + (m.role === "user" ? "user" : "bot") + '">' + esc(m.text) + "</div>";
        }).join("") + "</div>" +
      '<div class="row" style="margin-top:10px"><input type="text" id="chat-in" placeholder="' + esc(T("ask")) +
      '" style="flex:1"><button class="btn primary" data-action="chat-send">Send</button>' +
      '<button class="btn" data-action="chat-clear">Clear</button></div></div>';
    return html;
  }

  /* ------------------------------------------------------------------ */
  /* local assistant (ported from sarvam_client.local_answer)            */
  /* ------------------------------------------------------------------ */
  function localAnswer(q) {
    const s = (q || "").toLowerCase().trim().replace(/-/g, " ");
    const items = allItems().slice().sort(function (a, b) { return b.fit - a.fit; });
    if (!s) return "Ask about your best matches, what to learn, or which opportunities suit your year.";
    if (/best|top|recommend|suit my profile|match/.test(s)) {
      if (!items.length) return "I don't have a profile to match yet. Press “Try Demo Profile” on the left.";
      return "Based on your profile, your strongest matches are:\n" + items.slice(0, 3).map(function (i) {
        return "• " + i.opportunity.title + " — " + i.opportunity.organization + " (" + i.fit.toFixed(0) + "% fit)";
      }).join("\n") + "\nOpen the Radar for the full reasoning on each.";
    }
    if (/learn|skill|data scientist|become a|study/.test(s)) {
      const gaps = [];
      items.slice(0, 5).forEach(function (i) { (i.score.missing || []).forEach(function (m) { gaps.push(m); }); });
      const seen = {}, ordered = [];
      gaps.forEach(function (g) { if (!seen[g.toLowerCase()]) { seen[g.toLowerCase()] = 1; ordered.push(g); } });
      if (ordered.length) return "For your top matches, prioritise: " + ordered.slice(0, 6).join(", ") +
        ". The Skills & Gap tab turns this into a plan.";
      return "Fill in your profile (or use the demo profile) so I can be specific about skills.";
    }
    const ym = { first: 1, "1st": 1, second: 2, "2nd": 2, third: 3, "3rd": 3, final: 4, fourth: 4, "4th": 4 };
    if (/year/.test(s)) {
      let want = null;
      Object.keys(ym).forEach(function (k) { if (s.indexOf(k) >= 0) want = ym[k]; });
      if (want) {
        const picks = OPPS.filter(function (o) { return (o.eligible_years || []).indexOf(want) >= 0; }).slice(0, 4);
        if (picks.length) return "Opportunities that accept year " + want + ":\n" + picks.map(function (o) {
          return "• " + o.title + " — " + o.organization;
        }).join("\n") + "\nSample records — confirm the current intake on the official site.";
      }
      return "I couldn't match that year. Try 'second year' or 'final year'.";
    }
    if (/no experience|without experience|beginner|fresher|no prior/.test(s)) {
      const picks = OPPS.filter(function (o) { return o.experience_level === "Beginner"; }).slice(0, 5);
      return "Beginner-friendly options:\n" + picks.map(function (o) {
        return "• " + o.title + " — " + o.organization + " (" + o.category + ")";
      }).join("\n") + "\nStart with one to build a portfolio before targeting advanced roles.";
    }
    if (/research|improve my chances|chances|paper/.test(s)) {
      return "To strengthen a research application: build one small, documented project; learn to read and " +
        "summarise a paper; and write to a faculty mentor with a specific question. I can't guarantee " +
        "outcomes, but these improve your profile.";
    }
    if (/deadline|last date|apply by|when/.test(s)) {
      return "The sample dataset does not carry verified deadlines, so I won't invent any. Check the current " +
        "dates on the organisation's official website.";
    }
    if (/chemical|process|aspen/.test(s)) {
      const picks = OPPS.filter(function (o) { return o.category === "Chemical Engineering Internship"; });
      if (picks.length) return "Chemical-engineering options:\n" + picks.map(function (o) {
        return "• " + o.title + " — " + o.organization + " (" + o.work_mode + ")";
      }).join("\n");
    }
    if (/scholarship/.test(s)) {
      const picks = OPPS.filter(function (o) { return o.category === "Scholarship"; });
      if (picks.length) return "Scholarship records:\n" + picks.map(function (o) {
        return "• " + o.title + " — " + o.organization;
      }).join("\n") + "\nEligibility and income criteria vary; verify on the official source.";
    }
    return "I answer from a fixed sample dataset and your profile — I haven't searched the internet. Try: " +
      "“Which opportunities are best for my profile?”, “What should I learn?”, “Show beginner-friendly " +
      "options”, or “Opportunities for a second-year student”.";
  }

  /* ------------------------------------------------------------------ */
  /* main render                                                        */
  /* ------------------------------------------------------------------ */
  function applyI18n() {
    document.querySelectorAll("[data-i18n]").forEach(function (el) {
      const v = (UI[state.lang] || UI.English)[el.getAttribute("data-i18n")];
      if (v) el.textContent = v;
    });
    document.querySelectorAll("[data-i18n-ph]").forEach(function (el) {
      const v = (UI[state.lang] || UI.English)[el.getAttribute("data-i18n-ph")];
      if (v) el.setAttribute("placeholder", v);
    });
  }

  function render() {
    applyI18n();
    document.querySelectorAll(".tab").forEach(function (b) {
      b.classList.toggle("active", b.dataset.tab === state.tab);
    });
    document.getElementById("lang-label").textContent = state.lang;
    const main = document.getElementById("main");
    if (state.tab === "radar") main.innerHTML = renderRadar();
    else if (state.tab === "nextmove") main.innerHTML = renderNextMove();
    else if (state.tab === "copilot") main.innerHTML = renderCopilot();
    else if (state.tab === "skills") main.innerHTML = renderSkills();
    else if (state.tab === "whynot") main.innerHTML = renderWhyNot();
    else if (state.tab === "tracker") main.innerHTML = renderTracker();
    else main.innerHTML = renderAssistant();
    renderMetrics();
    save();
  }

  function renderMetrics() {
    const items = allItems();
    const strong = E.strongMatchCount(items);
    document.getElementById("metrics").innerHTML =
      metric(T("completeness"), completeness(state.profile) + "%", state.profile.name || "no profile yet") +
      metric(T("analysed"), String(OPPS.length), "sample dataset") +
      metric(T("strong"), String(strong), "70% fit or higher") +
      metric(T("tracked"), String(Object.keys(state.tracker).length), "in tracker");
  }

  /* ------------------------------------------------------------------ */
  /* profile form                                                       */
  /* ------------------------------------------------------------------ */
  function skillsPicker() {
    document.getElementById("pf-skills").innerHTML = E.MASTER_SKILLS.map(function (s) {
      return '<label><input type="checkbox" data-skill="' + esc(s) + '">' + esc(s) + "</label>";
    }).join("");
    document.getElementById("pf-interests").innerHTML = E.INTEREST_OPTIONS.map(function (s) {
      return '<label><input type="checkbox" data-interest="' + esc(s) + '">' + esc(s) + "</label>";
    }).join("");
  }

  function syncForm() {
    const p = state.profile || {};
    const set = function (id, v) { const el = document.getElementById(id); if (el) el.value = v === null || v === undefined ? "" : v; };
    set("pf-name", p.name || ""); set("pf-college", p.college || ""); set("pf-branch", p.branch || "");
    set("pf-year", p.year || 1); set("pf-cgpa", p.cgpa === null || p.cgpa === undefined ? "" : p.cgpa);
    set("pf-degree", p.degree || "B.Tech"); set("pf-exp", p.experience || "Beginner");
    set("pf-gender", p.gender || "Prefer not to say"); set("pf-mode", p.work_mode || "Any");
    set("pf-location", p.location || "Any"); set("pf-goal", state.careerGoal);
    document.querySelectorAll("[data-skill]").forEach(function (cb) {
      cb.checked = (p.skills || []).indexOf(cb.dataset.skill) >= 0;
    });
    document.querySelectorAll("[data-interest]").forEach(function (cb) {
      cb.checked = (p.interests || []).indexOf(cb.dataset.interest) >= 0;
    });
    document.getElementById("f-cat").value = state.filters.cat;
    document.getElementById("f-mode").value = state.filters.mode;
    document.getElementById("f-min").value = state.filters.min;
    document.getElementById("f-min-val").textContent = state.filters.min + "%";
    document.getElementById("demo-toggle").checked = state.demoMode;
  }

  function readForm() {
    const skills = Array.prototype.slice.call(document.querySelectorAll("[data-skill]:checked")).map(function (c) { return c.dataset.skill; });
    const interests = Array.prototype.slice.call(document.querySelectorAll("[data-interest]:checked")).map(function (c) { return c.dataset.interest; });
    let cgpa = null;
    try { cgpa = E.parseCgpa(document.getElementById("pf-cgpa").value); }
    catch (err) { alert("Invalid CGPA: " + err.message + " Leave it blank if you prefer not to share it."); return false; }
    state.profile = {
      name: document.getElementById("pf-name").value.trim(),
      college: document.getElementById("pf-college").value.trim(),
      degree: document.getElementById("pf-degree").value,
      branch: document.getElementById("pf-branch").value.trim(),
      year: Number(document.getElementById("pf-year").value),
      cgpa: cgpa, skills: skills, interests: interests,
      work_mode: document.getElementById("pf-mode").value,
      location: document.getElementById("pf-location").value.trim() || "Any",
      experience: document.getElementById("pf-exp").value,
      gender: document.getElementById("pf-gender").value
    };
    return true;
  }

  /* ------------------------------------------------------------------ */
  /* csv + downloads                                                    */
  /* ------------------------------------------------------------------ */
  function download(name, text, mime) {
    const blob = new Blob([text], { type: mime || "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = name; document.body.appendChild(a); a.click();
    document.body.removeChild(a); URL.revokeObjectURL(url);
  }
  function csvOfRadar() {
    const r = radar();
    const rows = [["pane", "id", "title", "organization", "category", "fit_pct", "required_coverage",
      "eligibility", "timing", "deadline", "verification_status", "missing_skills"]];
    ["apply_now", "prepare_for", "explore", "excluded"].forEach(function (pane) {
      r[pane].forEach(function (it) {
        const o = it.opportunity, sc = it.score;
        rows.push([pane, o.id, o.title, o.organization, o.category, it.fit.toFixed(1),
          sc.required_coverage.toFixed(2), it.eligibility.status, it.timing, it.deadline || "",
          o.verification_status, (sc.missing || []).join("; ")]);
      });
    });
    return rows.map(function (r) {
      return r.map(function (c) {
        const s = String(c === null || c === undefined ? "" : c);
        return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
      }).join(",");
    }).join("\n");
  }

  /* ------------------------------------------------------------------ */
  /* events                                                             */
  /* ------------------------------------------------------------------ */
  function wire() {
    document.querySelectorAll(".tab").forEach(function (b) {
      b.addEventListener("click", function () { state.tab = b.dataset.tab; render(); window.scrollTo({ top: 0, behavior: "smooth" }); });
    });

    document.getElementById("btn-demo").addEventListener("click", function () {
      state.profile = JSON.parse(JSON.stringify(DEMO_PROFILE));
      state.detailId = null; state.evidence = null; state.prepKit = null;
      syncForm(); render();
      window.scrollTo({ top: document.getElementById("main").offsetTop - 80, behavior: "smooth" });
    });
    document.getElementById("btn-demo-hero").addEventListener("click", function () {
      document.getElementById("btn-demo").click();
    });
    document.getElementById("btn-goto-app").addEventListener("click", function () {
      window.scrollTo({ top: document.getElementById("layout").offsetTop - 70, behavior: "smooth" });
    });
    document.getElementById("btn-apply-profile").addEventListener("click", function () {
      if (readForm()) { state.detailId = null; render(); }
    });

    document.getElementById("pf-year").addEventListener("change", function () { });
    document.getElementById("demo-toggle").addEventListener("change", function (e) {
      state.demoMode = e.target.checked; render();
    });
    document.getElementById("lang-toggle").addEventListener("click", function () {
      state.lang = state.lang === "English" ? "Hindi" : "English"; syncForm(); render();
    });
    document.getElementById("pf-goal").addEventListener("change", function (e) {
      state.careerGoal = e.target.value; save();
    });

    ["f-cat", "f-mode"].forEach(function (id) {
      document.getElementById(id).addEventListener("change", function (e) {
        state.filters[id === "f-cat" ? "cat" : "mode"] = e.target.value; render();
      });
    });
    document.getElementById("f-skill").addEventListener("change", function (e) {
      state.filters.skill = e.target.value; render();
    });
    document.getElementById("f-min").addEventListener("input", function (e) {
      state.filters.min = Number(e.target.value);
      document.getElementById("f-min-val").textContent = state.filters.min + "%";
      render();
    });

    [["w-skill", "skill"], ["w-interest", "interest"], ["w-academic", "academic"],
     ["w-workmode", "workmode"], ["w-experience", "experience"]].forEach(function (pair) {
      const el = document.getElementById(pair[0]);
      el.value = Math.round(state.weights[pair[1]] * 100);
      document.getElementById(pair[0] + "-val").textContent = el.value + "%";
      el.addEventListener("input", function (e) {
        state.weights[pair[1]] = Number(e.target.value) / 100;
        document.getElementById(pair[0] + "-val").textContent = e.target.value + "%";
        render();
      });
    });
    document.getElementById("btn-reset-weights").addEventListener("click", function () {
      state.weights = Object.assign({}, E.DEFAULT_WEIGHTS);
      syncForm();
      [["w-skill", "skill"], ["w-interest", "interest"], ["w-academic", "academic"],
       ["w-workmode", "workmode"], ["w-experience", "experience"]].forEach(function (pair) {
        const el = document.getElementById(pair[0]);
        el.value = Math.round(state.weights[pair[1]] * 100);
        document.getElementById(pair[0] + "-val").textContent = el.value + "%";
      });
      render();
    });

    document.getElementById("resume-text").addEventListener("input", function (e) {
      state.resume = e.target.value; state.evidence = null; state.prepKit = null;
    });
    document.getElementById("resume-file").addEventListener("change", function (e) {
      const f = e.target.files[0];
      if (!f) return;
      if (f.size > 5 * 1024 * 1024) { alert("File is larger than 5 MB."); return; }
      if (/\.pdf$/i.test(f.name)) {
        alert("PDF parsing in the browser needs an internet connection (pdf.js).\n\n" +
          "Paste the resume text into the box instead — that works fully offline — " +
          "or use the Python app for PDF upload.");
        return;
      }
      const reader = new FileReader();
      reader.onload = function () {
        state.resume = String(reader.result || "").slice(0, 60000);
        document.getElementById("resume-text").value = state.resume;
        state.evidence = null; state.prepKit = null;
        render();
      };
      reader.readAsText(f);
    });
    document.getElementById("consent").addEventListener("change", function (e) {
      state.consent = e.target.checked;
    });

    document.getElementById("btn-csv").addEventListener("click", function () {
      download("opportunityai_radar.csv", csvOfRadar(), "text/csv");
    });
    document.getElementById("btn-wipe").addEventListener("click", function () {
      if (!confirm("Delete your profile, tracker and chat stored in this browser?")) return;
      localStorage.removeItem(LS_KEY);
      state = { profile: {}, weights: Object.assign({}, E.DEFAULT_WEIGHTS), demoMode: true,
        lang: "English", tab: state.tab, careerGoal: "Undecided", resume: "", consent: false,
        tracker: {}, chat: [], detailId: null, evidence: null, prepKit: null, evidenceId: null,
        filters: { cat: "All", skill: "Any", mode: "All", min: 0 } };
      cache = {};
      document.getElementById("resume-text").value = "";
      syncForm(); render();
    });

    document.getElementById("main").addEventListener("click", function (e) {
      const btn = e.target.closest("[data-action]");
      if (!btn) return;
      const action = btn.dataset.action, id = btn.dataset.id;
      if (action === "detail") { state.detailId = id; render(); }
      else if (action === "close-detail") { state.detailId = null; render(); }
      else if (action === "track") {
        state.tracker[id] = { stage: "Shortlisted" }; render();
      } else if (action === "untrack") {
        delete state.tracker[id]; render();
      } else if (action === "build-evidence") {
        const sel = document.getElementById("cop-opp");
        const oppId = sel ? sel.value : (allItems()[0] || { opportunity: OPPS[0] }).opportunity.id;
        const opp = OPPS.filter(function (o) { return o.id === oppId; })[0];
        state.evidenceId = oppId;
        state.evidence = E.evidenceMatrix(state.resume, opp, SYN);
        state.prepKit = null;
        render();
      } else if (action === "build-prep") {
        const sel = document.getElementById("cop-opp");
        const oppId = sel ? sel.value : (allItems()[0] || { opportunity: OPPS[0] }).opportunity.id;
        const opp = OPPS.filter(function (o) { return o.id === oppId; })[0];
        state.evidenceId = oppId;
        state.prepKit = E.prepKitTemplate(state.profile, state.resume, opp, KNOW, SYN);
        if (!state.evidence) state.evidence = state.prepKit.evidence;
        render();
      } else if (action === "chat-send") {
        sendChat();
      } else if (action === "chat-clear") {
        state.chat = []; render();
      }
    });

    document.getElementById("main").addEventListener("change", function (e) {
      const el = e.target.closest("[data-action='stage']");
      if (el) {
        const id = el.dataset.id;
        if (state.tracker[id]) { state.tracker[id].stage = el.value; render(); }
      }
      const sel = e.target.closest("#cop-opp");
      if (sel) { state.evidenceId = sel.value; state.evidence = null; state.prepKit = null; render(); }
    });

    document.getElementById("main").addEventListener("keydown", function (e) {
      if (e.target.id === "chat-in" && e.key === "Enter") sendChat();
    });

    document.querySelectorAll(".tab").forEach(function (b) { });
  }

  function sendChat() {
    const input = document.getElementById("chat-in");
    if (!input) return;
    const q = input.value.trim();
    if (!q) return;
    state.chat.push({ role: "user", text: q });
    state.chat.push({ role: "bot", text: localAnswer(q) });
    input.value = "";
    render();
    const c = document.getElementById("chat");
    if (c) c.scrollTop = c.scrollHeight;
  }

  /* ------------------------------------------------------------------ */
  /* init                                                               */
  /* ------------------------------------------------------------------ */
  function init() {
    load();
    skillsPicker();
    document.getElementById("f-skill").innerHTML = ["Any"].concat(
      Array.from(new Set(OPPS.flatMap(function (o) { return (o.required_skills || []).concat(o.preferred_skills || []); }))).sort()
    ).map(function (s) { return '<option value="' + esc(s) + '">' + esc(s) + "</option>"; }).join("");
    document.getElementById("notice").textContent = NOTICE;
    syncForm();
    wire();
    render();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
