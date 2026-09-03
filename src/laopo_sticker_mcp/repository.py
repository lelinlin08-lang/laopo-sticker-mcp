from __future__ import annotations

import json
import os
import tempfile
import threading
from contextlib import suppress
from pathlib import Path
from urllib.parse import urljoin

from pydantic import ValidationError

from .models import Sticker, StickerView


class StickerRepository:
    def __init__(self, path: Path, public_base_url: str) -> None:
        self.path = path
        self.public_base_url = public_base_url.rstrip("/")
        self._write_lock = threading.Lock()

    def load(self) -> list[Sticker]:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise RuntimeError(f"表情包索引不存在：{self.path}") from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"表情包索引不是有效 JSON：{exc}") from exc

        raw_stickers = payload.get("stickers") if isinstance(payload, dict) else payload
        if not isinstance(raw_stickers, list):
            raise RuntimeError("表情包索引必须是数组或包含 stickers 数组的对象")

        try:
            stickers = [Sticker.model_validate(item) for item in raw_stickers]
        except ValidationError as exc:
            raise RuntimeError(f"表情包索引校验失败：{exc}") from exc

        ids = [sticker.id for sticker in stickers]
        if len(ids) != len(set(ids)):
            raise RuntimeError("表情包索引含有重复 id")
        return stickers

    def get(self, sticker_id: str) -> Sticker | None:
        return next((item for item in self.load() if item.id == sticker_id), None)

    def to_view(self, sticker: Sticker) -> StickerView:
        image_url = self.resolve_image_url(sticker.image_url)
        return StickerView(
            **sticker.model_dump(exclude={"image_url"}),
            image_url=image_url,
            markdown=f"![{sticker.name}]({image_url})",
        )

    def resolve_image_url(self, image_url: str) -> str:
        if image_url.startswith("${PUBLIC_BASE_URL}"):
            return image_url.replace("${PUBLIC_BASE_URL}", self.public_base_url, 1)
        if image_url.startswith("/"):
            return urljoin(f"{self.public_base_url}/", image_url.lstrip("/"))
        return image_url

    def add(self, sticker: Sticker) -> Sticker:
        with self._write_lock:
            existing = self.load()
            if any(item.id == sticker.id for item in existing):
                raise ValueError(f"表情包 id 已存在：{sticker.id}")
            existing.append(sticker)
            self._write(existing)
        return sticker

    def _write(self, stickers: list[Sticker]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "stickers": [item.model_dump(mode="json") for item in stickers],
        }
        fd, temp_name = tempfile.mkstemp(prefix=f"{self.path.name}.", suffix=".tmp", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, self.path)
        except Exception:
            with suppress(FileNotFoundError):
                os.unlink(temp_name)
            raise
