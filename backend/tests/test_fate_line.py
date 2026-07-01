"""T-102 · §6.1/6.3 고정 운명선 로더 검증.

운명선 = 과거 실제(또는 오프라인 합성) 30일 OHLC, 지수정규화(첫날 종가=100),
블라인드(종목명·시기는 _meta_*에만). 회차가 바뀌어도 동일(기둥3 통제변인).
2층 출렁임(§6.3)은 ±10%로 클램프되어 90% 고정을 보장한다.
"""

from __future__ import annotations

from sim import fate_line as F

CATS = {"large_stable", "mid_alt", "meme", "stable"}


def test_four_categories():
    fl = F.load_fate_line()
    assert set(fl.categories()) == CATS


def test_thirty_days():
    fl = F.load_fate_line()
    assert fl.days == 30
    for c in fl.categories():
        assert fl.day_ohlc(c, 29) is not None


def test_index_normalized_day1_close_100():
    fl = F.load_fate_line()
    for c in fl.categories():
        o, h, l, cl = fl.day_ohlc(c, 0)
        assert abs(cl - 100.0) < 1e-6


def test_ohlc_invariants():
    fl = F.load_fate_line()
    for c in fl.categories():
        for d in range(fl.days):
            o, h, l, cl = fl.day_ohlc(c, d)
            assert l <= o <= h
            assert l <= cl <= h


def test_change_rate():
    fl = F.load_fate_line()
    assert fl.change_rate("large_stable", 0) == 0.0  # 첫날은 전일 없음
    cr = fl.change_rate("meme", 5)
    assert isinstance(cr, float)
    # 정의: (close[d]-close[d-1])/close[d-1] 백분율
    _, _, _, c4 = fl.day_ohlc("meme", 4)
    _, _, _, c5 = fl.day_ohlc("meme", 5)
    assert abs(cr - (c5 - c4) / c4 * 100.0) < 1e-6


def test_category_swing_ordering():
    # SEED_GUIDE: 변동성 stable < large_stable < mid_alt < meme
    fl = F.load_fate_line()
    sw = {c: fl.swing(c) for c in fl.categories()}
    assert sw["stable"] < sw["large_stable"] < sw["mid_alt"] < sw["meme"]


def test_fate_line_has_crash_and_surge():
    # 6함정을 시험하려면 급락(F1: ≤−15%)·급등(M1: ≥+20%)이 운명선에 존재해야 함
    fl = F.load_fate_line()
    all_crs = [
        fl.change_rate(c, d) for c in fl.categories() for d in range(1, fl.days)
    ]
    assert min(all_crs) <= -15.0  # 어딘가 급락
    assert max(all_crs) >= 20.0   # 어딘가 급등


def test_meta_hidden_from_public_view():
    fl = F.load_fate_line()
    pub = fl.public_view()
    for cat in pub.values():
        assert all(not k.startswith("_meta") for k in cat)


def test_apply_wobble_clamps_to_10pct():
    # §6.3 2층 출렁임은 ±10% 이내 (90% 고정 보장)
    assert abs(F.apply_wobble(100.0, 0.5) - 110.0) < 1e-9   # +10% 상한 클램프
    assert abs(F.apply_wobble(100.0, -0.5) - 90.0) < 1e-9   # −10% 하한 클램프
    assert abs(F.apply_wobble(200.0, 0.03) - 206.0) < 1e-9
    assert F.apply_wobble(100.0, 0.0) == 100.0


def test_miss_returns_none():
    fl = F.load_fate_line()
    assert fl.day_ohlc("nonexistent", 0) is None
    assert fl.day_ohlc("large_stable", 999) is None
    assert fl.change_rate("nonexistent", 5) == 0.0
