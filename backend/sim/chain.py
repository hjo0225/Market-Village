"""T-19: 동행 체인 이벤트 엔진 (문서 §5·§8).

우마무스메 서포트카드식 — companion 확정 직후, 결정론 확률로 그 NPC 체인의 다음
미발동 단계(1→2→3)를 발동한다. 단계2·3은 개별 rapport 게이트. 효과는 4축 델타 +
rapport(옛 6함정 스탯 아님). 24편 데이터(T-20)는 load_chains가 주입 — 엔진은
데이터에 무관하게 순수하다.

결정론 rng: crc32(f"special:{seed}:{day}:{npc_id}") — 회차 재현(문서 §5.1).
"""

from __future__ import annotations

import json
import random
import zlib
from functools import lru_cache
from pathlib import Path

from .player_emotion.deltas import apply_delta
from .player_emotion.state import PlayerEmotionState

CHAINS_PATH = Path(__file__).resolve().parent / "data" / "npc_chains.json"

CHAIN_STAGES = 3
# 🙋 튜닝 잠정치(플레이테스트 확정 — 문서 §8).
SPECIAL_EVENT_PROB = 0.6      # 동행 시 체인 발동 확률
CHAIN_RAPPORT_GATE = 3.0      # 단계 2·3 개별 rapport 기준선


def next_stage(progress: dict[str, int], npc_id: str) -> int | None:
    """그 NPC의 다음 미발동 단계(1~3). 완주했으면 None."""
    done = progress.get(npc_id, 0)
    return done + 1 if done < CHAIN_STAGES else None


def _roll(seed: int, day: int, npc_id: str) -> float:
    rng = random.Random(zlib.crc32(f"special:{seed}:{day}:{npc_id}".encode()))
    return rng.random()


def maybe_trigger(
    seed: int,
    day: int,
    npc_id: str,
    progress: dict[str, int],
    rapport: float,
    *,
    prob: float = SPECIAL_EVENT_PROB,
    gate: float = CHAIN_RAPPORT_GATE,
) -> int | None:
    """발동할 단계 번호(1~3) 또는 None. 완주/래포미달/확률탈락이면 None."""
    stage = next_stage(progress, npc_id)
    if stage is None:
        return None
    if stage >= 2 and rapport < gate:
        return None
    if _roll(seed, day, npc_id) >= prob:
        return None
    return stage


def apply_chain_choice(
    emotion: PlayerEmotionState, rapport: float, event: dict, choice_id: str
) -> tuple[PlayerEmotionState, float]:
    """체인 선택지 효과 적용 → (새 감정, 새 rapport). 미지의 choice_id면 ValueError."""
    for ch in event.get("choices", []):
        if ch["id"] == choice_id:
            new_emotion = apply_delta(emotion, ch.get("deltas", {}))
            return new_emotion, rapport + float(ch.get("rapport", 0))
    raise ValueError(f"unknown chain choice {choice_id!r}")


def apply_chain_reward(
    emotion: PlayerEmotionState, event: dict
) -> PlayerEmotionState:
    """선택 없는 단계(3, 완성 보상)의 효과를 적용한다."""
    return apply_delta(emotion, (event.get("reward") or {}).get("deltas", {}))


# 문서 §3의 8 NPC(맵 등장 매매 에이전트) — 체인 대상.
CHAIN_NPCS = (
    "panic_ant", "fomo_scalper", "conspiracy_influencer", "value_investor",
    "quant_trader", "macro_whale", "contrarian", "jackpot_gambler",
)
_AXES = ("fear", "greed", "anxiety", "restlessness")


class ChainDataError(ValueError):
    """체인 데이터가 스키마를 위반할 때."""


def validate_chains(chains: dict) -> dict:
    """24편 스키마 검증(위반 시 ChainDataError). 통과하면 입력 반환.

    8 NPC × 3단계. 단계1·2 = 선택지 2(A/B, 4축 델타+rapport), 단계3 = 선택지 0
    + reward.deltas. 델타 축은 4축만."""
    for npc in CHAIN_NPCS:
        if npc not in chains:
            raise ChainDataError(f"missing NPC chain: {npc!r}")
    for npc, stages in chains.items():
        for stage in (1, 2, 3):
            if stage not in stages:
                raise ChainDataError(f"{npc}: missing stage {stage}")
        for stage in (1, 2):
            choices = stages[stage].get("choices") or []
            if len(choices) != 2:
                raise ChainDataError(f"{npc} stage{stage}: need 2 choices")
            for ch in choices:
                if not ch.get("id") or not str(ch.get("label", "")).strip():
                    raise ChainDataError(f"{npc} stage{stage}: bad choice")
                for axis in (ch.get("deltas") or {}):
                    if axis not in _AXES:
                        raise ChainDataError(f"{npc} stage{stage}: bad axis {axis!r}")
        s3 = stages[3]
        if s3.get("choices"):
            raise ChainDataError(f"{npc} stage3: must have no choices")
        for axis in ((s3.get("reward") or {}).get("deltas") or {}):
            if axis not in _AXES:
                raise ChainDataError(f"{npc} stage3: bad reward axis {axis!r}")
    return chains


@lru_cache(maxsize=1)
def load_chains() -> dict:
    """24편 체인 데이터(T-20) 로드. {npc_id: {stage(int): event}}.

    파일이 아직 없으면 빈 dict(엔진은 동작하되 체인이 발동하지 않음)."""
    if not CHAINS_PATH.exists():
        return {}
    with open(CHAINS_PATH, encoding="utf-8") as f:
        raw = json.load(f)
    return {
        npc: {int(stage): ev for stage, ev in stages.items()}
        for npc, stages in raw.items()
    }
