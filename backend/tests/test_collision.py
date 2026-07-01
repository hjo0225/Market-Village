"""C-018 가구 충돌 처리: 진열대/책장 5종을 경로탐색 충돌로 처리.

캐릭터 이동은 서버가 path_finder(보강 충돌맵)로 짠 좌표를 프론트가 보간만 한다.
원본 the_ville collision_maze는 벽만 막고 가구(책장·진열대)는 비워 둬서 캐릭터가
그 위를 통과했다. 보강 충돌맵이 5종 진열대/책장 타일을 막는지, 그리고 그 결과
경로가 가구를 지나지 않으면서도 목적지에는 여전히 도달 가능한지 검증한다.
"""

from __future__ import annotations

import random

import market_live_server as mls


# game_object_blocks.csv 기준 진열대/책장 5종 (id: 32257/32250/32231/32241/32271)
SHELVES = {
    "shelf",
    "bookshelf",
    "pharmacy store shelf",
    "grocery store shelf",
    "supply store product shelf",
}


def _shelf_tiles():
    m = mls._maze()
    tiles = []
    for y in range(m.maze_height):
        for x in range(m.maze_width):
            if m.tiles[y][x]["game_object"] in SHELVES:
                tiles.append((x, y))
    return tiles


def test_solid_objects_covers_five_shelf_types():
    assert mls.SOLID_OBJECTS == SHELVES


def test_shelf_tiles_blocked_in_augmented_maze():
    blocked = mls._blocked_maze()
    raw = mls._maze().collision_maze
    shelves = _shelf_tiles()
    assert len(shelves) > 0  # 맵에 진열대/책장이 실제로 존재
    cid = str(mls.collision_block_id)
    # 원본 collision_maze에서는 가구가 막혀 있지 않았다 (이 버그의 전제)
    assert any(str(raw[y][x]) != cid for (x, y) in shelves)
    # 보강 충돌맵에서는 모든 진열대/책장이 막혀 있다
    for (x, y) in shelves:
        assert str(blocked[y][x]) == cid, f"shelf tile {(x, y)} not blocked"


def test_paths_never_cross_shelves():
    blocked = mls._blocked_maze()
    cid = mls.collision_block_id
    shelf_set = set(_shelf_tiles())
    m = mls._maze()

    # 보강 충돌맵에서 걸을 수 있는 타일만 출발/도착 후보로
    walkable = [
        (x, y)
        for y in range(m.maze_height)
        for x in range(m.maze_width)
        if str(blocked[y][x]) != str(cid)
    ]
    rng = random.Random(1234)
    nontrivial = 0
    for _ in range(60):
        a = rng.choice(walkable)
        b = rng.choice(walkable)
        path = mls.path_finder(blocked, list(a), list(b), cid)
        if len(path) > 2:
            nontrivial += 1
        for t in path:
            assert tuple(t) not in shelf_set, f"path {a}->{b} crosses shelf {t}"
    assert nontrivial > 0  # 실제로 경로탐색이 일하는 케이스가 있었다
