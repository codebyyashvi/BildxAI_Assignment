"""ZIP submission script.

Creates candidate-name-bildx-image-ad.zip in the current directory,
excluding everything listed in the assignment's 'Do not include' section:
  .env files, API keys, node_modules, virtual environments, model weights,
  build caches, customer information, unrelated generated files.

Usage:
    python scripts/make_submission_zip.py [candidate-name]
"""
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

EXCLUDE_DIRS = {
    "node_modules",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".git",
    "dist",          # frontend build artefact (Docker builds it fresh)
    "build",
    ".tox",
    "coverage",
    ".eggs",
}

EXCLUDE_FILES = {
    ".env",          # secrets
    ".DS_Store",
    "Thumbs.db",
    "*.pyc",
    "*.pyo",
}

EXCLUDE_EXTENSIONS = {".pyc", ".pyo", ".pyd", ".so", ".egg"}

# Keep sample-output.png but skip the bulk of storage/output_ads
SKIP_PATHS_CONTAINING = [
    "storage/output_ads",
    "storage\\output_ads",
    "backend/.venv",
    "backend\\.venv",
]


def should_include(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    parts = rel.parts

    # Exclude any directory component in the exclude list
    for part in parts[:-1]:
        if part in EXCLUDE_DIRS:
            return False

    # Exclude by extension
    if path.suffix in EXCLUDE_EXTENSIONS:
        return False

    # Exclude .env (but not .env.example)
    if path.name == ".env":
        return False

    # Skip bulk storage but keep sample-output.png
    rel_str = str(rel).replace("\\", "/")
    for skip in SKIP_PATHS_CONTAINING:
        skip_norm = skip.replace("\\", "/")
        if rel_str.startswith(skip_norm):
            return False

    return True


def make_zip(candidate_name: str) -> Path:
    zip_name = f"{candidate_name}-bildx-image-ad.zip"
    zip_path = ROOT / zip_name

    added = 0
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
        for path in sorted(ROOT.rglob("*")):
            if path.is_file() and should_include(path, ROOT):
                arc_name = path.relative_to(ROOT)
                zf.write(path, arc_name)
                added += 1

    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"Created {zip_path.name}")
    print(f"  {added} files, {size_mb:.1f} MB")
    return zip_path


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "candidate"
    make_zip(name)
