"""
test_ui_theme.py — regression tests for the contrast defect.

The bug: app.py painted its own LIGHT backgrounds while Streamlit's theme was
left at "auto". On a dark-preferring machine Streamlit set light text (#FAFAFA)
high in the tree, so tab labels, sidebar labels and captions became invisible
against the light surfaces the app had painted.

Root causes, each pinned by a test below:
  1. no .streamlit/config.toml  -> theme.base stayed "auto"
  2. a `[class*="css"]` selector that matches nothing in Streamlit 1.66,
     so the intended `color:` never applied
  3. no explicit colour on the containers whose background the app repaints
  4. primary-button markers differ across Streamlit versions
"""

import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
APP = os.path.join(ROOT, "app.py")
CONFIG = os.path.join(ROOT, ".streamlit", "config.toml")


def _strip_comments(css: str) -> str:
    """Comments explain the fix and legitimately mention the dead selector."""
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def _css(strip_comments: bool = True) -> str:
    src = open(APP, encoding="utf-8").read()
    m = re.search(r'CSS = """(.*?)"""', src, re.S)
    assert m, "CSS block not found in app.py"
    return _strip_comments(m.group(1)) if strip_comments else m.group(1)


# --------------------------------------------------------------------------- #
def test_theme_config_exists_and_pins_light():
    assert os.path.exists(CONFIG), ".streamlit/config.toml is missing — theme.base would stay 'auto'"
    cfg = open(CONFIG, encoding="utf-8").read()
    assert re.search(r'^\s*base\s*=\s*"light"', cfg, re.M), "theme.base must be pinned to 'light'"
    for key in ("primaryColor", "backgroundColor", "textColor"):
        assert key in cfg, f"theme.{key} should be set explicitly"


def test_dead_class_selector_is_gone():
    """[class*="css"] was a pre-emotion Streamlit hack; it matches nothing now."""
    assert '[class*="css"]' not in _css(strip_comments=True), (
        'the dead [class*="css"] selector is back — it silently fails to set the text colour')


def test_explicit_text_colour_on_painted_containers():
    css = _css()
    # containers whose background the app controls must also set colour
    for sel in (".stApp", '[data-testid="stAppViewContainer"]'):
        assert sel in css, f"{sel} should be styled"
    m = re.search(r'\.stApp[^{]*\{([^}]*)\}', css)
    assert m and "color" in m.group(1), ".stApp must set an explicit text colour"
    # sidebar: background AND colour
    sb = re.search(r'section\[data-testid="stSidebar"\]\{([^}]*)\}', css)
    assert sb and "background" in sb.group(1), "sidebar background should be styled"
    assert 'section[data-testid="stSidebar"] label' in css, "sidebar labels need an explicit colour"
    assert '[data-testid="stSidebar"] [data-testid="stWidgetLabel"]' in css, \
        "sidebar widget labels need an explicit colour"


def test_tabs_are_coloured_defensively():
    css = _css()
    assert '.stTabs [data-baseweb="tab"]' in css, "tabs need a baseweb selector"
    assert '[role="tab"]' in css, (
        "tabs need a defensive [role=tab] rule — Streamlit has shipped more than one tab markup")


def test_primary_button_covers_both_markers():
    css = _css()
    assert 'button[kind="primary"]' in css
    assert 'stBaseButton-primary' in css, (
        "newer Streamlit marks primary buttons with data-testid=stBaseButton-primary; "
        "without it the label renders dark-on-gradient")


def test_no_global_white_text_rule():
    """A blanket white-text rule would break every light surface."""
    css = _css()
    offenders = []
    for sel, body in re.findall(r"([^{}]+)\{([^}]*)\}", css):
        sel = sel.strip().split("\n")[-1].strip()
        if re.search(r"color\s*:\s*(#fff\b|#ffffff\b|white)\b", body, re.I):
            if sel in ("*", "html", "body", ".stApp", ":root") or sel.endswith(", *"):
                offenders.append(sel)
    assert not offenders, f"blanket white text on {offenders}"


def test_muted_text_has_accessible_contrast():
    """Muted slate on white must clear WCAG AA for small text (>= 4.5:1)."""
    css = _css()
    m = re.search(r"--muted:\s*(#[0-9a-fA-F]{6})", css)
    assert m, "--muted should be a hex colour"
    hexv = m.group(1).lstrip("#")
    r, g, b = (int(hexv[i:i + 2], 16) / 255 for i in (0, 2, 4))

    def lin(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    L = 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)
    contrast = (1.0 + 0.05) / (L + 0.05)   # against white
    assert contrast >= 4.5, f"--muted {m.group(1)} has only {contrast:.2f}:1 on white"
