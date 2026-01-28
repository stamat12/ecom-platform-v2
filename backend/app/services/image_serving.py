from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image

import sys
LEGACY = Path(__file__).resolve().parents[2] / "legacy"
sys.path.insert(0, str(LEGACY))
import config  # type: ignore


_ALLOWED_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
# allow common Windows filenames: spaces and parentheses are allowed
_SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9._() -]+$")

# Where cached thumbs will be stored (inside backend/app/.cache by default)
CACHE_ROOT = Path(__file__).resolve().parents[1] / ".cache" / "thumbs"


def _image_base_dirs() -> list[Path]:
    env_dirs = os.getenv("IMAGE_BASE_DIRS")
    if env_dirs:
        return [Path(p.strip()) for p in env_dirs.split(";") if p.strip()]

    bases = getattr(config, "IMAGE_FOLDER_PATHS", [])
    return [Path(p) for p in bases]


def _validate_parts(sku: str, filename: str) -> None:
    # SKU: allow typical forms like JAL00022, but don't over-restrict
    if not sku or not _SAFE_NAME_RE.match(sku):
        raise ValueError("Invalid sku")

    if not filename or not _SAFE_NAME_RE.match(filename):
        raise ValueError("Invalid filename")

    ext = Path(filename).suffix.lower()
    if ext not in _ALLOWED_EXTS:
        raise ValueError("Unsupported file extension")


def _find_original_image_path(sku: str, filename: str) -> Optional[Path]:
    for base in _image_base_dirs():
        candidate = base / sku / filename
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def _variant_to_size(variant: str) -> Optional[Tuple[int, int]]:
    # Return (max_w, max_h) for thumbs, None means original.
    if variant in ("original", "", None):
        return None
    if variant == "thumb_256":
        return (256, 256)
    if variant == "thumb_512":
        return (512, 512)
    # You can extend variants here.
    raise ValueError("Unsupported variant")


def _cache_path_for(original: Path, sku: str, filename: str, variant: str) -> Path:
    # Cache: CACHE_ROOT/<variant>/<sku>/<filename>.jpg (or keep ext)
    # Keeping original ext is fine; we’ll write in same format when possible.
    return CACHE_ROOT / variant / sku / filename


def ensure_thumbnail(original_path: Path, sku: str, filename: str, variant: str) -> Path:
    size = _variant_to_size(variant)
    if size is None:
        return original_path

    cached = _cache_path_for(original_path, sku, filename, variant)

    # Regenerate if cache missing or older than original
    if cached.exists() and cached.stat().st_mtime >= original_path.stat().st_mtime:
        return cached

    cached.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(original_path) as im:
        im = im.convert("RGB") if im.mode in ("P", "RGBA") else im
        im.thumbnail(size, Image.LANCZOS)

        # Save thumbnail
        # If original is PNG/WebP, saving as same ext is ok, but JPEG is often smaller/faster.
        # Here we preserve ext to keep it simple.
        ext = original_path.suffix.lower()
        if ext in (".jpg", ".jpeg"):
            im.save(cached, format="JPEG", quality=85, optimize=True)
        elif ext == ".png":
            im.save(cached, format="PNG", optimize=True)
        elif ext == ".webp":
            im.save(cached, format="WEBP", quality=85, method=6)
        else:
            # Should not happen due to validation
            im.save(cached)

    return cached


def resolve_image_path(sku: str, filename: str, variant: str) -> Path:
    _validate_parts(sku, filename)

    original = _find_original_image_path(sku, filename)
    if not original:
        raise FileNotFoundError("Image not found")

    return ensure_thumbnail(original, sku, filename, variant)
