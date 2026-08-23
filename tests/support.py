"""Shared helpers for the No-Tube-Rot test suite.

Nothing here is a test. It holds the three things the test modules keep
needing: access to the repository's own files, a way to import the helper
scripts under `.github/scripts/`, and a builder for throwaway fixture
repositories so the scripts can be pointed at a tree that is deliberately
broken.

No third-party imports — the suite runs on a bare standard library, the same
way the extension ships with no dependencies.
"""
import importlib
import json
import pathlib
import re
import sys

# __pycache__/ is a reserved underscore-prefixed name, and Firefox rejects any
# extension folder containing one (issue #1). The suite must never leave one
# behind in a repository people load unpacked, so refuse to write bytecode as
# early as possible — tests/run.py sets this too, for anyone who reaches the
# test modules through `python -m unittest` instead.
sys.dont_write_bytecode = True

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / ".github" / "scripts"

# The files that make up the extension itself, as opposed to the repository
# around it. Several tests assert on this set rather than on a glob, so that
# adding a shipped file is a deliberate act with a test to update.
SHIPPED = [
    "manifest.json",
    "rules/redirect-home.json",
    "rules/redirect-shorts-feed.json",
    "rules/shorts-as-video.json",
    "settings.js",
    "content.js",
    "hide-shorts.css",
    "calm.css",
    "options.html",
    "options.css",
    "options.js",
]


def load_script(name: str):
    """Import one of the helper scripts in .github/scripts as a module."""
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    return importlib.import_module(name)


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def read_json(rel: str):
    return json.loads(read(rel))


def manifest() -> dict:
    return read_json("manifest.json")


def rulesets() -> dict[str, list]:
    """Every registered ruleset, keyed by id, in manifest order.

    The redirects are one ruleset each so the menu can switch them on
    independently, so there is no single rules file to read any more.
    """
    resources = manifest()["declarative_net_request"]["rule_resources"]
    return {res["id"]: read_json(res["path"]) for res in resources}


def rules() -> list:
    """Every rule from every ruleset, flattened."""
    return [rule for group in rulesets().values() for rule in group]


# ---- CSS ----------------------------------------------------------------
# A full CSS parser is out of scope; these stylesheets are a flat list of
# `selectors { declarations }` blocks with no at-rules and no nesting, so
# splitting them is enough to assert on structure. If a stylesheet ever grows
# an @media block, css_rules() raises rather than quietly mis-parsing it.

COMMENT_RE = re.compile(r"/\*.*?\*/", re.S)


def strip_comments(css: str) -> str:
    return COMMENT_RE.sub("", css)


def css_rules(css: str) -> list[tuple[str, str]]:
    """[(selector text, declaration text)] for every block in a stylesheet."""
    body = strip_comments(css)
    if "@" in body:
        raise AssertionError("css_rules() does not understand at-rules")
    if body.count("{") != body.count("}"):
        raise AssertionError("unbalanced braces in stylesheet")
    out = []
    for block in body.split("}"):
        if not block.strip():
            continue
        selectors, _, declarations = block.partition("{")
        out.append((selectors.strip(), declarations.strip()))
    return out


def declarations(block: str) -> list[tuple[str, str]]:
    """[(property, value)] for one declaration block."""
    out = []
    for decl in block.split(";"):
        if not decl.strip():
            continue
        prop, _, value = decl.partition(":")
        out.append((prop.strip(), value.strip()))
    return out


# ---- Colour -------------------------------------------------------------

def _channel(value: float) -> float:
    value /= 255
    return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_colour: str) -> float:
    """WCAG 2.1 relative luminance of an #rrggbb colour."""
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def contrast_ratio(a: str, b: str) -> float:
    """WCAG 2.1 contrast ratio between two #rrggbb colours, 1.0 to 21.0."""
    la, lb = relative_luminance(a), relative_luminance(b)
    lighter, darker = max(la, lb), min(la, lb)
    return (lighter + 0.05) / (darker + 0.05)


# ---- Fixture repositories ----------------------------------------------

FIXTURE_MANIFEST = {
    "manifest_version": 3,
    "name": "Fixture",
    "version": "1.0.0",
    "description": "A throwaway extension used by the tests.",
    "icons": {"16": "icons/icon-16.png"},
    "permissions": ["declarativeNetRequest", "storage"],
    "host_permissions": ["*://www.youtube.com/*"],
    "action": {"default_popup": "options.html"},
    "options_ui": {"page": "options.html", "open_in_tab": False},
    "declarative_net_request": {
        # Registered enabled, like the real thing: checks.py fails a tree that
        # ships a redirect switched off.
        "rule_resources": [
            {"id": "redirect-home", "enabled": True,
             "path": "rules/redirect-home.json"}
        ]
    },
    "content_scripts": [
        {
            "matches": ["*://www.youtube.com/*"],
            "css": ["calm.css"],
            "js": ["settings.js", "content.js"],
            "run_at": "document_start",
        }
    ],
}

# Deliberately references two files the manifest never names. referenced_files()
# has to reach them by reading this page, or a release ships a menu that opens
# blank.
FIXTURE_OPTIONS_HTML = """<!doctype html>
<title>Fixture</title>
<link rel="stylesheet" href="options.css">
<script src="options.js"></script>
"""

FIXTURE_CHANGELOG = """# Changelog

## 1.0.0 — 2026-01-01

### Added

* The first version.
"""


def build_fixture(root: pathlib.Path, *, version: str = "1.0.0",
                  changelog: str | None = None, content_js: str = "// nothing\n",
                  drop: tuple[str, ...] = ()) -> pathlib.Path:
    """Write a minimal, valid extension tree into `root`.

    `drop` names referenced files to leave out, for the tests that check the
    scripts notice missing files.
    """
    data = json.loads(json.dumps(FIXTURE_MANIFEST))
    data["version"] = version
    (root / "manifest.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    rules_dir = root / "rules"
    rules_dir.mkdir(parents=True, exist_ok=True)
    (rules_dir / "redirect-home.json").write_text("[]", encoding="utf-8")
    (root / "LICENSE").write_text("MIT\n", encoding="utf-8")
    (root / "CHANGELOG.md").write_text(
        FIXTURE_CHANGELOG if changelog is None else changelog, encoding="utf-8")

    written = {
        "content.js": content_js.encode("utf-8"),
        "settings.js": b"// nothing\n",
        "calm.css": b"html { color: red; }\n",
        "icons/icon-16.png": b"\x89PNG\r\n\x1a\n",
        "options.html": FIXTURE_OPTIONS_HTML.encode("utf-8"),
        "options.css": b"body { margin: 0; }\n",
        "options.js": b"// nothing\n",
    }
    for rel, blob in written.items():
        if rel in drop:
            continue
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(blob)

    forms = root / ".github" / "ISSUE_TEMPLATE"
    forms.mkdir(parents=True, exist_ok=True)
    (forms / "bug_report.yml").write_text("name: Bug\nbody: []\n", encoding="utf-8")
    return root
