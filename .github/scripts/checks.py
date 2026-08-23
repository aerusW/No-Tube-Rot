"""Repository checks for No-Tube-Rot.

Enforces the things that are easy to get wrong by hand: that the shipped JSON
parses, that the issue forms are valid YAML, and that the versioning rules in
CONTRIBUTING.md are actually followed.

Run it locally exactly as CI does:

    python .github/scripts/checks.py

Pass --base <ref> to also check the version-bump rules against that ref (CI
passes the pull request base, or the previous commit on a push).
"""
import argparse
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
ISSUE_FORMS = ".github/ISSUE_TEMPLATE"
HTML_ASSET_RE = re.compile(r"""(?:href|src)\s*=\s*["']([^"']+)["']""", re.I)
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
CHANGELOG_HEADING = re.compile(r"^## (\d+\.\d+\.\d+) — (\d{4}-\d{2}-\d{2})\s*$", re.M)

failures: list[str] = []
notes: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"  FAIL  {msg}")


def ok(msg: str) -> None:
    print(f"  ok    {msg}")


def git(*args: str) -> str | None:
    """git output, or None if the command failed or git isn't installed."""
    try:
        r = subprocess.run(["git", *args], capture_output=True, text=True,
                           encoding="utf-8", cwd=ROOT)
    except OSError:
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def local_assets(html: str) -> list[str]:
    """The local files an HTML page loads, from its href/src attributes.

    The manifest can name options.html, but it has no way to know that page
    pulls in options.css and options.js — and a release archive built without
    them ships a menu that opens blank. Absolute URLs and fragments are
    ignored; nothing shipped here loads anything remote, and this is the check
    that would notice if something started to.
    """
    found = HTML_ASSET_RE.findall(html)
    return [rel for rel in found
            if not re.match(r"(?:[a-z]+:|//|#|/)", rel, re.I)]


def referenced_files(manifest: dict, root: pathlib.Path | None = None) -> list[str]:
    """Every file the extension needs, as repo-relative paths.

    Shared with package.py, which uses it as the allowlist for what goes into a
    release archive. Keeping one definition means a new manifest key can never
    be validated here but silently left out of the package — or the reverse.

    Referenced HTML pages are followed one level into the assets they load, so
    the menu's stylesheet and script are part of the allowlist without the
    manifest having to repeat them.
    """
    root = ROOT if root is None else root
    referenced = list(manifest.get("icons", {}).values())
    for entry in manifest.get("content_scripts", []):
        referenced += entry.get("css", []) + entry.get("js", [])
    for res in manifest.get("declarative_net_request", {}).get("rule_resources", []):
        referenced.append(res.get("path", ""))

    action = manifest.get("action", {})
    referenced.append(action.get("default_popup", ""))
    referenced += list(action.get("default_icon", {}).values())
    referenced.append(manifest.get("options_ui", {}).get("page", ""))

    for rel in [r for r in referenced if r.endswith(".html")]:
        path = root / rel
        if path.exists():
            referenced += local_assets(path.read_text(encoding="utf-8"))

    # Deduplicate, keeping first-seen order so the packaging output is stable.
    return list(dict.fromkeys(rel for rel in referenced if rel))


def check_json() -> dict:
    """manifest.json, plus every rule file it registers.

    The ruleset list is read from the manifest rather than hardcoded: the
    redirects are one ruleset each so they can be switched on independently,
    and a new one must not be able to arrive unparsed.
    """
    print("\nJSON parses")
    manifest = {}
    try:
        manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        ok("manifest.json")
    except Exception as exc:
        fail(f"manifest.json: {exc}")
        return manifest

    for res in manifest.get("declarative_net_request", {}).get("rule_resources", []):
        name = res.get("path", "")
        try:
            json.loads((ROOT / name).read_text(encoding="utf-8"))
            ok(name)
        except Exception as exc:
            fail(f"{name}: {exc}")
    return manifest


def check_manifest(manifest: dict) -> str:
    print("\nManifest")
    if not manifest:
        return ""
    for field in ("manifest_version", "name", "version", "description",
                  "icons", "permissions", "content_scripts"):
        if field not in manifest:
            fail(f"manifest.json is missing '{field}'")
    # every file the manifest points at must exist
    referenced = referenced_files(manifest)
    missing = [rel for rel in referenced if not (ROOT / rel).exists()]
    for rel in missing:
        fail(f"manifest.json references missing file: {rel}")
    if not missing:
        ok(f"{len(referenced)} referenced files all exist")

    # 2.0's promise, enforced rather than remembered: a fresh install applies
    # nothing. A ruleset registered enabled would redirect people who never
    # asked for it, and it is a one-word edit away at all times.
    resources = manifest.get("declarative_net_request", {}).get("rule_resources", [])
    enabled = [r.get("id") for r in resources if r.get("enabled")]
    if enabled:
        fail(f"ruleset(s) registered enabled: {', '.join(enabled)}. Every "
             "redirect must ship off and be switched on from the menu.")
    elif resources:
        ok(f"{len(resources)} rulesets, all registered disabled")

    version = manifest.get("version", "")
    if not VERSION_RE.match(version):
        fail(f"version '{version}' is not MAJOR.MINOR.PATCH "
             "(see CONTRIBUTING.md#versioning-and-releases)")
    else:
        ok(f"version {version} is three-component")
    return version


def check_yaml() -> None:
    print("\nIssue forms are valid YAML")
    try:
        import yaml
    except ImportError:
        notes.append("PyYAML not installed — skipped issue form validation")
        print("  skip  PyYAML not installed")
        return
    for path in sorted((ROOT / ISSUE_FORMS).glob("*.yml")):
        try:
            yaml.safe_load(path.read_text(encoding="utf-8"))
            ok(path.name)
        except Exception as exc:
            fail(f"{path.name}: {exc}")


def check_changelog(version: str) -> None:
    print("\nChangelog")
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    headings = CHANGELOG_HEADING.findall(text)
    if not headings:
        fail("no '## X.Y.Z — YYYY-MM-DD' headings found in CHANGELOG.md")
        return
    newest = headings[0][0]
    if newest != version:
        fail(f"newest CHANGELOG entry is {newest} but manifest.json says "
             f"{version}; they must match")
    else:
        ok(f"newest entry {newest} matches the manifest")

    seen = [h[0] for h in headings]
    if len(seen) != len(set(seen)):
        dupes = {v for v in seen if seen.count(v) > 1}
        fail(f"duplicate CHANGELOG entries for: {', '.join(sorted(dupes))}")
    else:
        ok(f"{len(seen)} entries, no duplicates")


def check_version_bump(version: str, base: str) -> None:
    """If this change bumps the version, the new one must not already be tagged."""
    print(f"\nVersion bump (against {base})")
    previous = git("show", f"{base}:manifest.json")
    if previous is None:
        print(f"  skip  could not read manifest.json at {base}")
        return
    try:
        old = json.loads(previous).get("version", "")
    except Exception:
        print(f"  skip  manifest.json at {base} does not parse")
        return

    if old == version:
        ok(f"version unchanged at {version} (docs-only changes need no bump)")
        return

    tag = f"v{version}"
    tagged = git("rev-list", "-n", "1", tag)
    head = git("rev-parse", "HEAD")
    if tagged and tagged != head:
        fail(f"version bumped {old} -> {version}, but tag {tag} already exists "
             f"at {tagged[:7]}. Never reuse a released version.")
    else:
        ok(f"version bumped {old} -> {version}, {tag} is free")


def check_debug_leftovers(manifest: dict) -> None:
    """Every shipped script, not just the one that used to be the only one."""
    print("\nNo debug leftovers in shipped code")
    scripts = [rel for rel in referenced_files(manifest) if rel.endswith(".js")]
    for name in scripts:
        text = (ROOT / name).read_text(encoding="utf-8")
        found = [p for p in ("console.log", "debugger") if p in text]
        for pattern in found:
            fail(f"{name} contains '{pattern}'")
        if not found:
            ok(name)


def check_reserved_names() -> None:
    """Nothing in the tree should start with an underscore.

    Firefox rejects an extension containing reserved underscore-prefixed names
    outright, which is what made the add-on look broken for months (issue #1).
    Chrome writes `_metadata/` into any folder it loads unpacked and Python
    writes `__pycache__/`, so this is a live hazard in a working tree rather
    than a theoretical one.

    Ignored paths are a warning, not a failure: they are generated by whatever
    the developer happens to be running, they cannot reach a release (packages
    are built from an allowlist), and loading this folder unpacked in Chrome is
    a documented, supported thing to do. The warning is still worth printing,
    because while one is there this folder will not load in Firefox at all.
    A path git does *not* ignore is a repository bug, and fails.
    """
    print("\nNo reserved underscore-prefixed names in the tree")
    skip = {".git", "dist"}
    found = set()
    for path in ROOT.rglob("*"):
        rel = path.relative_to(ROOT)
        if rel.parts[0] in skip:
            continue
        for i, part in enumerate(rel.parts):
            if part.startswith("_"):
                found.add("/".join(rel.parts[:i + 1]))
                break

    in_git = git("rev-parse", "--git-dir") is not None
    for name in sorted(found):
        ignored = not in_git or git("check-ignore", "--quiet", name) is not None
        if ignored:
            notes.append(f"{name} is present — this folder will not load in "
                         "Firefox until it is deleted")
            print(f"  warn  {name} (ignored, but Firefox will reject this folder)")
        else:
            fail(f"{name} is committed; Firefox rejects reserved "
                 "underscore-prefixed names")
    if not found:
        ok("nothing Firefox would reject")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", help="ref to compare the version against")
    args = ap.parse_args()

    # Module-level, so that a second call in the same process (the tests do
    # this) starts from a clean slate rather than inheriting a verdict.
    failures.clear()
    notes.clear()

    manifest = check_json()
    version = check_manifest(manifest)
    check_yaml()
    if version:
        check_changelog(version)
        if args.base:
            check_version_bump(version, args.base)
    check_debug_leftovers(manifest)
    check_reserved_names()

    print()
    for note in notes:
        print(f"note: {note}")
    if failures:
        print(f"\n{len(failures)} check(s) failed:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
