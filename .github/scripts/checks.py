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
SHIPPED_JSON = ["manifest.json", "rules.json"]
ISSUE_FORMS = ".github/ISSUE_TEMPLATE"
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
    r = subprocess.run(["git", *args], capture_output=True, text=True,
                       encoding="utf-8", cwd=ROOT)
    return r.stdout.strip() if r.returncode == 0 else None


def check_json() -> dict:
    print("\nJSON parses")
    manifest = {}
    for name in SHIPPED_JSON:
        path = ROOT / name
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            ok(name)
            if name == "manifest.json":
                manifest = data
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
    referenced = list(manifest.get("icons", {}).values())
    for entry in manifest.get("content_scripts", []):
        referenced += entry.get("css", []) + entry.get("js", [])
    for res in manifest.get("declarative_net_request", {}).get("rule_resources", []):
        referenced.append(res.get("path", ""))
    for rel in referenced:
        if rel and not (ROOT / rel).exists():
            fail(f"manifest.json references missing file: {rel}")
    if not failures:
        ok(f"{len(referenced)} referenced files all exist")

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


def check_debug_leftovers() -> None:
    print("\nNo debug leftovers in shipped code")
    for name in ("content.js",):
        text = (ROOT / name).read_text(encoding="utf-8")
        for pattern in ("console.log", "debugger"):
            if pattern in text:
                fail(f"{name} contains '{pattern}'")
        else:
            ok(name)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", help="ref to compare the version against")
    args = ap.parse_args()

    manifest = check_json()
    version = check_manifest(manifest)
    check_yaml()
    if version:
        check_changelog(version)
        if args.base:
            check_version_bump(version, args.base)
    check_debug_leftovers()

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
