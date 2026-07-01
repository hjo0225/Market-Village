"""T-104 · §7 뉴스 3지선다 엔진 검증.

핵심 명제: 뉴스는 가격을 안 움직인다(§7.1). 오직 클론의 감정만 흔든다.
매일 서로 다른 톤 3개를 뽑아 3지선다로 제시(§7.4). 같은 톤이라도 클론마다
다르게 반응(순응/역행, §5.5 뉴스톤 계수). 시그니처 드라마는 2~3배 강도(§7.5).
"""

from __future__ import annotations

import random

from sim import news
from sim.models import Asset


def test_load_pool():
    pool = news.load_news_pool()
    assert len(pool.news) >= 12
    tones = {n["tone"] for n in pool.news}
    assert tones == {"fear", "optimism", "uncertain"}
    assert len(pool.signature_dramas) == 3


def test_draw_three_distinct_tones():
    pool = news.load_news_pool()
    picked = news.draw_three(pool, random.Random(7))
    assert len(picked) == 3
    assert len({n["tone"] for n in picked}) == 3  # 서로 다른 톤 3개


def test_draw_three_deterministic():
    pool = news.load_news_pool()
    a = news.draw_three(pool, random.Random(7))
    b = news.draw_three(pool, random.Random(7))
    assert [n["id"] for n in a] == [n["id"] for n in b]


def test_news_does_not_move_price():
    # §7.1 — apply_news_to_clone는 가격을 받지도 바꾸지도 않는다.
    pool = news.load_news_pool()
    fear_news = next(n for n in pool.news if n["tone"] == "fear")
    asset = Asset(symbol="A", name="A", price=100.0)
    delta = news.apply_news_to_clone(fear_news)
    assert asset.price == 100.0          # 가격 불변(구조적 보장)
    assert delta.fear_delta != 0.0       # 감정은 흔들림


def test_tone_emotion_direction():
    pool = news.load_news_pool()
    fear_news = next(n for n in pool.news if n["tone"] == "fear")
    opt_news = next(n for n in pool.news if n["tone"] == "optimism")
    # 공포 톤(순응) → fear 상승 = 공포내성↓
    assert news.apply_news_to_clone(fear_news).fear_delta > 0
    # 낙관 톤(순응) → greed 상승 = 탐욕제어↓
    assert news.apply_news_to_clone(opt_news).greed_delta > 0


def test_reverse_clone_buys_the_dip():
    # 역행형 클론("줍줍"): 공포 톤에 오히려 침착해짐 → fear 하락(내성↑)
    pool = news.load_news_pool()
    fear_news = next(n for n in pool.news if n["tone"] == "fear")
    assert news.apply_news_to_clone(fear_news, reverse=True).fear_delta < 0


def test_coefficient_scales_magnitude():
    pool = news.load_news_pool()
    fear_news = next(n for n in pool.news if n["tone"] == "fear")
    weak = news.apply_news_to_clone(fear_news, coef=0.5).fear_delta
    strong = news.apply_news_to_clone(fear_news, coef=1.5).fear_delta
    assert strong > weak > 0


def test_tone_to_trap_mapping():
    pool = news.load_news_pool()
    for n in pool.news:
        traps = set(n.get("triggers", []))
        if n["tone"] == "fear":
            assert traps <= {"F1", "F2"}
        elif n["tone"] == "optimism":
            assert traps <= {"M1", "M2", "G1", "G2"}


def test_signature_drama_stronger():
    pool = news.load_news_pool()
    drama = news.signature_drama(pool, "sig_great_crash")
    assert drama is not None
    assert 2.0 <= drama["strength_mult"] <= 3.0
    # 시그니처는 일반 뉴스보다 큰 감정 델타
    base = abs(news.apply_news_to_clone({"tone": "fear", "triggers": ["F1"]}).fear_delta)
    sig = abs(news.apply_news_to_clone(drama, coef=drama["strength_mult"]).fear_delta)
    assert sig > base


def test_signature_drama_miss_none():
    pool = news.load_news_pool()
    assert news.signature_drama(pool, "nonexistent") is None
