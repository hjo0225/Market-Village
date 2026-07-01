"""§8 6함정 분류 + §8.5 트리거 감지/정렬 (순수 규칙 엔진).

각 함정은 트리거 타입이 구조적으로 달라야 한다(§8.2): F계열(공포)은 '안 파는 게'
정답, G1(탐욕)은 '파는 게' 정답 — 정반대다. 따라서 단순 암기가 아니라 상황을
구분하는 판단력을 요구한다.

이 모듈은 결정만 한다(결정/표현 분리 §8.6.3). 대사·독백은 LLM 표현 계층이 입힌다.
임계값은 전부 sim.tuning(§11.5)에서 읽는다.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import tuning as T


# --------------------------------------------------------------------------- #
# 함정 분류 (§8.2)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Trap:
    id: str             # F1/F2/G1/G2/M1/M2
    name: str           # 한국어 이름
    correct_action: str  # hold / take_profit / size / hold_off
    impulse: str        # 충동적 오류
    trigger_type: str   # single(단발) / cumulative(누적) / state(상태의존)
    group: str          # fear / greed / fomo


ALL_TRAPS: tuple[Trap, ...] = (
    Trap("F1", "급락 패닉", "hold", "공포성 투매", "single", "fear"),
    Trap("F2", "멘탈 마모", "hold", "소모성 매도", "cumulative", "fear"),
    Trap("G1", "익절 거부", "take_profit", "매도 미루다 되돌림", "state", "greed"),
    Trap("G2", "과대 베팅", "size", "분산 깨고 몰빵", "state", "greed"),
    Trap("M1", "추격 매수", "hold_off", "고점 추격", "single", "fomo"),
    Trap("M2", "막차 불안", "hold_off", "분위기 추종 매수", "cumulative", "fomo"),
)

_BY_ID = {t.id: t for t in ALL_TRAPS}

# 단발 충격(급한 불 먼저, §8.5 STEP2 ①)
_SINGLE_SHOCK = {t.id for t in ALL_TRAPS if t.trigger_type == "single"}


# --------------------------------------------------------------------------- #
# 위기 컨텍스트 (그날의 시장 상태 + 클론 상태)
# --------------------------------------------------------------------------- #
@dataclass
class CrisisContext:
    """§8.5 STEP1이 6함정 조건과 대조할 입력. 모든 값은 '없음=무자극' 기본값."""

    change_pct: float = 0.0          # 당일 변화율(운명선 change_rate) — F1
    dip_streak: int = 0              # 소폭 하락 연속일 — F2
    wear_gauge: float = 0.0          # 마모 게이지 — F2
    holding_profit_pct: float = 0.0  # 보유 평가익 % — G1
    confidence: float = 0.0          # 자신감 — G2
    just_realized_profit: bool = False  # 직전 매매 수익 실현 — G2
    unheld_surge_pct: float = 0.0    # 미보유 종목 급등 % — M1
    fgi: float = 0.0                 # 시장 과열 지수 — M2
    crowd_buying: bool = False       # 군중 매수 우세 — M2


def detect_triggers(ctx: CrisisContext) -> set[str]:
    """§8.5 STEP1 — 조건을 만족한 함정 id 집합. 평온하면 빈 집합."""
    fired: set[str] = set()
    if ctx.change_pct <= T.F1_CRASH_PCT:
        fired.add("F1")
    if ctx.dip_streak >= T.F2_DIP_DAYS or ctx.wear_gauge >= T.F2_GAUGE:
        fired.add("F2")
    if ctx.holding_profit_pct >= T.G1_PROFIT_PCT:
        fired.add("G1")
    if ctx.confidence >= T.G2_CONFIDENCE and ctx.just_realized_profit:
        fired.add("G2")
    if ctx.unheld_surge_pct >= T.M1_SURGE_PCT:
        fired.add("M1")
    if ctx.fgi >= T.M2_FGI and ctx.crowd_buying:
        fired.add("M2")
    return fired


def prioritize(
    triggered: set[str], vulnerability: dict[str, float] | None = None
) -> str | None:
    """§8.5 STEP2 — 복수 트리거 중 '오늘의 위기' 1개 선정.

    ① 단발 충격(F1/M1) > 누적·상태의존  (급한 불 먼저)
    ② 동급이면 클론 취약점 점수가 더 높은 함정 우선  (가장 약한 곳이 먼저 터짐)
    나머지 트리거는 호출자가 이월(누적형 게이지 유지)할 수 있다.
    """
    if not triggered:
        return None
    vuln = vulnerability or {}

    def key(tid: str) -> tuple[int, float]:
        return (1 if tid in _SINGLE_SHOCK else 0, vuln.get(tid, 0.0))

    return max(sorted(triggered), key=key)


def get_trap(trap_id: str) -> Trap | None:
    return _BY_ID.get(trap_id)
