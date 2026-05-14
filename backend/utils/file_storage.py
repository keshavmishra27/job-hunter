import os
import shutil
from pathlib import Path
from backend.config import get_settings

settings = get_settings()


def save_file(content: bytes, subdir: str, filename: str) -> str:
    target = Path(settings.storage_dir) / subdir
    target.mkdir(parents=True, exist_ok=True)
    dest = target / filename
    dest.write_bytes(content)
    return str(dest)


def delete_file(path: str):
    p = Path(path)
    if p.exists():
        p.unlink()
