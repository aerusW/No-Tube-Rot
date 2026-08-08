"""Build a release archive of No-Tube-Rot.

The file list comes from manifest.json (via checks.referenced_files) rather than
from a hardcoded list or a "copy everything except..." filter. That is a
deliberate choice, and it is the fix for issue #1.

Chrome writes a generated `_metadata/` directory into any folder it loads as an
unpacked extension. Underscore-prefixed names are reserved in the extension
format, so a Firefox package containing one is rejected outright — which is why
the extension appeared not to work in Firefox for months when the real problem
was that the folder had been used for Chrome first. An allowlist cannot pick up
`_metadata/`, or `.git/`, or anything else that happens to be lying around; a
denylist has to be remembered.

Produces:

    dist/staging/                     the exact tree that ships
    dist/no-tube-rot-<version>.zip    that tree, zipped

The staging directory is kept because the release workflow signs *it* rather
than the repository root, for the same reason: web-ext's own ignore rules are a
denylist.

Run:  python .github/scripts/package.py
"""
import json
import pathlib
import shutil
import sys
import zipfile

# Importing checks.py would otherwise leave a __pycache__/ directory in the
# repository — another reserved underscore-prefixed name, in the folder people
# load as a temporary add-on. Given what this script exists to prevent, don't
# create one.
sys.dont_write_bytecode = True
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from checks import referenced_files  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
DIST = ROOT / "dist"
STAGING = DIST / "staging"

# Files that ship but that the manifest has no reason to point at.
ALWAYS = ["manifest.json", "LICENSE"]


def main() -> int:
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    version = manifest["version"]
    files = ALWAYS + referenced_files(manifest)

    missing = [rel for rel in files if not (ROOT / rel).exists()]
    if missing:
        print("Refusing to package, these files are missing:")
        for rel in missing:
            print(f"  - {rel}")
        return 1

    if DIST.exists():
        shutil.rmtree(DIST)
    STAGING.mkdir(parents=True)

    for rel in files:
        dest = STAGING / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, dest)

    archive = DIST / f"no-tube-rot-{version}.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in sorted(files):
            z.write(STAGING / rel, rel)

    print(f"Packaged {len(files)} files at version {version}")
    for rel in sorted(files):
        print(f"  {rel}")
    print(f"\n  {archive.relative_to(ROOT)}  ({archive.stat().st_size / 1024:.1f} KB)")
    print(f"  {STAGING.relative_to(ROOT)}/  (for web-ext sign)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
