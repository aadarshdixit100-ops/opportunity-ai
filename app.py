"""
app.py — OpportunityAI : Personal Opportunity Intelligence Platform.

Tabs: Radar | Copilot | Tracker | Skills & Gap | Why Not? | Assistant
Run:  streamlit run app.py

Runs fully offline with no API key. All dataset / ingested / resume text is
HTML-escaped before it enters an unsafe_allow_html block.
"""

from __future__ import annotations

import csv
import html
import io
import os
from typing import Any, Dict, List, Optional

import streamlit as st

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import db
import recommender as R
from sarvam_client import LANGUAGES, SarvamClient, local_answer, redact_pii

st.set_page_config(page_title="OpportunityAI", page_icon="🎯", layout="wide")

# --------------------------------------------------------------------------- #
# Theme
# --------------------------------------------------------------------------- #
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* ---------- Palette ---------------------------------------------------- */
:root{
  --navy:#0b1220;      /* primary text */
  --navy-2:#3b4a61;    /* secondary text */
  --muted:#5b6b82;     /* muted text (AA contrast on white) */
  --blue:#2563eb; --violet:#7c3aed;
  --bg:#f5f7fc; --card:#ffffff; --line:#e3e8f2;
  --green:#047857; --amber:#b45309; --red:#b91c1c;
  --green-bg:#e6f7ef; --amber-bg:#fdf1dd; --red-bg:#fdeaea;
  --blue-bg:#e8f0ff; --violet-bg:#f1e9ff; --grey-bg:#eef1f6;
}

/* ---------- Base -------------------------------------------------------
   Colour is set explicitly on the containers Streamlit paints, so it never
   depends on the framework's theme colour leaking through. The previous
   version relied on a `[class*="css"]` selector, which matches nothing in
   Streamlit 1.66 (classes are st-emotion-cache-*), leaving light theme text
   on the light backgrounds this stylesheet paints.                        */
html, body{
  font-family:'Inter','Segoe UI',system-ui,-apple-system,sans-serif;
  color:var(--navy);
}
.stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"]{color:var(--navy);}
.stApp{
  background:
    radial-gradient(1100px 460px at 10% -8%, #e8efff 0, rgba(232,239,255,0) 60%),
    radial-gradient(900px 420px at 92% 0, #f2eaff 0, rgba(242,234,255,0) 55%),
    var(--bg);
}
.block-container{padding-top:1rem;padding-bottom:3rem;max-width:1240px;}

h1,h2,h3,h4,h5,h6{color:var(--navy);letter-spacing:-.015em;}
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li{color:var(--navy);}
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] *,
.stCaption, small{color:var(--muted) !important;}

/* ---------- Sidebar ---------------------------------------------------- */
section[data-testid="stSidebar"]{background:var(--card);border-right:1px solid var(--line);}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] h4,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] li,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] [data-testid="stWidgetLabel"],
section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] *,
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] *{color:var(--navy);}
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] *{color:var(--muted) !important;}
div[data-testid="stSidebarNav"]{display:none;}

/* ---------- Tabs ------------------------------------------------------- */
.stTabs [data-baseweb="tab-list"]{gap:4px;background:transparent;border-bottom:1px solid var(--line);}
.stTabs [data-baseweb="tab"]{color:var(--navy-2);font-weight:600;background:transparent;
  border-radius:10px 10px 0 0;}
.stTabs [data-baseweb="tab"] p, .stTabs [data-baseweb="tab"] span{color:inherit;}
.stTabs [data-baseweb="tab"]:hover{color:var(--blue);background:rgba(37,99,235,.06);}
.stTabs [aria-selected="true"]{color:var(--blue) !important;}
/* Defensive: Streamlit has shipped tabs under more than one markup shape. */
[role="tab"], .stTabs button, [data-baseweb="tab-list"] button{color:var(--navy-2);}
[role="tab"] p, [role="tab"] span, .stTabs button p{color:inherit;}
[role="tab"][aria-selected="true"], .stTabs button[aria-selected="true"]{color:var(--blue);}
.stTabs [data-baseweb="tab-highlight"]{background-color:var(--blue);}
.stTabs [data-baseweb="tab-border"]{background-color:var(--line);}

/* ---------- Form controls ---------------------------------------------- */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stTextArea"] textarea,
[data-baseweb="select"] > div,
[data-baseweb="input"] input{
  background:var(--card) !important;color:var(--navy) !important;border-color:var(--line) !important;
}
[data-baseweb="select"] svg{fill:var(--navy-2);}
[data-baseweb="popover"] li, [role="option"]{color:var(--navy) !important;}
[data-baseweb="tag"]{background:var(--blue-bg) !important;}
[data-baseweb="tag"] span{color:#1d4ed8 !important;}
input[type="range"]{accent-color:var(--blue);}
[data-testid="stSlider"] [data-baseweb="slider"] div[role="slider"]{background-color:var(--blue);}

/* ---------- Buttons ---------------------------------------------------- */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button{
  border-radius:10px;font-weight:600;border:1px solid var(--line);
  background:var(--card);color:var(--navy);
}
.stButton > button p, .stDownloadButton > button p{color:inherit;}
.stButton > button:hover, .stDownloadButton > button:hover{border-color:#c7d8fb;color:var(--blue);}
/* Primary markers differ across Streamlit versions: kind="primary" and/or
   data-testid="stBaseButton-primary". Cover both so the button never renders
   as dark text on the gradient. */
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"],
.stButton > button[data-testid="stBaseButton-primary"],
.stFormSubmitButton > button[data-testid="stBaseButton-primary"],
button[data-testid="stBaseButton-primary"]{
  background:linear-gradient(135deg,var(--blue),var(--violet));border:none;color:#fff;
  box-shadow:0 10px 22px -14px rgba(37,99,235,.85);
}
.stButton > button[kind="primary"] p, .stButton > button[kind="primary"] span,
.stFormSubmitButton > button[kind="primary"] p,
button[data-testid="stBaseButton-primary"] p,
button[data-testid="stBaseButton-primary"] span{color:#fff !important;}
.stButton > button[kind="primary"]:hover,
button[data-testid="stBaseButton-primary"]:hover{filter:brightness(1.07);color:#fff;}
.stButton > button:focus-visible{outline:2px solid var(--blue);outline-offset:2px;}
.stButton > button:disabled, .stButton > button:disabled p{color:#94a3b8 !important;opacity:1;}

/* ---------- Alerts / expander / data ---------------------------------- */
[data-testid="stAlert"]{border-radius:12px;}
[data-testid="stAlert"] p, [data-testid="stAlert"] div{color:var(--navy);}
[data-testid="stExpander"]{border:1px solid var(--line);border-radius:14px;background:var(--card);}
[data-testid="stExpander"] summary, [data-testid="stExpander"] summary *{color:var(--navy);}
[data-testid="stDataFrame"]{border-radius:12px;}
[data-testid="stToggle"] label, [data-testid="stCheckbox"] label,
[data-testid="stRadio"] label, [data-testid="stMultiSelect"] label{color:var(--navy);}

/* ---------- Custom components ------------------------------------------ */
.hero{
  background:linear-gradient(118deg,#101a35 0,#1d3a8a 40%,#2563eb 68%,#7c3aed 100%);
  border-radius:22px;padding:26px 30px;color:#fff;margin-bottom:18px;
  box-shadow:0 24px 54px -28px rgba(37,99,235,.7);
}
.hero h1{color:#fff;margin:0 0 6px;font-size:1.9rem;font-weight:800;}
.hero p{margin:0;opacity:.95;font-size:.98rem;max-width:760px;color:#fff;}
.hero .kicker{font-size:.72rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;
  color:rgba(255,255,255,.85);margin-bottom:10px;}
.hero .tags{margin-top:12px;}
.hero .tags span{display:inline-block;background:rgba(255,255,255,.16);
  border:1px solid rgba(255,255,255,.26);color:#fff;padding:3px 11px;border-radius:999px;
  font-size:.75rem;margin:3px 6px 0 0;}
.statusstrip{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px;}
.statusstrip .pill{background:rgba(255,255,255,.16);border:1px solid rgba(255,255,255,.26);
  color:#fff;padding:4px 12px;border-radius:999px;font-size:.78rem;font-weight:600;}

.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:16px 18px;
  box-shadow:0 10px 24px -20px rgba(11,18,32,.55);margin-bottom:12px;transition:transform .16s,box-shadow .16s;}
.card:hover{transform:translateY(-2px);box-shadow:0 18px 34px -22px rgba(37,99,235,.5);}
.metric{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px;
  box-shadow:0 10px 22px -20px rgba(11,18,32,.5);height:100%;}
.metric .label{font-size:.71rem;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);font-weight:700;}
.metric .value{font-size:1.7rem;font-weight:800;margin-top:4px;color:var(--navy);}
.metric .sub{font-size:.79rem;color:var(--muted);margin-top:2px;}

.badge{display:inline-block;padding:3px 10px;border-radius:999px;font-size:.71rem;font-weight:600;margin:2px 5px 2px 0;}
.b-blue{background:var(--blue-bg);color:#1d4ed8;}
.b-violet{background:var(--violet-bg);color:#6d28d9;}
.b-green{background:var(--green-bg);color:var(--green);}
.b-amber{background:var(--amber-bg);color:var(--amber);}
.b-grey{background:var(--grey-bg);color:#475569;}
.b-red{background:var(--red-bg);color:var(--red);}

.chip{display:inline-block;background:var(--grey-bg);color:var(--navy-2);border-radius:8px;padding:3px 9px;
  font-size:.78rem;margin:2px 5px 2px 0;border:1px solid #e4eaf6;}
.chip-miss{background:var(--red-bg);color:var(--red);border-color:#f8d5d5;}
.chip-have{background:var(--green-bg);color:var(--green);border-color:#cdeee0;}

.opp-title{font-size:1.06rem;font-weight:700;margin:0;line-height:1.3;color:var(--navy);}
.opp-org{color:var(--muted);font-size:.86rem;margin:2px 0 7px;font-weight:500;}
.cbrow{display:flex;align-items:center;gap:9px;margin:4px 0;font-size:.79rem;color:var(--navy-2);}
.cblab{width:104px;color:var(--navy-2);}
.cbtrack{flex:1;height:7px;border-radius:999px;background:#e9eef7;overflow:hidden;}
.cbtrack>span{display:block;height:100%;border-radius:999px;background:linear-gradient(90deg,var(--blue),var(--violet));}
.cbval{width:38px;text-align:right;font-weight:600;color:var(--navy);}
.section-title{font-size:1.02rem;font-weight:700;margin:2px 0 9px;color:var(--navy);}
.section-title .dot{display:inline-block;width:8px;height:8px;border-radius:3px;margin-right:8px;
  background:linear-gradient(135deg,var(--blue),var(--violet));}
.muted{color:var(--muted);font-size:.83rem;}
.small{font-size:.84rem;color:var(--navy-2);}
.q{border-left:3px solid #cbd5e1;padding:4px 10px;margin:4px 0;color:var(--navy-2);font-size:.83rem;font-style:italic;}
.brand{font-weight:800;font-size:1.1rem;color:var(--navy);}
.brand span{background:linear-gradient(135deg,var(--blue),var(--violet));
  -webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;}
</style>"""
st.markdown(CSS, unsafe_allow_html=True)

DEMO_PROFILE: Dict[str, Any] = {
    "name": "Aarav Sharma", "college": "Indian Institute of Technology (BHU), Varanasi",
    "degree": "B.Tech", "branch": "Chemical Engineering", "year": 2, "cgpa": 8.2,
    "skills": ["Python", "Pandas", "Excel", "Thermodynamics", "Git", "SQL", "Data Visualization"],
    "interests": ["Data Science", "Machine Learning", "Chemical Engineering", "Research"],
    "work_mode": "Any", "location": "Any", "stipend": "Any", "experience": "Beginner",
    "gender": "Prefer not to say",
}

CAREER_GOALS = ["Industry job", "Higher studies", "Research", "Startup", "Undecided"]

# --------------------------------------------------------------------------- #
# i18n — hand-written static UI strings (dynamic text goes through Sarvam)
# --------------------------------------------------------------------------- #
UI: Dict[str, Dict[str, str]] = {
    "English": {
        "app_tagline": "Personal Opportunity Intelligence Platform",
        "radar": "Radar", "copilot": "Copilot", "tracker": "Tracker", "skills": "Skills & Gap",
        "whynot": "Why Not?", "assistant": "Assistant",
        "profile": "Your profile", "demo_profile": "Try Demo Profile",
        "career_goal": "Career goal", "demo_mode": "Demo Mode",
        "demo_note": "Sample deadlines are shown as illustrative dates.",
        "language": "Language", "filters": "Filters", "weights": "Matching weights",
        "category": "Category", "required_skill": "Required skill", "work_mode": "Work mode",
        "min_fit": "Minimum fit %", "show_all": "Show all",
        "apply_now": "Apply Now", "prepare_for": "Prepare For", "explore": "Explore",
        "excluded": "Excluded", "why_not": "Why Not?",
        "fit": "Fit", "eligible": "Eligible", "potentially": "Potentially Eligible",
        "ineligible": "Ineligible", "timing": "Timing", "verify": "Verify",
        "view_details": "View details", "save_tracker": "Save to Tracker", "ai_copilot": "AI Copilot",
        "why_matches": "Why this opportunity?", "improve_fit": "What could improve your fit",
        "eligibility_gates": "Eligibility gates", "breakdown": "Score breakdown",
        "counterfactual": "If you learn one skill", "next_action": "Next action",
        "matching_skills": "Matching skills", "missing_skills": "Missing skills",
        "learning_plan": "Prioritised learning plan", "roadmap": "12-week roadmap",
        "resume_upload": "Upload resume (PDF)", "consent": "I consent to sending redacted resume text to the AI service",
        "evidence": "Evidence Matrix", "prep_kit": "7-Day Prep Kit",
        "export_csv": "Export Radar as CSV", "delete_data": "Delete my data",
        "completeness": "Profile completeness", "strong_matches": "Strong matches",
        "analysed": "Opportunities analysed", "saved": "Tracked",
        "not_verified": "Not verified", "sample": "Sample data",
        "privacy": "Your resume stays on this machine unless you tick 'Remember my resume' and consent.",
        "translation_unavailable": "Translation unavailable",
        "stage": "Stage", "notes": "Notes", "history": "Stage history",
        "no_ai": "Sarvam AI is off — using the built-in engine and templates.",
        "ask_placeholder": "Ask about opportunities, skills or your profile…",
        "next_move": "Your Next Best Move",
        "next_move_desc": "One prioritised action, ranked by relevance × gap × confidence ÷ effort across your top targets.",
        "top_action": "Recommended action",
        "why": "Why",
        "pathway": "Pathway",
        "alternatives": "Other actions, ranked",
        "effort": "Estimated effort",
        "confidence": "Evidence confidence",
        "relevance": "Relevance",
        "gap": "Fit gap addressed",
        "info_quality": "Information quality",
        "info_note": "Completeness is how much of the record is stated. It is not a guarantee of legitimacy and is not part of your fit score.",
        "why_not_apply": "Why isn't this in Apply Now?",
        "disclaimer": "This is guidance based on your profile and the dataset — it is not a prediction of selection.",
    },
    "Hindi": {
        "app_tagline": "व्यक्तिगत अवसर इंटेलिजेंस प्लेटफ़ॉर्म",
        "radar": "रडार", "copilot": "कोपायलट", "tracker": "ट्रैकर", "skills": "कौशल व अंतराल",
        "whynot": "क्यों नहीं?", "assistant": "सहायक",
        "profile": "आपकी प्रोफ़ाइल", "demo_profile": "डेमो प्रोफ़ाइल आज़माएँ",
        "career_goal": "करियर लक्ष्य", "demo_mode": "डेमो मोड",
        "demo_note": "नमूना समय-सीमाएँ केवल उदाहरण के रूप में दिखाई जाती हैं।",
        "language": "भाषा", "filters": "फ़िल्टर", "weights": "मिलान भार",
        "category": "श्रेणी", "required_skill": "आवश्यक कौशल", "work_mode": "कार्य मोड",
        "min_fit": "न्यूनतम फ़िट %", "show_all": "सभी दिखाएँ",
        "apply_now": "अभी आवेदन करें", "prepare_for": "तैयारी करें", "explore": "खोजें",
        "excluded": "बाहर रखे गए", "why_not": "क्यों नहीं?",
        "fit": "फ़िट", "eligible": "पात्र", "potentially": "संभावित पात्र",
        "ineligible": "अपात्र", "timing": "समय", "verify": "जाँचें",
        "view_details": "विवरण देखें", "save_tracker": "ट्रैकर में सहेजें", "ai_copilot": "AI कोपायलट",
        "why_matches": "यह अवसर क्यों?", "improve_fit": "फ़िट कैसे बेहतर होगा",
        "eligibility_gates": "पात्रता शर्तें", "breakdown": "स्कोर विवरण",
        "counterfactual": "यदि एक कौशल सीखें", "next_action": "अगला कदम",
        "matching_skills": "मेल खाते कौशल", "missing_skills": "अनुपस्थित कौशल",
        "learning_plan": "प्राथमिकता सीखने की योजना", "roadmap": "12-सप्ताह का रोडमैप",
        "resume_upload": "रिज़्यूमे अपलोड करें (PDF)", "consent": "मैं संपादित रिज़्यूमे पाठ AI सेवा को भेजने की सहमति देता/देती हूँ",
        "evidence": "प्रमाण मैट्रिक्स", "prep_kit": "7-दिवसीय तैयारी किट",
        "export_csv": "रडार CSV निर्यात करें", "delete_data": "मेरा डेटा हटाएँ",
        "completeness": "प्रोफ़ाइल पूर्णता", "strong_matches": "मज़बूत मिलान",
        "analysed": "विश्लेषित अवसर", "saved": "ट्रैक किए गए",
        "not_verified": "सत्यापित नहीं", "sample": "नमूना डेटा",
        "privacy": "आपका रिज़्यूमे इस मशीन पर रहता है जब तक आप सहमति न दें।",
        "translation_unavailable": "अनुवाद उपलब्ध नहीं",
        "stage": "चरण", "notes": "टिप्पणियाँ", "history": "चरण इतिहास",
        "no_ai": "Sarvam AI बंद है — अंतर्निहित इंजन उपयोग हो रहा है।",
        "ask_placeholder": "अवसरों, कौशल या प्रोफ़ाइल के बारे में पूछें…",
        "next_move": "आपका अगला सर्वोत्तम कदम",
        "next_move_desc": "आपके शीर्ष लक्ष्यों पर प्रासंगिकता × अंतराल × विश्वास ÷ प्रयास के आधार पर एक प्राथमिक कदम।",
        "top_action": "अनुशंसित कदम",
        "why": "क्यों",
        "pathway": "मार्ग",
        "alternatives": "अन्य कदम, क्रम में",
        "effort": "अनुमानित प्रयास",
        "confidence": "प्रमाण विश्वास",
        "relevance": "प्रासंगिकता",
        "gap": "संबोधित फ़िट अंतराल",
        "info_quality": "सूचना गुणवत्ता",
        "info_note": "पूर्णता बताती है कि रिकॉर्ड में कितना कुछ दर्ज है। यह वैधता की गारंटी नहीं है और फ़िट स्कोर का हिस्सा नहीं है।",
        "why_not_apply": "यह 'अभी आवेदन करें' में क्यों नहीं है?",
        "disclaimer": "यह आपकी प्रोफ़ाइल और डेटासेट पर आधारित मार्गदर्शन है — चयन की भविष्यवाणी नहीं।",
    },
}

TIMING_BADGE = {"open": ("Open", "b-green"), "closing_soon": ("Closing soon", "b-amber"),
                "rolling": ("Rolling", "b-blue"), "not_yet_open": ("Opens later", "b-violet"),
                "closed": ("Closed", "b-red"), "unknown": ("Timing not verified", "b-grey")}


def init_state() -> None:
    ss = st.session_state
    ss.setdefault("profile", db.load_profile())
    ss.setdefault("radar", None)
    ss.setdefault("weights", dict(R.DEFAULT_WEIGHTS))
    ss.setdefault("demo_mode", True)
    ss.setdefault("lang", "English")
    ss.setdefault("career_goal", "Undecided")
    ss.setdefault("chat", [])
    ss.setdefault("resume_text", "")
    ss.setdefault("remember_resume", False)
    ss.setdefault("consent", False)
    ss.setdefault("evidence", None)
    ss.setdefault("prep_kit", None)
    ss.setdefault("tab", "Radar")


init_state()
db.init_db()

OPPS = R.load_opportunities()
KNOW = R.load_knowledge()
NOTICE = R.dataset_notice()
SYN = KNOW.get("skill_synonyms", {})
PLAYBOOK = KNOW.get("skill_playbook", {})
CLIENT = SarvamClient()
TODAY = R.today()


def t(key: str) -> str:
    return UI.get(st.session_state.lang, UI["English"]).get(key, UI["English"].get(key, key))


def dyn(text: str) -> str:
    """Translate dynamic text when a non-English language is active."""
    lang = st.session_state.lang
    if lang == "English" or not text:
        return text
    code = LANGUAGES.get(lang)
    if not code or not CLIENT.configured:
        return text
    out = CLIENT.translate(text, code)
    if out == text and CLIENT.last_error:
        return f"{text}\n\n_({t('translation_unavailable')})_"
    return out


# --------------------------------------------------------------------------- #
# Render helpers
# --------------------------------------------------------------------------- #
def esc(x: Any) -> str:
    return html.escape(str(x if x is not None else ""))


def badge(text: str, cls: str = "b-grey") -> str:
    return f'<span class="badge {cls}">{esc(text)}</span>'


def ring(pct: float, uid: str, size: int = 78, stroke: int = 8) -> str:
    pct = max(0.0, min(100.0, float(pct)))
    r = (size - stroke) / 2.0
    c = 2 * 3.14159265 * r
    off = c * (1 - pct / 100.0)
    gid = f"g_{uid}"
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">'
            f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="1">'
            f'<stop offset="0%" stop-color="#2563eb"/><stop offset="100%" stop-color="#7c3aed"/>'
            f'</linearGradient></defs>'
            f'<circle cx="{size/2}" cy="{size/2}" r="{r:.1f}" fill="none" stroke="#eaeff9" stroke-width="{stroke}"/>'
            f'<circle cx="{size/2}" cy="{size/2}" r="{r:.1f}" fill="none" stroke="url(#{gid})" '
            f'stroke-width="{stroke}" stroke-linecap="round" stroke-dasharray="{c:.1f}" '
            f'stroke-dashoffset="{off:.1f}" transform="rotate(-90 {size/2} {size/2})"/>'
            f'<text x="50%" y="50%" text-anchor="middle" dominant-baseline="central" font-size="19" '
            f'font-weight="800" fill="#0b1220">{pct:.0f}%</text></svg>')


COMP_LABELS = [("skill", "Skill"), ("interest", "Interest"), ("academic", "Academic"),
               ("workmode", "Work mode"), ("experience", "Experience")]


def comp_bars(components: Dict[str, float]) -> str:
    rows = ""
    for k, label in COMP_LABELS:
        v = max(0.0, min(100.0, components.get(k, 0.0)))
        rows += (f'<div class="cbrow"><div class="cblab">{esc(label)}</div>'
                 f'<div class="cbtrack"><span style="width:{v:.0f}%"></span></div>'
                 f'<div class="cbval">{v:.0f}%</div></div>')
    return rows


def completeness(p: Dict[str, Any]) -> int:
    if not p:
        return 0
    checks = [bool(p.get("name")), bool(p.get("college")), bool(p.get("degree")),
              bool(p.get("branch")), bool(p.get("year")), p.get("cgpa") is not None,
              bool(p.get("skills")), bool(p.get("interests")), bool(p.get("work_mode")),
              bool(p.get("experience"))]
    return round(100 * sum(checks) / len(checks))


def elig_badge(status: str) -> str:
    return {"Eligible": badge(t("eligible"), "b-green"),
            "Potentially Eligible": badge(t("potentially"), "b-amber"),
            "Ineligible": badge(t("ineligible"), "b-red")}.get(status, badge(status, "b-grey"))


def verif_badge(opp: Dict[str, Any]) -> str:
    v = opp.get("verification_status")
    if v == "closed":
        return badge("Closed", "b-red")
    if v == "verified":
        return badge(f"Verified {opp.get('last_verified') or ''}".strip(), "b-green")
    if v == "fetched":
        return badge(f"Fetched (not human-checked)", "b-amber")
    return badge(t("sample"), "b-amber")


def card_html(item: Dict[str, Any], uid_suffix: str = "") -> str:
    opp = item["opportunity"]
    sc = item["score"]
    fit = item.get("fit", sc["score_pct"])
    timing = item.get("timing", "unknown")
    tlabel, tcls = TIMING_BADGE.get(timing, ("Timing not verified", "b-grey"))
    elig = item.get("eligibility", {}).get("status", "Potentially Eligible")
    deadline = item.get("deadline")
    cat_cls = R.CATEGORY_BADGE.get(opp["category"], "b-grey")
    demo_b = badge("DEMO deadline", "b-violet") if (deadline and not opp.get("deadline")) else ""
    saved = opp["id"] in {a["opportunity_id"] for a in db.get_applications()}
    verify_chip = ""
    if elig == "Potentially Eligible" and item.get("eligibility", {}).get("verify"):
        verify_chip = badge(f"{t('verify')}: {item['eligibility']['verify'][0][:44]}", "b-amber")
    ic = R.information_completeness(opp)
    info_chip = badge(f"{t('info_quality')} {ic['completeness_pct']}%", "b-grey")

    matched = "".join(f'<span class="chip chip-have">{esc(m["skill"])}</span>'
                      for m in sc.get("matched", [])[:5])
    missing = "".join(f'<span class="chip chip-miss">{esc(s)}</span>' for s in sc.get("missing", [])[:5])

    return f"""
    <div class="card">
      <div style="display:flex;gap:14px;align-items:center;">
        <div style="flex:0 0 auto;">{ring(fit, uid=opp['id'] + uid_suffix)}</div>
        <div style="flex:1 1 auto;min-width:0;">
          <div class="opp-title">{esc(opp['title'])}</div>
          <div class="opp-org">{esc(opp['organization'])}</div>
          <div>{badge(opp['category'], cat_cls)} {badge(tlabel, tcls)} {elig_badge(elig)}
            {verif_badge(opp)} {info_chip} {demo_b} {badge(t('saved'), 'b-blue') if saved else ''}</div>
          <div style="margin-top:8px;">{verify_chip}</div>
        </div>
      </div>
      <div style="margin-top:8px;">{comp_bars(sc['components'])}</div>
      <div style="margin-top:8px;">{matched}{missing}</div>
      <div class="muted" style="margin-top:6px;">
        {t('fit')}: {fit:.0f}% · {t('next_action')}: {esc(item.get('next_action', ''))}
      </div>
    </div>"""


def csv_of_radar(radar: Dict[str, List[Dict[str, Any]]]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["pane", "id", "title", "organization", "category", "fit_pct", "required_coverage",
                "eligibility", "timing", "deadline", "verification_status", "missing_skills"])
    for pane in ("apply_now", "prepare_for", "explore", "excluded"):
        for it in radar.get(pane, []):
            o, sc = it["opportunity"], it["score"]
            w.writerow([pane, o["id"], o["title"], o["organization"], o["category"],
                        f"{it.get('fit', sc['score_pct']):.1f}", f"{sc['required_coverage']:.2f}",
                        it.get("eligibility", {}).get("status", ""), it.get("timing", ""),
                        it.get("deadline") or "", o.get("verification_status", ""),
                        "; ".join(sc.get("missing", []))])
    return buf.getvalue()


def compute_radar(force: bool = False) -> Dict[str, List[Dict[str, Any]]]:
    if force or st.session_state.radar is None:
        st.session_state.radar = R.build_radar(
            st.session_state.profile, OPPS, st.session_state.weights, TODAY,
            st.session_state.demo_mode, knowledge=KNOW)
    return st.session_state.radar


def apply_filters(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    f = st.session_state
    out = []
    for it in items:
        o, sc = it["opportunity"], it["score"]
        if f.get("f_cat", "All") != "All" and o["category"] != f["f_cat"]:
            continue
        if f.get("f_mode", "All") != "All" and o.get("work_mode") != f["f_mode"]:
            continue
        sk = f.get("f_skill", "Any")
        if sk != "Any" and sk not in (o.get("required_skills", []) + o.get("preferred_skills", [])):
            continue
        if it.get("fit", sc["score_pct"]) < f.get("f_min", 0):
            continue
        out.append(it)
    return out


def load_pdf(upload) -> tuple[str, Optional[str]]:
    """Return (text, error). Validates type, size, header and page count."""
    if upload is None:
        return "", None
    data = upload.getvalue()
    if len(data) > 5 * 1024 * 1024:
        return "", "File is larger than 5 MB."
    if not data[:5].startswith(b"%PDF"):
        return "", "That does not look like a PDF file."
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        if len(reader.pages) > 10:
            return "", f"PDF has {len(reader.pages)} pages; the limit is 10."
        text = "\n".join((pg.extract_text() or "") for pg in reader.pages)
    except Exception:
        return "", "Could not read that PDF."
    if len(text.strip()) < 40:
        return "", ("No selectable text found — this looks like a scanned PDF. "
                    "Please upload a text-based PDF.")
    return text, None


# --------------------------------------------------------------------------- #
# Header
# --------------------------------------------------------------------------- #
p = st.session_state.profile
radar = compute_radar()
all_items = radar["apply_now"] + radar["prepare_for"] + radar["explore"]

# Status strip values — all derived, nothing invented.
_verified_open = sum(1 for o in OPPS
                     if o.get("verification_status") == "verified"
                     and R.timing_status(o, TODAY, st.session_state.demo_mode) in ("open", "closing_soon", "rolling"))
_sample_count = sum(1 for o in OPPS if o.get("verification_status") == "sample")
_demo_state = 'On' if st.session_state.demo_mode else 'Off'

st.markdown(f"""
<div class="hero">
  <div class="kicker">OpportunityAI · Opportunity Intelligence</div>
  <h1>Discover opportunities. Build skills. Take your next step.</h1>
  <p>Internships, scholarships, hackathons, research programmes and competitions — matched to your
  skills, interests, academics and goals. Eligibility, timing and fit are kept as three separate
  facts, and every unknown field is labelled rather than invented.</p>
  <div class="statusstrip">
    <span class="pill">{esc(t('completeness'))}: {completeness(p)}%</span>
    <span class="pill">{esc(t('career_goal'))}: {esc(st.session_state.career_goal)}</span>
    <span class="pill">{esc(t('language'))}: {esc(st.session_state.lang)}</span>
    <span class="pill">{esc(t('demo_mode'))}: {esc(_demo_state)}</span>
  </div>
</div>""", unsafe_allow_html=True)

strong = R.strong_match_count(all_items)
h1, h2, h3, h4, h5 = st.columns([1, 1, 1, 1, 1.4])
with h1:
    st.markdown(f'<div class="metric"><div class="label">{esc(t("analysed"))}</div>'
                f'<div class="value">{len(OPPS)}</div>'
                f'<div class="sub">{_sample_count} sample · {len(OPPS) - _sample_count} closed/other</div></div>',
                unsafe_allow_html=True)
with h2:
    st.markdown(f'<div class="metric"><div class="label">{esc(t("strong_matches"))}</div>'
                f'<div class="value">{strong}</div><div class="sub">70% fit or higher</div></div>',
                unsafe_allow_html=True)
with h3:
    st.markdown(f'<div class="metric"><div class="label">Verified &amp; open</div>'
                f'<div class="value">{_verified_open}</div>'
                f'<div class="sub">human-checked records with a live window</div></div>',
                unsafe_allow_html=True)
with h4:
    st.markdown(f'<div class="metric"><div class="label">{esc(t("saved"))}</div>'
                f'<div class="value">{len(db.get_applications())}</div>'
                f'<div class="sub">in tracker</div></div>', unsafe_allow_html=True)
with h5:
    st.caption(t("privacy"))

# --------------------------------------------------------------------------- #
# Sidebar
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.markdown('<div class="brand">🎯 Opportunity<span>AI</span></div>', unsafe_allow_html=True)

    if st.button(f"⚡ {t('demo_profile')}", type="primary", width="stretch"):
        st.session_state.profile = dict(DEMO_PROFILE)
        db.save_profile(st.session_state.profile)
        compute_radar(force=True)
        st.rerun()

    with st.expander(f"📝 {t('profile')}", expanded=not bool(st.session_state.profile)):
        with st.form("profile_form"):
            pf = st.session_state.profile or {}
            name = st.text_input("Name", value=pf.get("name", ""))
            college = st.text_input("College", value=pf.get("college", ""))
            degree = st.selectbox("Degree", ["B.Tech", "B.E.", "B.Sc", "BCA", "MCA", "M.Tech",
                                             "M.Sc", "MBA", "B.Com", "Other"],
                                  index=(["B.Tech", "B.E.", "B.Sc", "BCA", "MCA", "M.Tech",
                                          "M.Sc", "MBA", "B.Com", "Other"].index(pf["degree"])
                                         if pf.get("degree") in ["B.Tech", "B.E.", "B.Sc", "BCA", "MCA",
                                                                 "M.Tech", "M.Sc", "MBA", "B.Com", "Other"] else 0))
            branch = st.text_input("Branch", value=pf.get("branch", ""))
            year = st.selectbox("Year", [1, 2, 3, 4, 5],
                                index=([1, 2, 3, 4, 5].index(pf["year"]) if pf.get("year") in [1, 2, 3, 4, 5] else 1))
            cgpa_raw = st.text_input("CGPA (0-10)", value=str(pf.get("cgpa", "")))
            experience = st.selectbox("Experience", ["Beginner", "Intermediate", "Advanced"],
                                      index=["Beginner", "Intermediate", "Advanced"].index(
                                          pf.get("experience", "Beginner")))
            gender = st.selectbox("Gender (optional)", ["Prefer not to say", "Female", "Male", "Other"],
                                  index=["Prefer not to say", "Female", "Male", "Other"].index(
                                      pf.get("gender", "Prefer not to say")))
            work_mode = st.selectbox("Work mode", ["Any", "Remote", "On-site", "Hybrid"],
                                     index=["Any", "Remote", "On-site", "Hybrid"].index(pf.get("work_mode", "Any")))
            location = st.text_input("Location", value=pf.get("location", "Any"))
            skills = st.multiselect("Skills", R.MASTER_SKILLS, default=pf.get("skills", []))
            interests = st.multiselect("Interests", R.INTEREST_OPTIONS, default=pf.get("interests", []))
            if st.form_submit_button("🔍 Find My Opportunities", type="primary", width="stretch"):
                bad = False
                try:
                    cgpa = R.parse_cgpa(cgpa_raw)
                except ValueError as exc:
                    st.error(f"Invalid CGPA: {exc}")
                    cgpa, bad = None, True
                if not bad:
                    st.session_state.profile = {
                        "name": name.strip(), "college": college.strip(), "degree": degree,
                        "branch": branch.strip(), "year": year, "cgpa": cgpa, "skills": skills,
                        "interests": interests, "work_mode": work_mode, "location": location.strip() or "Any",
                        "stipend": "Any", "experience": experience, "gender": gender}
                    db.save_profile(st.session_state.profile)
                    compute_radar(force=True)
                    st.rerun()

    st.divider()
    st.session_state.career_goal = st.selectbox(t("career_goal"), CAREER_GOALS,
                                                index=CAREER_GOALS.index(st.session_state.career_goal))
    st.session_state.demo_mode = st.toggle(t("demo_mode"), value=st.session_state.demo_mode)
    if st.session_state.demo_mode:
        st.caption(t("demo_note"))
    lang = st.selectbox(t("language"), list(UI.keys()),
                        index=list(UI.keys()).index(st.session_state.lang))
    if lang != st.session_state.lang:
        st.session_state.lang = lang
        st.rerun()

    with st.expander(f"⚙️ {t('weights')}"):
        w = st.session_state.weights
        w["skill"] = st.slider("Skill", 0, 100, int(w["skill"] * 100)) / 100
        w["interest"] = st.slider("Interest", 0, 100, int(w["interest"] * 100)) / 100
        w["academic"] = st.slider("Academic", 0, 100, int(w["academic"] * 100)) / 100
        w["workmode"] = st.slider("Work mode", 0, 100, int(w["workmode"] * 100)) / 100
        w["experience"] = st.slider("Experience", 0, 100, int(w["experience"] * 100)) / 100
        if st.button("Reset weights", width="stretch"):
            st.session_state.weights = dict(R.DEFAULT_WEIGHTS)
            compute_radar(force=True)
            st.rerun()

    with st.expander(f"🔎 {t('filters')}", expanded=True):
        st.session_state.f_cat = st.selectbox(t("category"), ["All"] + R.CATEGORY_ORDER)
        all_skills = sorted({s for o in OPPS for s in o.get("required_skills", []) + o.get("preferred_skills", [])})
        st.session_state.f_skill = st.selectbox(t("required_skill"), ["Any"] + all_skills)
        st.session_state.f_mode = st.selectbox(t("work_mode"), ["All", "Remote", "On-site", "Hybrid"])
        st.session_state.f_min = st.slider(t("min_fit"), 0, 100, 0, 5)

    with st.expander(f"📄 {t('resume_upload')}"):
        up = st.file_uploader("PDF", type=["pdf"], label_visibility="collapsed")
        st.session_state.consent = st.checkbox(t("consent"), value=st.session_state.consent)
        st.session_state.remember_resume = st.checkbox("Remember my resume (this machine only)",
                                                       value=st.session_state.remember_resume)
        if up is not None:
            text, err = load_pdf(up)
            if err:
                st.error(err)
            else:
                st.session_state.resume_text = text
                st.success(f"Loaded {len(text)} characters.")
        if st.session_state.resume_text:
            st.caption(f"Resume in session: {len(st.session_state.resume_text)} chars.")

    st.divider()
    st.download_button(f"⬇️ {t('export_csv')}", data=csv_of_radar(radar),
                       file_name="opportunityai_radar.csv", mime="text/csv", width="stretch")
    if st.button(f"🗑️ {t('delete_data')}", width="stretch"):
        db.wipe_all()
        st.session_state.profile = {}
        st.session_state.resume_text = ""
        st.session_state.evidence = None
        st.session_state.prep_kit = None
        compute_radar(force=True)
        st.success("Local data deleted.")
        st.rerun()

    if CLIENT.configured:
        st.success("Sarvam AI: connected")
    else:
        st.caption(t("no_ai"))

# --------------------------------------------------------------------------- #
# Tabs
# --------------------------------------------------------------------------- #
tabs = st.tabs([f"🎯 {t('radar')}", f"🚀 {t('next_move')}", f"🤖 {t('copilot')}",
                f"📋 {t('tracker')}", f"🧠 {t('skills')}", f"🚫 {t('whynot')}",
                f"💬 {t('assistant')}"])
tab_radar, tab_nextmove, tab_copilot, tab_tracker, tab_skills, tab_whynot, tab_assistant = tabs

# ------------------------------- RADAR ------------------------------------- #
with tab_radar:
    if not st.session_state.profile:
        st.info("Set your profile in the sidebar, or press **Try Demo Profile**.")
    compact = st.toggle("Compact view (tabs instead of columns)", value=False)

    panes = [("apply_now", t("apply_now")), ("prepare_for", t("prepare_for")), ("explore", t("explore"))]
    filtered = {k: apply_filters(radar[k]) for k, _ in panes}

    if compact:
        sub = st.tabs([f"{label} ({len(filtered[k])})" for k, label in panes])
        containers = [(c, k, label) for c, (k, label) in zip(sub, panes)]
    else:
        cols = st.columns(3)
        containers = [(cols[i], k, label) for i, (k, label) in enumerate(panes)]

    for container, key, label in containers:
        with container:
            items = filtered[key]
            cap = R.RADAR_THRESHOLDS["explore_max"] if key == "explore" else None
            shown = items[:cap] if cap else items
            st.markdown(f'<div class="section-title"><span class="dot"></span>{esc(label)} '
                        f'({len(items)})</div>', unsafe_allow_html=True)
            if cap and len(items) > cap:
                st.caption(f"Showing {cap} of {len(items)}.")
            if not shown:
                st.caption("Nothing in this pane with the current filters.")
            for it in shown:
                st.markdown(card_html(it, uid_suffix=key), unsafe_allow_html=True)
                b1, b2 = st.columns(2)
                with b1:
                    if st.button(f"{t('view_details')}", key=f"d_{key}_{it['opportunity']['id']}",
                                 width="stretch"):
                        st.session_state["detail_id"] = it["opportunity"]["id"]
                        st.rerun()
                with b2:
                    if st.button(f"➕ {t('save_tracker')}", key=f"s_{key}_{it['opportunity']['id']}",
                                 width="stretch"):
                        db.set_stage(it["opportunity"]["id"], "Shortlisted")
                        st.toast(f"Added {it['opportunity']['id']} to the tracker.")
                        st.rerun()

    did = st.session_state.get("detail_id")
    if did:
        it = next((x for x in all_items if x["opportunity"]["id"] == did), None)
        if it:
            st.divider()
            st.markdown(f"### {it['opportunity']['title']}")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f'<div class="section-title"><span class="dot"></span>{esc(t("why_matches"))}</div>',
                            unsafe_allow_html=True)
                st.markdown(comp_bars(it["score"]["components"]), unsafe_allow_html=True)
                if it["score"]["matched"]:
                    st.markdown("**" + t("matching_skills") + ":** " + "".join(
                        f'<span class="chip chip-have">{esc(m["skill"])}'
                        f'{" (synonym)" if m["via"] == "synonym" else ""}'
                        f'{" (similar)" if m["via"] == "similar" else ""}</span>'
                        for m in it["score"]["matched"]), unsafe_allow_html=True)
                if it["score"]["missing"]:
                    st.markdown("**" + t("missing_skills") + ":** " + "".join(
                        f'<span class="chip chip-miss">{esc(s)}</span>' for s in it["score"]["missing"]),
                        unsafe_allow_html=True)
                cf = R.counterfactuals(st.session_state.profile, it["opportunity"],
                                       st.session_state.weights, SYN)
                if cf:
                    st.markdown(f'<div class="section-title"><span class="dot"></span>'
                                f'{esc(t("counterfactual"))}</div>', unsafe_allow_html=True)
                    for c in cf:
                        st.markdown(f"- Learn **{c['skill']}**: {c['before_pct']}% → "
                                    f"**{c['after_pct']}%** (+{c['delta']} pts)")
            with c2:
                st.markdown(f'<div class="section-title"><span class="dot"></span>'
                            f'{esc(t("eligibility_gates"))}</div>', unsafe_allow_html=True)
                gate_rows = [{"Gate": g["gate"], "Result": g["status"], "Detail": g["detail"]}
                             for g in it["eligibility"]["gates"]]
                st.dataframe(gate_rows, width="stretch", hide_index=True)
                st.markdown(f"**{t('timing')}:** {TIMING_BADGE.get(it['timing'], ('unknown', ''))[0]}"
                            + (f" · deadline {it['deadline']}" if it.get("deadline") else ""))
                if it["score"].get("unconfirmed"):
                    st.markdown("**" + t("not_verified") + ":**")
                    for u in it["score"]["unconfirmed"]:
                        st.markdown(f"- {u}")

                st.markdown(f'<div class="section-title"><span class="dot"></span>'
                            f'{esc(t("info_quality"))}</div>', unsafe_allow_html=True)
                ic = R.information_completeness(it["opportunity"])
                st.markdown("".join(
                    badge(f"{name}: {'stated' if ok else 'not stated'}", "b-green" if ok else "b-grey")
                    for name, ok in ic["fields"].items()), unsafe_allow_html=True)
                st.caption(f"{ic['label']}: {ic['completeness_pct']}% "
                           f"({ic['present_count']}/{ic['total']} fields stated) · "
                           f"{'human-verified' if ic['human_verified'] else 'not human-verified'}. "
                           + ic["note"])

            if it["timing"] not in ("open", "closing_soon", "rolling") or \
                    it["required_coverage"] < R.RADAR_THRESHOLDS["apply_min_coverage"] or \
                    it["fit"] < R.RADAR_THRESHOLDS["apply_min_fit"] or \
                    it["eligibility"]["status"] == "Potentially Eligible":
                st.markdown(f'<div class="section-title"><span class="dot"></span>'
                            f'{esc(t("why_not_apply"))}</div>', unsafe_allow_html=True)
                st.dataframe([{"Check": r["check"], "Status": r["status"],
                               "Detail": r["detail"], "Next": r["action"]}
                              for r in R.why_not_apply_now(it, KNOW)],
                             width="stretch", hide_index=True)
                if st.button("🤖 Explain this match", key=f"ex_{did}"):
                    with st.spinner("Generating…"):
                        out = CLIENT.explain_match(st.session_state.profile, it["score"])
                    st.session_state[f"exp_{did}"] = out
                cached = st.session_state.get(f"exp_{did}")
                if cached:
                    st.info(dyn(cached["text"]))
                    st.caption("Source: Sarvam AI" if cached["source"] == "ai" else "Source: built-in template")

# ----------------------------- NEXT MOVE ----------------------------------- #
with tab_nextmove:
    st.markdown(f"## 🚀 {t('next_move')}")
    st.caption(t("next_move_desc"))
    if not st.session_state.profile:
        st.info("Set your profile first — press **Try Demo Profile**.")
    else:
        actions = R.action_priority(st.session_state.profile, OPPS, st.session_state.weights,
                                    TODAY, KNOW, st.session_state.demo_mode, target_n=5)
        if not actions:
            st.success("Nothing to improve — you already cover the required skills for your top targets.")
        else:
            top = actions[0]
            st.markdown(f"""
            <div class="card" style="border-left:5px solid #2563eb;">
              <div class="muted" style="text-transform:uppercase;letter-spacing:.08em;font-weight:700;">
                {esc(t('top_action'))}</div>
              <div style="font-size:1.35rem;font-weight:800;margin:6px 0 4px;">Learn {esc(top['skill'])}</div>
              <div class="small">{esc(dyn(top['why']))}</div>
            </div>""", unsafe_allow_html=True)

            m1, m2, m3, m4 = st.columns(4)
            for col, label, val, sub in (
                    (m1, t("effort"), f"{top['hours']}h", "estimate"),
                    (m2, t("gap"), f"+{top['gap']:.1f}", "points on average"),
                    (m3, t("relevance"), f"{top['opportunities_lifted']}", "targets affected"),
                    (m4, t("confidence"), f"{top['confidence']:.2f}", "source weight")):
                with col:
                    st.markdown(f'<div class="metric"><div class="label">{esc(label)}</div>'
                                f'<div class="value">{esc(val)}</div>'
                                f'<div class="sub">{esc(sub)}</div></div>', unsafe_allow_html=True)

            c1, c2 = st.columns([1, 1])
            with c1:
                st.markdown(f'<div class="section-title"><span class="dot"></span>{esc(t("pathway"))}</div>',
                            unsafe_allow_html=True)
                for step in R.pathway(top):
                    st.markdown(f"**{step['stage']}** — {esc(step['detail'])}")
            with c2:
                st.markdown(f'<div class="section-title"><span class="dot"></span>'
                            f'{esc(t("alternatives"))}</div>', unsafe_allow_html=True)
                st.dataframe([{"Action": f"Learn {a['skill']}", "Priority": round(a["priority"], 3),
                               "Hours": a["hours"], "Avg gain": f"+{a['gap']:.1f}",
                               "Targets": a["opportunities_lifted"]} for a in actions],
                             width="stretch", hide_index=True)

            if top.get("needs_verification"):
                st.warning("One of the affected opportunities is only *Potentially Eligible* — "
                           "confirm its eligibility before investing time.")
            st.caption(t("disclaimer"))

# ------------------------------ COPILOT ------------------------------------ #
with tab_copilot:
    st.markdown("## AI Application Copilot")
    st.caption("Everything below is built deterministically first. AI only refines prose — a quote that "
               "is not found verbatim in your resume is discarded.")
    ids = [x["opportunity"]["id"] for x in all_items] or [o["id"] for o in OPPS]
    label_map = {x["opportunity"]["id"]: x["opportunity"]["title"] for x in all_items}
    label_map.update({o["id"]: o["title"] for o in OPPS})
    pick = st.selectbox("Opportunity", ids, format_func=lambda i: f"{label_map.get(i, i)}")
    opp = next(o for o in OPPS if o["id"] == pick)
    sc = R.score_opportunity(st.session_state.profile, opp, st.session_state.weights, SYN)

    resume_text = st.session_state.resume_text
    if not resume_text:
        st.warning("Upload a PDF resume in the sidebar to build the Evidence Matrix. "
                   "You can still see the deterministic structure below.")

    if st.button("🔍 Build Evidence Matrix", type="primary"):
        rows = R.evidence_matrix(resume_text, opp, SYN)
        if resume_text and st.session_state.consent and CLIENT.configured:
            with st.spinner("Refining with Sarvam AI…"):
                rows = CLIENT.refine_evidence(resume_text, rows)
        st.session_state.evidence = rows

    rows = st.session_state.evidence
    if rows is not None:
        st.markdown(f'<div class="section-title"><span class="dot"></span>{esc(t("evidence"))}</div>',
                    unsafe_allow_html=True)
        if not resume_text:
            st.caption("No resume loaded — every row shows 'No evidence'.")
        for r in rows:
            cls = {"Demonstrated": "b-green", "Listed only": "b-amber", "No evidence": "b-grey"}.get(r["label"], "b-grey")
            st.markdown(f"**{esc(r['requirement'])}** {badge(r['label'], cls)} "
                        f"{badge(r.get('section', ''), 'b-grey')}"
                        + (" " + badge("AI-refined", "b-violet") if r.get("refined") == "ai" else ""),
                        unsafe_allow_html=True)
            if r.get("quote"):
                st.markdown(f'<div class="q">{esc(r["quote"])}</div>', unsafe_allow_html=True)

    if st.button(f"🧰 Generate {t('prep_kit')}"):
        kit = R.prep_kit_template(st.session_state.profile, resume_text, opp, KNOW, SYN)
        if resume_text and st.session_state.consent and CLIENT.configured:
            with st.spinner("Generating with Sarvam AI…"):
                kit = CLIENT.generate_prep_kit(st.session_state.profile, resume_text, opp)
        st.session_state.prep_kit = kit

    kit = st.session_state.prep_kit
    if kit:
        st.divider()
        st.markdown(f'<div class="section-title"><span class="dot"></span>{esc(t("prep_kit"))}</div>',
                    unsafe_allow_html=True)
        st.markdown("**Resume checklist**")
        for c in kit["resume_checklist"]:
            st.markdown(f"- {c}")
        st.markdown("**Interview topics**")
        for c in kit["interview_topics"]:
            st.markdown(f"- {c}")
        st.markdown("**7-day plan**")
        st.dataframe([{"Day": d["day"], "Focus": d["focus"], "Hours": d["hours"],
                       "Tasks": " · ".join(d["tasks"]), "Output": d["output"]} for d in kit["plan"]],
                     width="stretch", hide_index=True)
        st.caption(kit["note"])
        if st.button(f"➕ {t('save_tracker')}", key="copilot_track"):
            db.set_stage(opp["id"], "Preparing")
            st.success("Saved to the tracker as 'Preparing'.")

# ------------------------------ TRACKER ------------------------------------ #
with tab_tracker:
    st.markdown("## Application Tracker")
    st.caption("Stored locally in SQLite. Persists across restarts. Stages follow the funnel.")
    apps = db.get_applications()
    if not apps:
        st.info("Nothing tracked yet. Use **Save to Tracker** on a Radar card or in the Copilot.")
    else:
        for a in apps:
            opp = next((o for o in OPPS if o["id"] == a["opportunity_id"]), None)
            title = opp["title"] if opp else a["opportunity_id"]
            st.markdown(f"**{esc(title)}** — `{esc(a['stage'])}`")
            c1, c2, c3 = st.columns([2, 3, 1])
            with c1:
                new_stage = st.selectbox("Stage", db.STAGES, index=db.STAGES.index(a["stage"]),
                                         key=f"st_{a['opportunity_id']}", label_visibility="collapsed")
            with c2:
                note = st.text_input("Notes", value=a.get("notes", ""),
                                     key=f"nt_{a['opportunity_id']}", label_visibility="collapsed")
            with c3:
                if st.button("Update", key=f"up_{a['opportunity_id']}", width="stretch"):
                    db.set_stage(a["opportunity_id"], new_stage, note)
                    st.rerun()
            hist = db.get_stage_history(a["opportunity_id"])
            if hist:
                st.caption(" → ".join(h["to_stage"] for h in hist))

        st.divider()
        st.markdown(f'<div class="section-title"><span class="dot"></span>Funnel</div>', unsafe_allow_html=True)
        counts: Dict[str, int] = {}
        for h in db.get_stage_history():
            counts[h["to_stage"]] = counts.get(h["to_stage"], 0) + 1
        if counts:
            for stage in db.STAGES:
                if stage in counts:
                    st.markdown(f"- **{stage}**: {counts[stage]}")
        else:
            st.caption("No stage changes recorded yet.")

# --------------------------- SKILLS & GAP ---------------------------------- #
with tab_skills:
    st.markdown("## Skills & Gap")
    if not st.session_state.profile:
        st.info("Set your profile first.")
    else:
        pool = all_items or []
        if not pool:
            st.info("No eligible opportunities yet.")
        else:
            labels = {x["opportunity"]["id"]: f"{x['opportunity']['title']} ({x['fit']:.0f}%)" for x in pool}
            default_ids = [x["opportunity"]["id"] for x in pool[:3]]
            picked = st.multiselect("Analyse against", list(labels.keys()), default=default_ids,
                                    format_func=lambda i: labels[i])
            chosen = [x for x in pool if x["opportunity"]["id"] in picked]
            gap = R.skill_gap(st.session_state.profile, chosen, KNOW)
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f'<div class="section-title"><span class="dot"></span>'
                            f'{esc(t("matching_skills"))}</div>', unsafe_allow_html=True)
                st.markdown("".join(f'<span class="chip chip-have">{esc(s)}</span>'
                                    for s in gap["matching_skills"]) or "None yet.", unsafe_allow_html=True)
            with c2:
                st.markdown(f'<div class="section-title"><span class="dot"></span>'
                            f'{esc(t("missing_skills"))}</div>', unsafe_allow_html=True)
                st.markdown("".join(f'<span class="chip chip-miss">{esc(s)}</span>'
                                    for s in gap["missing_skills"]) or "No gaps.", unsafe_allow_html=True)

            st.divider()
            st.markdown(f'<div class="section-title"><span class="dot"></span>'
                        f'{esc(t("learning_plan"))}</div>', unsafe_allow_html=True)
            if gap["learning_plan"]:
                st.dataframe([{"Priority": x["priority"], "Skill": x["skill"],
                               "Practice project": x["practice_project"],
                               "Resource type": x["resource_type"]} for x in gap["learning_plan"]],
                             width="stretch", hide_index=True)
            st.markdown(f'<div class="section-title"><span class="dot"></span>{esc(t("roadmap"))}</div>',
                        unsafe_allow_html=True)
            for line in R.build_roadmap(gap["learning_plan"]):
                st.markdown(f"- {line}")

            st.divider()
            st.markdown('<div class="section-title"><span class="dot"></span>Track your skill progress</div>',
                        unsafe_allow_html=True)
            states = db.get_skill_states()
            if gap["missing_skills"]:
                sk = st.selectbox("Skill", gap["missing_skills"])
                cur = states.get(sk, {}).get("state", "Not Started")
                new_state = st.radio("State", db.SKILL_STATES, index=db.SKILL_STATES.index(cur),
                                     horizontal=True)
                note = st.text_input("Evidence note", value=states.get(sk, {}).get("evidence_note", ""))
                if st.button("Save skill state"):
                    db.set_skill_state(sk, new_state, note)
                    st.success(f"{sk}: {new_state}")
            if states:
                st.dataframe([{"Skill": k, "State": v["state"], "Note": v["evidence_note"]}
                              for k, v in states.items()], width="stretch", hide_index=True)

# ------------------------------ WHY NOT ------------------------------------ #
with tab_whynot:
    st.markdown("## Why Not?")
    st.caption("Excluded from the Radar, with the exact reason. An unverified field is never a failure — "
               "only a stated requirement that is not met, or a closed deadline.")
    if not radar["excluded"]:
        st.success("Nothing is excluded for this profile.")
    for it in radar["excluded"]:
        o = it["opportunity"]
        st.markdown(f"""
        <div class="card">
          <div class="opp-title">{esc(o['title'])}</div>
          <div class="opp-org">{esc(o['organization'])}</div>
          <div>{badge(o['category'], R.CATEGORY_BADGE.get(o['category'], 'b-grey'))}
            {elig_badge(it['eligibility']['status'])}
            {badge(TIMING_BADGE.get(it['timing'], ('unknown', ''))[0],
                   TIMING_BADGE.get(it['timing'], ('unknown', 'b-grey'))[1])}
            {verif_badge(o)}</div>
          <div class="small" style="margin-top:8px;"><b>Reason:</b> {esc(it['reason'])}</div>
          <div class="muted" style="margin-top:4px;"><b>What would help:</b> {esc(it['fix'])}</div>
        </div>""", unsafe_allow_html=True)
        with st.expander("Eligibility gates"):
            st.dataframe([{"Gate": g["gate"], "Result": g["status"], "Detail": g["detail"]}
                          for g in it["eligibility"]["gates"]], width="stretch", hide_index=True)

# ----------------------------- ASSISTANT ----------------------------------- #
with tab_assistant:
    st.markdown("## Assistant")
    if CLIENT.configured:
        st.caption("Sarvam AI is connected. Answers use your profile and the local dataset as context.")
    else:
        st.caption("Built-in assistant (no API key). It answers from your profile and the local dataset — "
                   "it has not searched the internet.")

    if not st.session_state.chat:
        st.session_state.chat = [{"role": "assistant", "content":
            "Ask me: 'Which opportunities are best for my profile?', 'What should I learn?', "
            "'Show beginner-friendly options', or 'Opportunities for a second-year student'."}]

    for turn in st.session_state.chat:
        with st.chat_message(turn["role"]):
            st.markdown(turn["content"])

    q = st.chat_input(t("ask_placeholder"))
    if q:
        st.session_state.chat.append({"role": "user", "content": q})
        with st.chat_message("user"):
            st.markdown(q)
        results = all_items
        ctx = [f"Profile: {st.session_state.profile}",
               f"Radar apply_now: {[x['opportunity']['title'] for x in radar['apply_now']]}",
               f"prepare_for: {[x['opportunity']['title'] for x in radar['prepare_for']]}",
               "Dataset is illustrative sample data; no verified deadlines or links; no internet search."]
        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                ai = CLIENT.answer_question(q, "\n".join(ctx), st.session_state.chat)
            if ai["text"]:
                ans, src = ai["text"], "Sarvam AI"
            else:
                ans = local_answer(q, st.session_state.profile, results, OPPS)
                src = "built-in assistant"
            st.markdown(ans)
            st.caption(f"Source: {src}")
        st.session_state.chat.append({"role": "assistant", "content": ans})

    if st.button("Clear chat"):
        st.session_state.chat = []
        st.rerun()

st.divider()
st.caption(NOTICE)
