"""T-10: NPC 8+8 → 4축 톤 가중치 + 게시판 톤 델타 (얇은 어댑터).

기존 personas.py(매매 5축 + herd/rumor)를 수정하지 않고, 여기서 새 플레이어
4축(fear/greed/anxiety/restlessness) 톤 벡터를 결정론적으로 파생한다. 게시판에
참여한 작성자/댓글자의 톤을 합산해 플레이어 노출 델타에 방향·크기로 얹는다.

파생 규칙(0~1):
  fear         = fear/100
  greed        = greed/100
  anxiety      = rumor            (루머·불확실성 전파 성향)
  restlessness = excitement/100   (조급·안절부절, 매매 충동)
"""

from __future__ import annotations

from .personas import SNS_PERSONAS, TRADER_PERSONAS
from .player_emotion import config

TONE_AXES = ("fear", "greed", "anxiety", "restlessness")

_BY_ID: dict[str, dict] = {p["id"]: p for p in TRADER_PERSONAS + SNS_PERSONAS}

_AUTHOR_WEIGHT = 1.0
_COMMENT_WEIGHT = 0.5


def npc_tone(npc_id: str) -> dict[str, float]:
    """npc_id의 4축 톤 벡터(0~1). 미지의 id(예: 'clone')는 전부 0."""
    p = _BY_ID.get(npc_id)
    if p is None:
        return {a: 0.0 for a in TONE_AXES}
    return {
        "fear": round(p.get("fear", 0) / 100.0, 3),
        "greed": round(p.get("greed", 0) / 100.0, 3),
        "anxiety": round(float(p.get("rumor", 0.0)), 3),
        "restlessness": round(p.get("excitement", 0) / 100.0, 3),
    }


def board_tone_delta(threads: list[dict], scale: float | None = None) -> dict[str, float]:
    """게시판 참여자 톤을 가중 평균해 축별 델타로 만든다(빈 게시판=빈 델타).

    작성자 가중 1.0, 댓글자 0.5. 평균 톤 × config.BOARD_TONE_SCALE.
    크라우드 구성이 공포적이면 fear가, 탐욕적이면 greed가 더 커진다.
    """
    if scale is None:
        scale = config.BOARD_TONE_SCALE

    acc = {a: 0.0 for a in TONE_AXES}
    wsum = 0.0
    for th in threads:
        for author_id, weight in (
            (th.get("author_id"), _AUTHOR_WEIGHT),
            *((c.get("author_id"), _COMMENT_WEIGHT) for c in th.get("comments", [])),
        ):
            tone = npc_tone(author_id)
            for a in TONE_AXES:
                acc[a] += tone[a] * weight
            wsum += weight

    if wsum == 0:
        return {}
    return {a: round(acc[a] / wsum * scale, 2) for a in TONE_AXES}
