"""T-221 · §9.5.3 매매 에이전트 8종 맵 상시 이동 — 브릿지/엔드포인트 확장.

game_run의 NPC 풀이 personas 모듈로 대체되고, /control/game/day/home·walk가
클론 외 NPC 8종의 스프라이트·위치·그날 경로도 내려준다(맵 표현은 map.html).
순수 연출 — 가격·판정에 영향 없음(부속 PRD §3.1).
"""

from __future__ import annotations

import market_live_server as mls
from sim import game_run, personas

_TRADER_IDS = {p["id"] for p in personas.TRADER_PERSONAS}


def _start(gid: str):
    return mls.control_game_start(mls.GameStartBody(
        game_id=gid, answers={}, symbol="DOGE", start_price=100.0))


def test_game_run_npc_pool_replaced_by_personas():
    # turtle/frog 스텁 제거 — 정의부가 personas 헬퍼와 완전 일치.
    assert game_run._NPC_SCHEDS == personas.npc_scheds()
    assert game_run._NPC_STIM_TRAP == personas.npc_stim_traps()
    assert "turtle" not in game_run._NPC_SCHEDS
    assert "frog" not in game_run._NPC_SCHEDS


def test_home_returns_eight_npc_walkers():
    _start("npcmap_a")
    r = mls.control_game_home(game_id="npcmap_a")
    assert r["status"] == "ok"
    npcs = r["npcs"]
    assert {n["id"] for n in npcs} == _TRADER_IDS
    for n in npcs:
        assert n["sprite"] and n["name"], n["id"]
        assert mls._gamerun_walkable(tuple(n["pos"])), n["id"]


def test_home_npc_positions_deterministic():
    _start("npcmap_b")
    a = mls.control_game_home(game_id="npcmap_b")
    b = mls.control_game_home(game_id="npcmap_b")
    assert a["npcs"] == b["npcs"]


def test_walk_returns_npc_steps_and_day_caches():
    _start("npcmap_c")
    mls.control_game_home(game_id="npcmap_c")
    first = mls.control_game_walk(game_id="npcmap_c")
    assert first["status"] == "ok"
    assert set(first["npcs"]) == _TRADER_IDS
    # 스케줄이 있으니 최소 한 명은 실제로 움직인다.
    assert any(len(steps) > 0 for steps in first["npcs"].values())
    for steps in first["npcs"].values():
        for xy in steps:
            assert len(xy) == 2
    second = mls.control_game_walk(game_id="npcmap_c")
    assert second.get("cached") is True and second["npcs"] == {}


def test_walk_new_day_moves_npcs_again():
    _start("npcmap_d")
    mls.control_game_home(game_id="npcmap_d")
    mls.control_game_walk(game_id="npcmap_d")
    mls.control_game_advance(mls.GameAdvanceBody(game_id="npcmap_d"))
    r = mls.control_game_walk(game_id="npcmap_d")
    assert not r.get("cached")
    assert set(r["npcs"]) == _TRADER_IDS


# --- T-237 · §12.1b 시간대 동기화 — 경로를 4구간(오전/점심/오후/저녁)으로 ------ #
_BANDS = ("오전", "점심", "오후", "저녁")


def test_walk_returns_time_band_segments():
    _start("npcmap_e")
    r = mls.control_game_walk(game_id="npcmap_e")
    assert list(r["segments"].keys()) == list(_BANDS)
    # flat steps는 구간들의 순차 연결과 정확히 일치(하위호환 정합).
    concat = [xy for band in _BANDS for xy in r["segments"][band]]
    assert concat == r["steps"]
    # NPC도 같은 구간 구조.
    assert set(r["npc_segments"]) == _TRADER_IDS
    for bands in r["npc_segments"].values():
        assert list(bands.keys()) == list(_BANDS)
    for nid in _TRADER_IDS:
        concat_n = [xy for band in _BANDS for xy in r["npc_segments"][nid][band]]
        assert concat_n == r["npcs"][nid]


def test_walk_segments_cached_same_day():
    _start("npcmap_f")
    mls.control_game_walk(game_id="npcmap_f")
    again = mls.control_game_walk(game_id="npcmap_f")
    assert again.get("cached") is True
    assert all(v == [] for v in again["segments"].values())


def test_home_returns_place_labels():
    # T-240 — 맵 장소 라벨: 장소명+대표 좌표. 클론 집은 박제 홈 타일과 일치.
    _start("npcmap_h")
    r = mls.control_game_home(game_id="npcmap_h")
    places = {p["name"]: p["pos"] for p in r["places"]}
    assert "카페" in places and "일터" in places and "광장" in places
    assert places["집"] == mls._GAME_WALKERS["npcmap_h"]["home"]
    for pos in places.values():
        assert len(pos) == 2


def test_clone_returns_to_the_same_home_every_day():
    # T-239 — 시작 집은 랜덤이어도 한 게임 안에선 매일 같은 집으로 귀가한다
    # (기존엔 귀가 타일을 day-시드 난수로 뽑아 다른 집으로 들어가는 날이 있었다).
    _start("npcmap_g")
    d0 = mls.control_game_walk(game_id="npcmap_g")   # 워커는 첫 호출에서 생성됨
    home = list(mls._GAME_WALKERS["npcmap_g"]["home"])
    assert d0["steps"][-1] == home
    mls.control_game_advance(mls.GameAdvanceBody(game_id="npcmap_g"))
    d1 = mls.control_game_walk(game_id="npcmap_g")
    assert d1["steps"][-1] == home                 # 다음 날도 같은 집
