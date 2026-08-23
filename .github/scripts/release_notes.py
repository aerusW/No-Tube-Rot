"""Print one version's section of CHANGELOG.md, for use as GitHub release notes.

CONTRIBUTING.md's release steps say to publish the notes from the changelog
section rather than writing them twice. This does that mechanically, so the
release body and the changelog cannot drift apart.

Run:  python .github/scripts/release_notes.py 1.3.5
"""
import pathlib
import sys

# No __pycache__/ in the repository — see the note in package.py.
sys.dont_write_bytecode = True
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from checks import CHANGELOG_HEADING  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]


def notes_for(version: str) -> str | None:
    """The body under '## <version> — <date>', up to the next version heading."""
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    matches = list(CHANGELOG_HEADING.finditer(text))
    for i, m in enumerate(matches):
        if m.group(1) != version:
            continue
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        return text[m.end():end].strip()
    return None


def main() -> int:
    # CHANGELOG.md is UTF-8, and a Windows console defaults to a legacy code
    # page that cannot encode much of it — a warning callout in a release note
    # would otherwise crash this script with a UnicodeEncodeError, on the one
    # machine a contributor is told to rehearse a release from. CI already runs
    # UTF-8, so this is for everybody else.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    if len(sys.argv) != 2:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    version = sys.argv[1]
    body = notes_for(version)
    if body is None:
        print(f"No CHANGELOG.md section found for {version}", file=sys.stderr)
        return 1
    print(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
