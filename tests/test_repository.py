from __future__ import annotations

import pytest

from laopo_sticker_mcp.models import Sticker
from laopo_sticker_mcp.repository import StickerRepository


def test_resolves_public_base_url(settings) -> None:
    repository = StickerRepository(settings.stickers_file, "https://stickers.example.com")
    sticker = repository.get("love_cat_001")
    assert sticker is not None
    view = repository.to_view(sticker)
    assert view.image_url == "https://stickers.example.com/media/love_cat_001.png"
    assert view.markdown == "![永远很爱你猫猫](https://stickers.example.com/media/love_cat_001.png)"


def test_add_is_atomic_and_rejects_duplicate(settings) -> None:
    repository = StickerRepository(settings.stickers_file, settings.public_base_url)
    sticker = Sticker(
        id="happy_cat_001",
        name="开心猫",
        image_url="https://images.example.test/happy.png",
        tags=["开心"],
        description="开心猫猫",
        emotion=["开心"],
        usage="庆祝时使用",
    )
    repository.add(sticker)
    assert repository.get(sticker.id) == sticker
    with pytest.raises(ValueError, match="已存在"):
        repository.add(sticker)
