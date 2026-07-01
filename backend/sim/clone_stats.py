"""§10 클론 표시 스탯 — 무너지는 걸 견디는 게임의 역설계 UI.

같은 우마무스메식 스탯 UI, 정반대 감정(§10). 코드 NPC 수치는 'fear 높음=취약'
(§9.5.2)이지만 클론 표시용은 '내성/저항'(높을수록 강함)이라 부호를 뒤집는다.

6함정(F1~M2) 개별 저항/제어 + 멘탈회복 = 7개를 각각 보여준다(§5.5의 6함정 취약점
점수와 짝을 이루는 동적 버전 — 취약점은 1층 기질 고정값, 이 스탯은 2층 상태로
매매 행동에서 실시간으로 움직임). 초기값은 F1·F2가 같은 fear에서, G1·G2가 같은
greed에서, M1·M2가 같은 excitement에서 출발해 쌍으로 시작하지만, 이후 각자 실제
어느 함정이 발동했는지에 따라 개별로 갈라진다.

플레이어는 직접 못 올리고(교류로 간접), 클론의 실제 매매 행동에서 자동으로
차오르고 깎인다(§11.5 비대칭). trust(정보 신뢰)는 클론 표시 스탯이 아니다
(§11.4.3) — 여기 안 들어간다.
"""

from __future__ import annotations

from . import tuning as T

F1_RES = "급락패닉저항"
F2_RES = "멘탈마모저항"
G1_CTRL = "익절거부제어"
G2_CTRL = "과대베팅제어"
M1_RES = "추격매수저항"
M2_RES = "막차불안저항"
MENTAL = "멘탈회복"

# 함정 → 영향 받는 표시 스탯 (§10 개별 표시, 1:1)
_TRAP_STAT = {
    "F1": F1_RES, "F2": F2_RES,
    "G1": G1_CTRL, "G2": G2_CTRL,
    "M1": M1_RES, "M2": M2_RES,
}

# 결과 → 적용 델타 (§11.5.1 비대칭 8:3)
_OUTCOME_DELTA = {
    "trap": T.DELTA_TRAP,      # 함정에 빠짐 −8
    "resist": T.DELTA_RESIST,  # 견딤 +3
    "calm": T.DELTA_CALM,      # 평온한 날 +1
}


def _field(emotion, name: str) -> float:
    if isinstance(emotion, dict):
        return float(emotion.get(name, 50.0))
    return float(getattr(emotion, name, 50.0))


def clone_stats(emotion) -> dict[str, float]:
    """raw 감정(fear/greed/excitement/confidence) → 7 표시 스탯(부호 역전 §9.5.2).

    F1·F2는 같은 fear에서, G1·G2는 같은 greed에서, M1·M2는 같은 excitement에서
    쌍으로 시작(초기값 산출 시점엔 아직 구분할 개별 이력이 없음) — 이후
    apply_outcome이 실제 발동한 함정만 개별로 움직인다.
    """
    fear_r = round(T.STAT_MAX - _field(emotion, "fear"), 2)
    greed_r = round(T.STAT_MAX - _field(emotion, "greed"), 2)
    fomo_r = round(T.STAT_MAX - _field(emotion, "excitement"), 2)
    return {
        F1_RES: fear_r, F2_RES: fear_r,
        G1_CTRL: greed_r, G2_CTRL: greed_r,
        M1_RES: fomo_r, M2_RES: fomo_r,
        MENTAL: round(_field(emotion, "confidence"), 2),  # 자신감 ↔ 위축
    }


def stat_for_trap(trap_id: str) -> str | None:
    return _TRAP_STAT.get(trap_id)


def apply_outcome(stats: dict[str, float], trap_id: str, outcome: str) -> dict[str, float]:
    """매매 결과를 해당 스탯에 자동 반영(§11.5 비대칭). 0~100 클램프."""
    stat = stat_for_trap(trap_id)
    delta = _OUTCOME_DELTA.get(outcome, 0.0)
    if stat is not None and stat in stats:
        stats[stat] = T.clamp(stats[stat] + delta, T.STAT_MIN, T.STAT_MAX)
    return stats
