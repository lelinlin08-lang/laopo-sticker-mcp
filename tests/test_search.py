from __future__ import annotations

import pytest

from laopo_sticker_mcp.repository import StickerRepository
from laopo_sticker_mcp.search import StickerSearch, load_synonyms


def test_love_context_ranks_love_sticker_first(settings) -> None:
    repository = StickerRepository(settings.stickers_file, settings.public_base_url)
    search = StickerSearch(load_synonyms(settings.synonyms_file))
    ranked = search.search(
        repository.load(),
        query="爱",
        emotion="安慰、亲昵",
        context="用户撒娇问我是不是不爱她了",
        limit=3,
    )
    assert ranked[0].sticker.id == "love_cat_001"


def test_shock_context_ranks_shock_sticker_first(settings) -> None:
    repository = StickerRepository(settings.stickers_file, settings.public_base_url)
    search = StickerSearch(load_synonyms(settings.synonyms_file))
    ranked = search.search(repository.load(), query="救命，太离谱了", context="听到反转", limit=1)
    assert [item.sticker.id for item in ranked] == ["shock_cat_001"]


def test_search_requires_signal(settings) -> None:
    repository = StickerRepository(settings.stickers_file, settings.public_base_url)
    search = StickerSearch()
    with pytest.raises(ValueError, match="至少填写一个"):
        search.search(repository.load())
