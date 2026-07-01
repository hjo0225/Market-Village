"""T-111(+개별화) · §10 클론 표시 스탯 — 6함정 개별 저항/제어 + 멘탈회복(7개).

우마무스메식 스탯 UI를 쓰되 올리는 게임이 아니라 무너지는 걸 견디는 게임(§10).
코드 NPC 수치(fear 높음=취약, §9.5.2)를 클론 표시용 '내성/저항'(높을수록 강함)
으로 뒤집어 보여준다. 6함정(F1~M2)을 각각 개별 스탯으로(그룹 묶음 아님) — 내부
6함정 취약점 점수(§5.5, 1층 기질 고정)와 짝을 이루는 동적 버전(2층 상태, 매매
행동에서 실시간으로 움직임). 스탯은 클론의 실제 매매에서 자동으로 차오르고
깎인다(§11.5 비대칭). 평온한 날(트리거 자체 없음)은 관련 함정이 없어 아무 것도
안 움직인다(사람 결정 — 8:3:1 비대칭 희석 방지, 회복은 오직 함정을 견뎌야만).
"""

from __future__ import annotations

from sim import clone_stats as CSt

ALL_SEVEN = {"급락패닉저항", "멘탈마모저항", "익절거부제어", "과대베팅제어",
            "추격매수저항", "막차불안저항", "멘탈회복"}


def test_seven_stats_inverted_from_raw():
    # PRD §10 예시 패널의 그룹 축(공포/탐욕/FOMO)을 유지하되 6함정으로 개별화:
    # fear69→공포계열 31, greed78→탐욕계열 22, excitement88→FOMO계열 12, confidence41→멘탈41
    emo = {"fear": 69.0, "greed": 78.0, "excitement": 88.0, "confidence": 41.0}
    s = CSt.clone_stats(emo)
    assert set(s) == ALL_SEVEN
    # F1·F2는 같은 fear에서 쌍으로 시작(초기값 시점엔 구분할 개별 이력 없음)
    assert s["급락패닉저항"] == 31.0 and s["멘탈마모저항"] == 31.0
    assert s["익절거부제어"] == 22.0 and s["과대베팅제어"] == 22.0
    assert s["추격매수저항"] == 12.0 and s["막차불안저항"] == 12.0
    assert s["멘탈회복"] == 41.0


def test_stat_for_trap_mapping_is_individual():
    # 그룹 묶음이 아니라 함정마다 1:1 개별 스탯
    assert CSt.stat_for_trap("F1") == "급락패닉저항"
    assert CSt.stat_for_trap("F2") == "멘탈마모저항"
    assert CSt.stat_for_trap("G1") == "익절거부제어"
    assert CSt.stat_for_trap("G2") == "과대베팅제어"
    assert CSt.stat_for_trap("M1") == "추격매수저항"
    assert CSt.stat_for_trap("M2") == "막차불안저항"


def _base():
    return {k: 50.0 for k in ALL_SEVEN}


def test_outcome_asymmetry():
    # 함정에 빠짐 −8, 견딤 +3 (§11.5.1 비대칭 8:3)
    base = _base()
    fell = CSt.apply_outcome(dict(base), "F1", "trap")
    assert fell["급락패닉저항"] == 42.0
    resisted = CSt.apply_outcome(dict(base), "F1", "resist")
    assert resisted["급락패닉저항"] == 53.0
    # 나빠지는 폭 > 좋아지는 폭
    assert (50.0 - fell["급락패닉저항"]) > (resisted["급락패닉저항"] - 50.0)


def test_outcome_clamps():
    low = _base(); low["급락패닉저항"] = 3.0
    assert CSt.apply_outcome(low, "F1", "trap")["급락패닉저항"] == 0.0
    high = _base(); high["급락패닉저항"] = 99.0
    assert CSt.apply_outcome(high, "F1", "resist")["급락패닉저항"] == 100.0


def test_only_mapped_stat_changes():
    # F1·F2가 같은 fear에서 쌍으로 시작해도, 실제 발동한 함정 하나만 개별로 움직임
    base = _base()
    out = CSt.apply_outcome(dict(base), "M1", "trap")
    assert out["추격매수저항"] == 42.0
    assert out["막차불안저항"] == 50.0            # 짝인 M2는 안 바뀜(개별화 확인)
    assert out["급락패닉저항"] == 50.0 and out["익절거부제어"] == 50.0
