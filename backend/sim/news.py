"""§7 뉴스 3지선다 엔진 — 가격이 아니라 클론의 '심리'를 흔드는 레버.

핵심 명제(§7.1): 뉴스는 **가격에 영향을 주지 않는다.** 가격은 운명선(§6.3)대로만
움직인다. 뉴스는 오직 클론의 감정·행동에만 작용한다. → "너를 움직인 건 뉴스가
아니라, 뉴스에 대한 너의 반응이다."

매일(낮) 서로 다른 톤 3개를 뽑아 3지선다 제시(§7.4). 같은 톤이라도 클론마다 다르게
반응(§5.5 뉴스톤 계수: 순응 or 역행). 시그니처 드라마는 일반 뉴스의 2~3배(§7.5).

이 모듈은 가격을 **받지도 반환하지도 않는다** — §7.1을 구조로 강제한다.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from . import tuning as T
from .models import EmotionDelta

REPO_ROOT = Path(__file__).resolve().parents[2]
NEWS_POOL_PATH = REPO_ROOT / "news_pool.seed.json"

# 톤 → 흔드는 감정축 (§7.3)
_TONE_AXIS = {
    "fear": "fear",        # 매도 충동 (공포내성↓)
    "optimism": "greed",   # 매수 충동 (탐욕제어↓)
    "uncertain": "fear",   # 불안 자체 (얼어붙음/조급)
}

# intensity → 강도 배수 (§7.5: 일반의 2~3배)
_INTENSITY_MULT = {"high": 2.0, "extreme": 3.0}


@dataclass
class NewsPool:
    news: list[dict]
    signature_dramas: list[dict]
    tone_to_trap: dict


@lru_cache(maxsize=2)
def _load_raw(path_str: str) -> dict:
    with open(path_str, encoding="utf-8") as f:
        return json.load(f)


def load_news_pool(path: Path | None = None) -> NewsPool:
    raw = _load_raw(str(path or NEWS_POOL_PATH))
    sig = raw.get("signature_dramas", {}).get("events", [])
    return NewsPool(
        news=list(raw.get("news", [])),
        signature_dramas=list(sig),
        tone_to_trap=dict(raw.get("tone_to_trap", {})),
    )


def draw_three(pool: NewsPool, rng: random.Random) -> list[dict]:
    """§7.4 — 서로 다른 톤 3개를 결정론으로 뽑는다(명백한 정답 없음)."""
    by_tone: dict[str, list[dict]] = {"fear": [], "optimism": [], "uncertain": []}
    for n in pool.news:
        by_tone.setdefault(n["tone"], []).append(n)
    picked = []
    for tone in ("fear", "optimism", "uncertain"):
        bucket = by_tone.get(tone, [])
        if bucket:
            picked.append(rng.choice(bucket))
    return picked


def apply_news_to_clone(
    news_item: dict, coef: float = 1.0, reverse: bool = False
) -> EmotionDelta:
    """뉴스 톤 → 클론 감정 델타(§7.1: 가격 무관). coef=뉴스톤 반응 계수(0.5~1.5,
    §5.5), reverse=역행형 클론("줍줍"). 가격을 받지 않음으로 §7.1을 강제."""
    tone = news_item.get("tone", "fear")
    # 순응이면 기본 강도(내성 −6), 역행이면 작게 반대로(내성 +3)
    base = T.NEWS_TONE_REVERSE if reverse else abs(T.NEWS_TONE_DELTA)
    sign = -1.0 if reverse else 1.0
    mag = base * coef * sign

    delta = EmotionDelta()
    if tone == "optimism":
        delta.greed_delta = mag
        delta.excitement_delta = mag * 0.5
    elif tone == "uncertain":
        delta.fear_delta = mag * 0.5   # 불안은 공포보다 옅게
    else:  # fear (기본)
        delta.fear_delta = mag
    return delta


def signature_drama(pool: NewsPool, drama_id: str) -> dict | None:
    """§7.5 — 시그니처 드라마를 강도 배수(2~3배) 부여해 반환. 미스는 None."""
    for ev in pool.signature_dramas:
        if ev.get("id") == drama_id:
            out = dict(ev)
            out["strength_mult"] = _INTENSITY_MULT.get(ev.get("intensity"), 2.0)
            return out
    return None
