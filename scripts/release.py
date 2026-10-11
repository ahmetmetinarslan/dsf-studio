"""Package the tested Windows build and sources, excluding local tools and secrets."""
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.0.0"
EVIDENCE = (
    "stage1/results.json", "acceptance/results.json", "acceptance/K01_ffprobe.json",
    "acceptance/stress100.json", "acceptance/extra.json", "acceptance/preview_six.json",
    "acceptance/color_reference.json", "gui/results.json",
    "package-check/package-check.json", "hardware.json",
)


def portable_value(value):
    """Remove this machine's workspace prefix without changing measured values."""
    if isinstance(value, str):
        return value.replace(str(ROOT), "<workspace>").replace(ROOT.as_posix(), "<workspace>")
    if isinstance(value, list):
        return [portable_value(item) for item in value]
    if isinstance(value, dict):
        return {key: portable_value(item) for key, item in value.items()}
    return value


def archive(path, files, relative):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for source in sorted(files):
            z.write(source, relative(source))
    with zipfile.ZipFile(path) as z:
        invalid = z.testzip()
        if invalid:
            raise RuntimeError(f"Bozuk ZIP girdisi: {invalid}")
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"file": path.name, "bytes": path.stat().st_size, "sha256": digest}


def main():
    release = ROOT / "release"
    release.mkdir(exist_ok=True)
    package = ROOT / "dist" / "DSF-Studio"
    if not (package / "DSF-Studio.exe").is_file():
        raise SystemExit("Önce scripts/build_windows.py ile Windows paketini oluşturun.")

    for relative in EVIDENCE:
        target = ROOT / "test-evidence" / relative
        source = ROOT / "artifacts" / relative
        if not source.is_file():
            source = target
        data = portable_value(json.loads(source.read_text(encoding="utf-8-sig")))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf8")

    for name in ("README.md", "TEST_RESULTS.md", "THIRD_PARTY_NOTICES.md", "RELEASE_NOTES.md"):
        shutil.copy2(ROOT / name, package / name)
    for name in ("docs", "test-evidence"):
        shutil.copytree(ROOT / name, package / name, dirs_exist_ok=True)

    package_files = [p for p in package.rglob("*") if p.is_file()]
    manifest = [archive(release / f"DSF-Studio-{VERSION}-Windows-x64.zip", package_files,
                        lambda p: p.relative_to(package.parent).as_posix())]
    source_files = []
    for folder in ("dsf", "scripts", "tests", "examples", "licenses", "docs", "test-evidence"):
        source_files.extend(p for p in (ROOT / folder).rglob("*")
                            if p.is_file() and "__pycache__" not in p.parts)
    source_files.extend(p for p in ROOT.iterdir()
                        if p.is_file() and p.suffix in (".md", ".txt", ".lock", ".py", ".cmd"))
    source_files.extend([ROOT / ".gitignore", ROOT / ".gitattributes",
                         ROOT / "BUILD_INFO.json", ROOT / "tools" / "README.md"])
    manifest.append(archive(release / f"DSF-Studio-{VERSION}-Source.zip", set(source_files),
                            lambda p: "DSF-Studio-source/" + p.relative_to(ROOT).as_posix()))
    (release / "SHA256.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf8")
    print(json.dumps(manifest, indent=2), flush=True)


if __name__ == "__main__":
    main()
