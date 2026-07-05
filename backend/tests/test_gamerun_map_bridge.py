"""T-207b · GameRun ↔ 맵 좌표 브릿지 — §12.0 엔진→표현 단방향.

game_run.py는 맵을 모른다(의도적). 이 다리는 market_live_server.py에 산다:
GameRun의 추상 일과(카페/일터/광장/운동/집_차트)를 the_ville 실제 타일 좌표로
바꿔, 기존 Live 클래스가 쓰는 것과 같은 경로탐색(_maze/_blocked_maze/path_finder)
을 **재사용**(Live 인스턴스는 새로 안 건드림 — 순수 유틸이라 독립 함수로 복제).
"""

from __future__ import annotations

import os
import random

import pytest

import market_live_server as mls

# the_ville 맵 에셋(environment/)은 gitignore — 없으면(CI) 맵 의존 테스트만 스킵(T-220 패턴).
_MAZE_META = os.path.join(
    os.path.dirname(__file__), "..", "..",
    "environment", "frontend_server", "static_dirs", "assets", "the_ville",
    "matrix", "maze_meta_info.json",
)
requires_ville = pytest.mark.skipif(
    not os.path.exists(_MAZE_META),
    reason="environment/ 맵 에셋은 gitignore — 로컬 전용(CI엔 없음)",
)


@requires_ville
def test_all_menu_locations_map_to_real_addresses():
    # T-241 — 일과 메뉴 8곳 전부(펍·마켓·도서관 포함) 실주소·실타일이어야 한다.
    from sim.game_run import _MENU
    assert len(_MENU) == 8
    for place in _MENU:
        addr = mls._GAME_LOCATION_ADDR.get(place)
        assert addr, f"{place} 주소 매핑 누락"
        tiles = mls._maze().address_tiles.get(addr)
        assert tiles, f"{place}→{addr} 타일 없음"


@requires_ville
def test_gamerun_rand_tile_for_returns_walkable_tile():
    tile = mls._gamerun_rand_tile_for(mls._GAME_LOCATION_ADDR["카페"], random.Random(1))
    assert tile is not None
    assert mls._gamerun_walkable(tile) is True


@requires_ville
def test_gamerun_path_between_two_addresses():
    rng = random.Random(2)
    a = mls._gamerun_rand_tile_for(mls._GAME_LOCATION_ADDR["집_차트"], rng)
    b = mls._gamerun_rand_tile_for(mls._GAME_LOCATION_ADDR["카페"], rng)
    path = mls._gamerun_path(a, b)
    assert len(path) >= 1
    assert path[0] == tuple(a) or path[-1] == tuple(b)


@requires_ville
def test_gamerun_path_deterministic_by_seed():
    rng1 = random.Random(9)
    t1 = mls._gamerun_rand_tile_for(mls._GAME_LOCATION_ADDR["광장"], rng1)
    rng2 = random.Random(9)
    t2 = mls._gamerun_rand_tile_for(mls._GAME_LOCATION_ADDR["광장"], rng2)
    assert t1 == t2


# --- 엔드포인트 (핸들러 직접호출) ----------------------------------------- #
def _start(gid="map_gr"):
    return mls.control_game_start(mls.GameStartBody(
        game_id=gid, answers={}, symbol="DOGE", start_price=100.0))


@requires_ville
def test_home_endpoint_returns_clone_sprite_and_pos():
    _start("mgr_a")
    r = mls.control_game_home(game_id="mgr_a")
    assert r["status"] == "ok"
    assert r["persona"]["underscore"] == "Isabella_Rodriguez"
    assert len(r["pos"]) == 2


def test_home_endpoint_missing_game():
    assert mls.control_game_home(game_id="nope")["status"] == "error"


@requires_ville
def test_walk_endpoint_returns_steps_first_call():
    _start("mgr_b")
    mls.control_game_home(game_id="mgr_b")  # 초기 위치 확보
    r = mls.control_game_walk(game_id="mgr_b")
    assert r["status"] == "ok"
    assert isinstance(r["steps"], list) and len(r["steps"]) > 0


@requires_ville
def test_walk_endpoint_same_day_returns_empty_cached():
    _start("mgr_c")
    mls.control_game_home(game_id="mgr_c")
    first = mls.control_game_walk(game_id="mgr_c")
    second = mls.control_game_walk(game_id="mgr_c")   # 같은 day, 재호출
    assert len(first["steps"]) > 0
    assert second.get("cached") is True and second["steps"] == []


@requires_ville
def test_walk_endpoint_new_day_after_advance_returns_new_steps():
    _start("mgr_d")
    mls.control_game_home(game_id="mgr_d")
    mls.control_game_walk(game_id="mgr_d")
    mls.control_game_advance(mls.GameAdvanceBody(game_id="mgr_d"))
    r = mls.control_game_walk(game_id="mgr_d")
    assert r["status"] == "ok" and len(r["steps"]) > 0 and not r.get("cached")
