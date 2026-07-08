"""T-19: 동행 체인 이벤트 엔진 (문서 §5·§8).

companion 확정 직후, 결정론 확률로 그 NPC 체인의 다음 미발동 단계를 발동한다.
단계2·3은 rapport 게이트. 발동·해결 시 special_event_count++. 효과는 4축 델타
+ rapport(옛 6함정 스탯 아님). 데이터(24편)는 T-20이 주입 — 엔진은 데이터 무관.
"""

import pytest

from sim.chain import (
    CHAIN_RAPPORT_GATE,
    apply_chain_choice,
    maybe_trigger,
    next_stage,
)
from sim.player_emotion.state import PlayerEmotionState

# 픽스처 체인표(NPC 1명, 3단계).
FIXTURE = {
    "panic_ant": {
        1: {"title": "쏟은 커피", "text": "...", "choices": [
            {"id": "A", "label": "커피 살게", "deltas": {"fear": -4}, "rapport": 2},
            {"id": "B", "label": "차트 그만 봐", "deltas": {"fear": -2}, "rapport": -1},
        ]},
        2: {"title": "새벽 매도", "text": "...", "choices": [
            {"id": "A", "label": "이해해", "deltas": {"anxiety": -4}, "rapport": 2},
        ]},
        3: {"title": "모닝콜 동맹", "text": "...", "choices": [],
            "reward": {"deltas": {"fear": -6}}},
    },
}


def _emo():
    return PlayerEmotionState(fear=60, greed=50, anxiety=50, restlessness=50)


def test_next_stage_progression():
    assert next_stage({}, "panic_ant") == 1
    assert next_stage({"panic_ant": 1}, "panic_ant") == 2
    assert next_stage({"panic_ant": 3}, "panic_ant") is None   # 완주


def test_trigger_is_deterministic():
    a = maybe_trigger(42, 0, "panic_ant", {}, rapport=0.0, prob=1.0)
    b = maybe_trigger(42, 0, "panic_ant", {}, rapport=0.0, prob=1.0)
    assert a == b == 1


def test_prob_zero_never_triggers():
    assert maybe_trigger(42, 0, "panic_ant", {}, rapport=0.0, prob=0.0) is None


def test_stage2_blocked_by_rapport_gate():
    prog = {"panic_ant": 1}
    # 래포 부족 → 단계2 차단.
    assert maybe_trigger(1, 3, "panic_ant", prog, rapport=CHAIN_RAPPORT_GATE - 1, prob=1.0) is None
    # 래포 충족 → 단계2 발동.
    assert maybe_trigger(1, 3, "panic_ant", prog, rapport=CHAIN_RAPPORT_GATE, prob=1.0) == 2


def test_completed_chain_never_triggers():
    assert maybe_trigger(1, 5, "panic_ant", {"panic_ant": 3}, rapport=99, prob=1.0) is None


def test_apply_choice_updates_emotion_and_rapport():
    emo, rap = apply_chain_choice(_emo(), 0.0, FIXTURE["panic_ant"][1], "A")
    assert emo.fear < 60          # deltas 적용
    assert rap == 2.0             # rapport 적용


def test_apply_choice_rejects_unknown():
    with pytest.raises(ValueError):
        apply_chain_choice(_emo(), 0.0, FIXTURE["panic_ant"][1], "Z")


# --- T-26: 데드락 회귀 잠금 (실 데이터로 1→2→3 진행 가능해야) ------------- #
from sim.chain import CHAIN_NPCS, load_chains  # noqa: E402


def _best_rapport_choice(event: dict) -> str:
    """그 단계에서 rapport를 가장 많이 올리는 선택지 id."""
    return max(event["choices"], key=lambda c: c.get("rapport", 0))["id"]


@pytest.mark.parametrize("npc", CHAIN_NPCS)
def test_full_chain_reachable_with_best_rapport_choices(npc):
    """T-26 데드락 회귀: 실 npc_chains.json에서, 각 단계 최고-rapport 선택지를
    고르면 rapport 누적이 게이트를 넘어 stage 1→2→3가 전부 발동해야 한다.

    이전(gate 3.0 vs stage1 최고 +2)엔 stage2가 영구 차단돼 동행 체인이
    stage1 인트로만 반복되고 절대 진행하지 못했다(사용자 "1:1이 작동 안 함").
    """
    chains = load_chains()
    stages = chains[npc]
    emo = _emo()
    rapport = 0.0
    progress: dict[str, int] = {}
    reached = []
    for day in range(1, 4):
        stage = maybe_trigger(7, day, npc, progress, rapport, prob=1.0)
        assert stage is not None, (
            f"{npc}: day{day} 체인 발동 실패 — rapport={rapport} 게이트 미달(데드락)"
        )
        reached.append(stage)
        ev = stages[stage]
        if ev.get("choices"):
            cid = _best_rapport_choice(ev)
            emo, rapport = apply_chain_choice(emo, rapport, ev, cid)
        progress[npc] = stage
    assert reached == [1, 2, 3], f"{npc}: 진행 단계 {reached} != [1,2,3]"
