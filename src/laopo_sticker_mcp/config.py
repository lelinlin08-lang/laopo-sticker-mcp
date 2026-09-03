from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _detect_project_root() -> Path:
    explicit = os.getenv("STICKER_PROJECT_ROOT", "").strip()
    if explicit:
        return Path(explicit).expanduser().resolve()

    working_directory = Path.cwd().resolve()
    if (working_directory / "stickers.json").is_file():
        return working_directory

    source_checkout = Path(__file__).resolve().parents[2]
    if (source_checkout / "stickers.json").is_file():
        return source_checkout
    return working_directory


PROJECT_ROOT = _detect_project_root()


def _as_bool(value: str | None, *, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _path_from_env(name: str, default: str) -> Path:
    value = Path(os.getenv(name, default)).expanduser()
    return value if value.is_absolute() else PROJECT_ROOT / value


def _public_base_url() -> str:
    explicit = os.getenv("PUBLIC_BASE_URL", "").strip()
    if explicit:
        return explicit.rstrip("/")

    render_host = os.getenv("RENDER_EXTERNAL_HOSTNAME", "").strip()
    if render_host:
        return f"https://{render_host}".rstrip("/")

    railway_host = os.getenv("RAILWAY_PUBLIC_DOMAIN", "").strip()
    if railway_host:
        return f"https://{railway_host}".rstrip("/")

    return "http://127.0.0.1:8000"


@dataclass(frozen=True, slots=True)
class Settings:
    project_root: Path
    stickers_file: Path
    synonyms_file: Path
    media_dir: Path
    public_base_url: str
    enable_add_tool: bool
    enable_collect_tool: bool
    max_upload_bytes: int
    host: str
    port: int
    stateless_http: bool
    log_level: str

    @classmethod
    def from_env(cls) -> Settings:
        load_dotenv(PROJECT_ROOT / ".env", override=False)
        return cls(
            project_root=PROJECT_ROOT,
            stickers_file=_path_from_env("STICKERS_FILE", "stickers.json"),
            synonyms_file=_path_from_env("SYNONYMS_FILE", "synonyms.json"),
            media_dir=_path_from_env("MEDIA_DIR", "media"),
            public_base_url=_public_base_url(),
            enable_add_tool=_as_bool(os.getenv("ENABLE_ADD_TOOL")),
            enable_collect_tool=_as_bool(os.getenv("ENABLE_COLLECT_TOOL")),
            max_upload_bytes=int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024))),
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "8000")),
            stateless_http=_as_bool(os.getenv("MCP_STATELESS_HTTP"), default=True),
            log_level=os.getenv("LOG_LEVEL", "info").lower(),
        )
