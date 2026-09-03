#!/usr/bin/env python3
"""Safely add a sticker locally, either by URL or by copying an image into media/."""

from __future__ import annotations

import argparse
import mimetypes
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from laopo_sticker_mcp.config import Settings  # noqa: E402
from laopo_sticker_mcp.models import Sticker  # noqa: E402
from laopo_sticker_mcp.repository import StickerRepository  # noqa: E402

ALLOWED_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


def csv_list(value: str) -> list[str]:
    items = [item.strip() for item in value.replace("，", ",").split(",") if item.strip()]
    if not items:
        raise argparse.ArgumentTypeError("至少填写一项")
    return items


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Add one sticker to stickers.json")
    result.add_argument("--id", required=True)
    result.add_argument("--name", required=True)
    source = result.add_mutually_exclusive_group(required=True)
    source.add_argument("--url", help="Existing public HTTPS image URL")
    source.add_argument("--file", type=Path, help="Local image copied into media/")
    result.add_argument("--tags", required=True, type=csv_list, help="Comma-separated")
    result.add_argument("--emotion", required=True, type=csv_list, help="Comma-separated")
    result.add_argument("--description", required=True)
    result.add_argument("--usage", required=True)
    return result


def main() -> None:
    args = parser().parse_args()
    settings = Settings.from_env()
    repository = StickerRepository(settings.stickers_file, settings.public_base_url)

    image_url = args.url
    copied_path: Path | None = None
    if args.file:
        source = args.file.expanduser().resolve()
        if not source.is_file():
            raise SystemExit(f"图片文件不存在：{source}")
        suffix = source.suffix.lower()
        if suffix not in ALLOWED_SUFFIXES:
            guessed = mimetypes.guess_type(source.name)[0]
            raise SystemExit(f"不支持的图片格式：{suffix or guessed or '未知'}")
        settings.media_dir.mkdir(parents=True, exist_ok=True)
        copied_path = settings.media_dir / f"{args.id}{suffix}"
        if copied_path.exists():
            raise SystemExit(f"目标图片已存在：{copied_path}")
        shutil.copy2(source, copied_path)
        image_url = f"${{PUBLIC_BASE_URL}}/media/{copied_path.name}"

    sticker = Sticker(
        id=args.id,
        name=args.name,
        image_url=image_url,
        tags=args.tags,
        description=args.description,
        emotion=args.emotion,
        usage=args.usage,
    )
    try:
        repository.add(sticker)
    except Exception:
        if copied_path is not None:
            copied_path.unlink(missing_ok=True)
        raise
    view = repository.to_view(sticker)
    print(f"Added {view.id}: {view.name}")
    print(view.image_url)
    print(view.markdown)


if __name__ == "__main__":
    main()
