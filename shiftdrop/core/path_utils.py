"""
Path Utilities: Non-destructive path generation and filename safety.
Prevents accidental overwrites of existing files by generating Windows-standard 'name (1).ext'.
"""
from pathlib import Path

def get_unique_target_path(target_path: Path | str) -> Path:
    """
    Returns a unique file path so that existing files are never overwritten.
    If 'report.pdf' exists, generates 'report (1).pdf', 'report (2).pdf', etc.
    """
    p = Path(target_path)
    if not p.exists():
        return p

    parent = p.parent
    stem = p.stem
    suffix = p.suffix
    counter = 1

    while True:
        candidate = parent / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1
