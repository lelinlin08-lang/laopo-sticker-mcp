from __future__ import annotations

import json
from pathlib import Path

import pytest

from laopo_sticker_mcp.config import Settings


@pytest.fixture
def sample_payload() -> dict:
    return {
        "version": 1,
        "stickers": [
            {
                "id": "love_cat_001",
                "name": "永远很爱你猫猫",
                "image_url": "${PUBLIC_BASE_URL}/media/love_cat_001.png",
                "tags": ["爱", "撒娇", "情侣", "安慰", "猫猫"],
                "description": "小猫认真说永远很爱你",
                "emotion": ["甜", "安慰", "认真", "亲昵"],
                "usage": "对方怀疑感情、撒娇询问爱不爱时使用",
            },
            {
                "id": "shock_cat_001",
                "name": "猫猫瞳孔地震",
                "image_url": "https://images.example.test/shock.png",
                "tags": ["震惊", "离谱", "猫猫"],
                "description": "猫猫震惊",
                "emotion": ["震惊", "不可思议"],
                "usage": "听到离谱消息时使用",
            },
        ],
    }


@pytest.fixture
def settings(tmp_path: Path, sample_payload: dict) -> Settings:
    data_file = tmp_path / "stickers.json"
    data_file.write_text(json.dumps(sample_payload, ensure_ascii=False), encoding="utf-8")
    synonyms = tmp_path / "synonyms.json"
    synonyms.write_text(
        json.dumps({"安慰": ["不爱", "难过", "哄"], "震惊": ["离谱", "救命"]}, ensure_ascii=False),
        encoding="utf-8",
    )
    media = tmp_path / "media"
    media.mkdir()
    media.joinpath("love_cat_001.png").write_bytes(b"\x89PNG\r\n\x1a\nfixture")
    return Settings(
        project_root=tmp_path,
        stickers_file=data_file,
        synonyms_file=synonyms,
        media_dir=media,
        public_base_url="http://testserver",
        enable_add_tool=False,
        enable_collect_tool=False,
        max_upload_bytes=1024 * 1024,
        host="127.0.0.1",
        port=8000,
        stateless_http=True,
        log_level="warning",
    )
