"""T-122 · D-B 가격 하이브리드 — 운명선 90% 고정 + 출렁임 10%.

§6.3 2층 시장: 1층 운명선(고정, 90%)이 가격의 모양을 정하고, 2층 에이전트 매매가
±10% 얇은 질감만 더한다. 가격(A)은 운명선에 단단히 묶이고(회차 재현=기둥3),
출렁임은 양념. 자산별 시작가에 운명선 지수(day1=100)를 스케일해 모양을 입힌다.

이 티켓은 하이브리드 '결합기'와 심볼→카테고리 매퍼(순수)를 제공한다. 30일 루프에서
이를 매 라운드 적용해 가격 정본을 교체하는 일은 T-118(일별 인덱싱 존재)에서 한다.
"""

from __future__ import annotations

from sim import fate_line as FL


def test_category_for_symbol():
    assert FL.category_for_symbol("BTC") == "large_stable"
    assert FL.category_for_symbol("ETH") == "large_stable"
    assert FL.category_for_symbol("SOL") == "mid_alt"
    assert FL.category_for_symbol("DOGE") == "meme"
    assert FL.category_for_symbol("PEPE") == "meme"
    assert FL.category_for_symbol("USDT") == "stable"
    # 미지의 심볼은 중견 알트로 폴백
    assert FL.category_for_symbol("XYZ") == "mid_alt"
    # 대소문자 무관
    assert FL.category_for_symbol("btc") == "large_stable"


def test_hybrid_price_fate_base_is_90pct():
    # 출렁임 0이면 가격 = 시작가 × (운명선지수/100) — 순수 운명선 모양
    assert FL.hybrid_price(1000.0, fate_index=100.0, agent_pressure=0.0) == 1000.0
    assert FL.hybrid_price(1000.0, fate_index=120.0, agent_pressure=0.0) == 1200.0
    assert FL.hybrid_price(1000.0, fate_index=80.0, agent_pressure=0.0) == 800.0


def test_hybrid_wobble_capped_10pct():
    # 에이전트 압력이 커도 운명선 기준 ±10% 안에서만 출렁인다
    assert FL.hybrid_price(1000.0, 100.0, agent_pressure=0.5) == 1100.0   # +10% 상한
    assert FL.hybrid_price(1000.0, 100.0, agent_pressure=-0.5) == 900.0   # −10% 하한
    # 운명선이 80일 때 출렁임은 그 base(800) 기준 ±10%
    assert abs(FL.hybrid_price(1000.0, 80.0, agent_pressure=-0.5) - 720.0) < 1e-9


def test_hybrid_never_negative():
    assert FL.hybrid_price(1000.0, 0.0, agent_pressure=-0.5) == 0.0
