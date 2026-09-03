from __future__ import annotations

import os
import tempfile
from contextlib import suppress
from pathlib import Path
from urllib.parse import urljoin

import httpx

from .models import ChatGPTFile
from .security import assert_safe_public_https_url

ALLOWED_MIME_TO_EXTENSION = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


async def download_chatgpt_image(file: ChatGPTFile, *, max_bytes: int) -> tuple[bytes, str]:
    current_url = file.download_url
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
        for _ in range(4):
            assert_safe_public_https_url(current_url)
            async with client.stream("GET", current_url, headers={"Accept": "image/*"}) as response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get("location")
                    if not location:
                        raise ValueError("附件下载重定向缺少 Location")
                    current_url = urljoin(current_url, location)
                    continue
                response.raise_for_status()
                mime_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                if mime_type not in ALLOWED_MIME_TO_EXTENSION:
                    raise ValueError(f"不支持的图片类型：{mime_type or '未知'}")
                declared_size = int(response.headers.get("content-length", "0") or 0)
                if declared_size > max_bytes:
                    raise ValueError(f"图片超过大小限制：{max_bytes} bytes")
                chunks: list[bytes] = []
                size = 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > max_bytes:
                        raise ValueError(f"图片超过大小限制：{max_bytes} bytes")
                    chunks.append(chunk)
                if not chunks:
                    raise ValueError("下载到的图片为空")
                return b"".join(chunks), ALLOWED_MIME_TO_EXTENSION[mime_type]
    raise ValueError("附件下载重定向次数过多")


def save_media_atomically(media_dir: Path, filename: str, data: bytes) -> Path:
    media_dir.mkdir(parents=True, exist_ok=True)
    destination = media_dir / filename
    fd, temp_name = tempfile.mkstemp(prefix=f"{filename}.", suffix=".tmp", dir=media_dir)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, destination)
    except Exception:
        with suppress(FileNotFoundError):
            os.unlink(temp_name)
        raise
    return destination
