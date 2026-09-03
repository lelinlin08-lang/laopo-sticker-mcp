from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from .models import Sticker

SPLIT_RE = re.compile(r"[\s,，。.!！?？、;；:：/|]+")


def normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", text).casefold().strip()


def load_synonyms(path: Path) -> dict[str, list[str]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    if not isinstance(payload, dict):
        raise RuntimeError("synonyms.json 必须是对象")
    return {
        normalize(str(key)): [normalize(str(item)) for item in values if str(item).strip()]
        for key, values in payload.items()
        if isinstance(values, list)
    }


@dataclass(frozen=True, slots=True)
class RankedSticker:
    sticker: Sticker
    score: float


class StickerSearch:
    def __init__(self, synonyms: dict[str, list[str]] | None = None) -> None:
        self.synonyms = synonyms or {}

    def search(
        self,
        stickers: list[Sticker],
        *,
        query: str = "",
        emotion: str = "",
        context: str = "",
        limit: int = 3,
    ) -> list[RankedSticker]:
        if not any(value.strip() for value in (query, emotion, context)):
            raise ValueError("query、emotion、context 至少填写一个")

        limit = max(1, min(limit, 3))
        q = normalize(query)
        e = normalize(emotion)
        c = normalize(context)
        query_terms = self._expand_terms(q)
        emotion_terms = self._expand_terms(e)
        context_terms = self._expand_terms(c)

        ranked = [
            RankedSticker(
                sticker=sticker,
                score=self._score(sticker, q, e, c, query_terms, emotion_terms, context_terms),
            )
            for sticker in stickers
        ]
        ranked.sort(key=lambda item: (-item.score, item.sticker.id))
        positive = [item for item in ranked if item.score > 0]
        return positive[:limit]

    def _expand_terms(self, text: str) -> set[str]:
        if not text:
            return set()
        terms = {text, *(part for part in SPLIT_RE.split(text) if part)}
        for canonical, aliases in self.synonyms.items():
            family = {canonical, *aliases}
            if any(member and member in text for member in family):
                terms.update(family)
        return {term for term in terms if term}

    @staticmethod
    def _score(
        sticker: Sticker,
        query: str,
        emotion: str,
        context: str,
        query_terms: set[str],
        emotion_terms: set[str],
        context_terms: set[str],
    ) -> float:
        name = normalize(sticker.name)
        tags = [normalize(item) for item in sticker.tags]
        emotions = [normalize(item) for item in sticker.emotion]
        description = normalize(sticker.description)
        usage = normalize(sticker.usage)
        semantic_labels = {*tags, *emotions}

        score = 0.0

        def label_hits(text: str, weight: float) -> float:
            if not text:
                return 0.0
            return sum(weight for label in semantic_labels if label and label in text)

        score += label_hits(query, 7.0)
        score += label_hits(emotion, 6.0)
        score += label_hits(context, 3.5)

        for term in query_terms:
            if term in name:
                score += 5.0
            if any(term in item or item in term for item in tags):
                score += 4.0
            if any(term in item or item in term for item in emotions):
                score += 3.5
            if term in description:
                score += 2.0
            if term in usage:
                score += 2.5

        for term in emotion_terms:
            if any(term in item or item in term for item in emotions):
                score += 5.0
            if any(term in item or item in term for item in tags):
                score += 3.0

        for term in context_terms:
            if len(term) >= 2 and term in usage:
                score += 2.0
            if len(term) >= 2 and term in description:
                score += 1.0

        return score
