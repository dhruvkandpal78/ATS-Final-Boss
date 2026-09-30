"""Resolve public runtime resources in checkouts and installed distributions."""
from importlib.metadata import PackageNotFoundError, distribution
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NOTICES = {"LICENSE", "LICENSE-MIT-LEGACY.txt"}


def notice_path(name: str) -> Path:
    if name not in NOTICES:
        raise ValueError("Unknown public notice")
    local = ROOT / name
    if local.is_file():
        return local
    try:
        installed = distribution("ats-final-boss")
    except PackageNotFoundError:
        raise FileNotFoundError("Public notice is unavailable") from None
    for entry in installed.files or ():
        if (entry.name == name and len(entry.parts) >= 3 and
                entry.parts[-2] == "licenses" and entry.parts[-3].endswith(".dist-info")):
            path = Path(installed.locate_file(entry))
            if path.is_file():
                return path
    raise FileNotFoundError("Public notice is unavailable")


def models_directory() -> Path:
    value = os.environ.get("ATS_MODELS_DIR")
    if value is None:
        return ROOT / "results" / "models"
    if not value.strip():
        raise ValueError("ATS_MODELS_DIR must identify an approved model directory")
    return Path(value).expanduser()
