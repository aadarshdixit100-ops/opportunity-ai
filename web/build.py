"""build.py — inline data + css + engine + app into a single self-contained index.html."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
# The project root is the parent directory when web/ lives inside the project,
# otherwise a sibling "opportunity-ai" folder (development layout).
_P = os.path.dirname(HERE)
PROJ = _P if os.path.isdir(os.path.join(_P, "data")) else os.path.join(_P, "opportunity-ai")
OUT = os.path.join(PROJ, "index.html")


def read(p):
    with open(p, "r", encoding="utf-8") as fh:
        return fh.read()


def main():
    opps = json.load(open(os.path.join(PROJ, "data", "opportunities.json"), encoding="utf-8"))
    know = json.load(open(os.path.join(PROJ, "data", "knowledge.json"), encoding="utf-8"))

    data_js = "const DATA = " + json.dumps({
        "opportunities": opps["opportunities"],
        "knowledge": {
            "skill_synonyms": know["skill_synonyms"],
            "skill_playbook": know["skill_playbook"],
            "domain_bridges": know["domain_bridges"],
        },
        "notice": opps["_meta"]["important_notice"],
    }, ensure_ascii=False) + ";"

    html = read(os.path.join(HERE, "template.html"))
    html = html.replace("/*__CSS__*/", read(os.path.join(HERE, "styles.css")))
    html = html.replace("/*__DATA__*/", data_js)
    html = html.replace("/*__ENGINE__*/", read(os.path.join(HERE, "engine.js")))
    html = html.replace("/*__APP__*/", read(os.path.join(HERE, "app.js")))

    # sanity: no unresolved placeholders, no leftover citation markers
    for token in ("__CSS__", "__DATA__", "__ENGINE__", "__APP__"):
        assert token not in html, "unresolved placeholder " + token
    assert "[cite:" not in html, "citation marker leaked into the file"

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(html)
    print("wrote", OUT, len(html), "bytes")


if __name__ == "__main__":
    main()
