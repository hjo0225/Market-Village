"""T-24 · /emo 클론·NPC 이동 경로 벽 통과 방지 — 백엔드 경로 계약.

map.html은 충돌 데이터가 없는 표현 계층이라, 벽 정합은 전적으로 백엔드가 주는
타일 경로에 달렸다(map.html은 연속 타일을 직선 보간할 뿐). 이 테스트는 emo 걷기
응답의 연속 타일이 (1) 서로 인접(맨해튼 ≤1)하고 (2) 모두 walkable 임을 고정한다 —
비인접 점프(_gamerun_path 직선 폴백)나 non-walkable 타일은 맵에서 벽 통과로 보인다.
"""

from __future__ import annotations

import os

import pytest

import market_live_server as mls

# the_ville 맵 에셋(environment/)은 gitignore — 없으면(CI) 스킵(기존 브릿지 테스트 패턴).
_MAZE_META = os.path.join(
    os.path.dirname(__file__), "..", "..",
    "environment", "frontend_server", "static_dirs", "assets", "the_ville",
    "matrix", "maze_meta_info.json",
)
requires_ville = pytest.mark.skipif(
    not os.path.exists(_MAZE_META),
    reason="environment/ 맵 에셋은 gitignore — 로컬 전용(CI엔 없음)",
)

_SEEDS = [1, 2, 3, 7, 11, 42, 99]


def _emo_start(seed: int) -> str:
    st = mls._emo_api.start(mls._emo_api.StartBody(answers={}, seed=seed, days=10))
    return st["game_id"]


def _assert_contiguous_walkable(steps, who: str) -> None:
    for i, (x, y) in enumerate(steps):
        assert mls._gamerun_walkable((x, y)), f"{who} 스텝 {i} 비-walkable 타일 {(x, y)}"
    for i in range(1, len(steps)):
        x0, y0 = steps[i - 1]
        x1, y1 = steps[i]
        assert abs(x1 - x0) + abs(y1 - y0) <= 1, (
            f"{who} 스텝 {i - 1}->{i} 비인접 점프 {(x0, y0)}->{(x1, y1)} (벽 통과)"
        )


@requires_ville
@pytest.mark.parametrize("seed", _SEEDS)
def test_emo_clone_route_is_contiguous_and_walkable(seed):
    gid = _emo_start(seed)
    mls.emo_map_home(game_id=gid)
    walk = mls.emo_map_walk(game_id=gid)
    assert walk["status"] == "ok"
    steps = walk["steps"]
    if steps:
        home = mls.emo_map_home(game_id=gid)   # walk 소비 후엔 하루 시작 위치
        px, py = home["pos"]
        sx, sy = steps[0]
        assert abs(sx - px) + abs(sy - py) <= 1, (
            f"clone(seed={seed}) 시작→첫스텝 순간이동 {(px, py)}->{(sx, sy)}"
        )
    _assert_contiguous_walkable(steps, f"clone(seed={seed})")


@requires_ville
@pytest.mark.parametrize("seed", _SEEDS)
def test_emo_npc_routes_are_contiguous_and_walkable(seed):
    gid = _emo_start(seed)
    mls.emo_map_home(game_id=gid)
    walk = mls.emo_map_walk(game_id=gid)
    for nid, steps in (walk["npcs"] or {}).items():
        _assert_contiguous_walkable(steps, f"npc {nid}(seed={seed})")
