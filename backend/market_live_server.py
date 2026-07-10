"""Market Village LIVE server.

감정 4축 미연시 게임(``backend.sim.emo_game.EmoGameRun``, 라우터 ``sim.emo_api``)이
유일한 게임 경로다. Next.js 루트 ``/`` → ``/emo``가 소비한다. 구 "AI 클론 30일
관찰" 엔진(``sim.game_run.GameRun``)과 ``/control/*`` 라우트 일체는 T-15 컷오버에서
완전히 제거됐다(2026-07-08) — emo 게임이 유일 진입점이라 병행 유지할 이유가 없어짐.

reverie의 ``Maze``+``path_finder``는 지도 경로탐색 유틸로만 재사용한다(the_ville
타일맵) — ``/emo/{id}/map/{home,walk,approach}``(§12.0 EmoGameRun↔맵 좌표 브릿지)가
이걸 쓴다. reverie의 인지 루프 자체는 안 쓴다.

Run from backend/:
    cd backend && python -m uvicorn market_live_server:app --port 8100
"""

from __future__ import annotations

import os
import random
import sys
import zlib
from os.path import abspath, dirname, join, normpath

# Everything lives in backend/ now (no reverie folder). maze/path_finder/utils
# are the_ville map utilities kept alongside the game logic (backend.sim).
_HERE = dirname(abspath(__file__))            # backend/
_REPO = normpath(join(_HERE, ".."))           # repo root
sys.path.insert(0, _HERE)                     # maze / path_finder / utils (local)
sys.path.insert(0, _REPO)                     # backend.sim

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from maze import Maze  # noqa: E402  (the_ville map util)
from path_finder import path_finder  # noqa: E402  (path util)
from utils import collision_block_id  # noqa: E402  (config)

from backend.sim import personas as _personas  # noqa: E402  (맵 브리지·NPC 일과)
from backend.sim import emo_api as _emo_api  # noqa: E402  (감정 4축 게임 라우터 — 유일 게임 경로)
from backend.sim import emo_store as _emo_store  # noqa: E402  (맵 브리지가 emo 게임 조회)


# the_ville 정적 자원(맵 이미지·스프라이트) — /emo/{id}/map/{home,walk}(§12.0)의
# 맵 표현 계층이 쓴다.
ASSETS_DIR = join(_REPO, "environment", "frontend_server", "static_dirs", "assets")

# --------------------------------------------------------------------------- #
# App + shared state
# --------------------------------------------------------------------------- #
app = FastAPI(title="Market Village Live")
app.include_router(_emo_api.router)   # /emo/* — 감정 4축 게임(유일 게임 경로, 프론트 /emo)

# Pre-warm the sentiment model so the first event doesn't pay the load cost.
import threading
threading.Thread(
    target=lambda: __import__("backend.sim.sentiment", fromlist=["_get_pipeline"])._get_pipeline(),
    daemon=True,
).start()

# mvp니까~
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"], allow_headers=["*"],
)
if os.path.isdir(ASSETS_DIR):
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")

# T-FE2: the_ville 배경 지도(순수 캔버스, Next.js MapBackground가 iframe으로 embed).
_MAP_PATH = join(_HERE, "static_demo", "map.html")


@app.get("/map")
def map_client():
    from fastapi.responses import HTMLResponse
    try:
        with open(_MAP_PATH, encoding="utf-8") as f:
            return HTMLResponse(f.read())
    except FileNotFoundError:
        return HTMLResponse("<h1>map not found</h1>", status_code=404)


_MAZE: Maze | None = None
_BLOCKED_MAZE: list | None = None

# C-018: game_object_blocks.csv 기준 진열대/책장 5종. the_ville collision_maze는
# 벽만 막고 이 가구들은 비워 둬서 캐릭터가 통과했다. 경로탐색용 충돌맵에만 막아
# 캐릭터가 책장/진열대 위를 가로지르지 못하게 한다(공유 CSV는 무수정).
SOLID_OBJECTS = {
    "shelf",
    "bookshelf",
    "pharmacy store shelf",
    "grocery store shelf",
    "supply store product shelf",
}


def _maze() -> Maze:
    global _MAZE
    if _MAZE is None:
        _MAZE = Maze("the_ville")
    return _MAZE


def _blocked_maze() -> list:
    """collision_maze ∪ {SOLID_OBJECTS 가구 타일} 보강 충돌맵 (캐시).

    원본 collision_maze를 복사해 진열대/책장 타일을 collision_block_id로 막는다.
    path_finder는 값이 collision_block_id인 칸만 벽으로 보므로 형식을 그대로 둔다.
    """
    global _BLOCKED_MAZE
    if _BLOCKED_MAZE is None:
        m = _maze()
        cid = str(collision_block_id)
        grid = [list(row) for row in m.collision_maze]
        for y in range(m.maze_height):
            for x in range(m.maze_width):
                if m.tiles[y][x]["game_object"] in SOLID_OBJECTS:
                    grid[y][x] = cid
        _BLOCKED_MAZE = grid
    return _BLOCKED_MAZE


# --------------------------------------------------------------------------- #
# T-207b — GameRun ↔ 맵 좌표 브릿지 (§12.0 엔진→표현 단방향).
# game_run.py는 맵을 모른다(의도적, 모듈 docstring 참고). 여기 이 표현 계층에서만
# GameRun의 추상 일과를 the_ville 실좌표로 바꾼다. Live 클래스 인스턴스는 건드리지
# 않는다 — 아래는 그 클래스의 _walkable/_rand_tile_for/_path와 같은 로직이지만
# 인스턴스 상태가 전혀 필요 없는 순수 유틸이라 독립 함수로 둔다(수술하듯).
# --------------------------------------------------------------------------- #
_GAME_LOCATION_ADDR = {
    "카페": "the Ville:Hobbs Cafe:cafe",
    "일터": "the Ville:Harvey Oak Supply Store:supply store",
    "광장": "the Ville:Johnson Park:park",
    "운동": "the Ville:Johnson Park:park",   # 전용 체육시설 자산 없음 — 공원 재사용
    "집_차트": "<spawn_loc>sp-A",
    # T-241 — the_ville 미사용 장소 활용(일과 8곳 확장).
    "펍": "the Ville:The Rose and Crown Pub:pub",
    "마켓": "the Ville:The Willows Market and Pharmacy:store",
    "도서관": "the Ville:Oak Hill College:library",
}
_GAME_CLONE_SPRITE = "Isabella_Rodriguez"   # interview.py의 거울 클론과 동일 스프라이트
# game_id → {"pos": [x,y], "day": int, "npcs": {npc_id: [x,y]}} (T-221 NPC 상시 이동)
_GAME_WALKERS: dict[str, dict] = {}


def _gamerun_walkable(tile) -> bool:
    if tile is None:
        return False
    x, y = tile
    try:
        return str(_blocked_maze()[y][x]) != str(collision_block_id)
    except Exception:
        return False


def _gamerun_rand_tile_for(address: str, rng: random.Random):
    tiles = _maze().address_tiles.get(address)
    if not tiles:
        return None
    # T-24 — walkable 타일만 반환한다. non-walkable 목적지는 path_finder를 실패시켜
    # 직선 폴백(벽 통과)을 유발하므로, 후보가 없으면 차라리 None(상위가 건너뜀).
    candidates = [t for t in sorted(tiles) if _gamerun_walkable(t)]
    return rng.choice(candidates) if candidates else None


def _gamerun_path(a, b) -> list[tuple[int, int]]:
    if a is None or b is None:
        return []
    try:
        p = path_finder(_blocked_maze(), list(a), list(b), collision_block_id)
        return [(t[0], t[1]) for t in p]
    except Exception:
        # T-24 — 길찾기 실패 시 직선 [a,b]를 주면 map.html이 그 사이를 직선 보간해
        # 벽을 통과한다(표현 계층엔 충돌 데이터가 없음). 빈 경로를 줘 상위(_walk_via)가
        # 순간이동 없이 목표를 건너뛰게 한다.
        return []


def _walker_seed(*parts) -> int:
    """워커용 고정 시드 — hash()는 프로세스마다 소금이 달라 재시작 안정성이 없음
    (_news_seed와 같은 이유로 crc32, /review에서 일관성 지적)."""
    return zlib.crc32(":".join(str(p) for p in parts).encode())


def _ensure_game_walker(game_id: str, npc_scheds: dict | None = None) -> dict:
    """클론+NPC 워커 상태 초기화(결정론) — home/walk 어느 쪽이 먼저 와도 동일.

    T-273 — NPC 일과는 게임의 npc_scheds(마을 프리셋 반영)를 단일 소스로 쓴다.
    판정(overlap_meetings)과 연출(맵 경로)이 갈라지던 잠재 불일치의 해소이기도.
    """
    walker = _GAME_WALKERS.setdefault(game_id, {"pos": None, "day": -1, "npcs": {}})
    walker.setdefault("npcs", {})  # T-221 이전에 만들어진 워커 하위호환
    if walker["pos"] is None:
        rng = random.Random(_walker_seed("walker", game_id))
        home_tile = _gamerun_rand_tile_for(_GAME_LOCATION_ADDR["집_차트"], rng)
        walker["pos"] = list(home_tile) if home_tile else [70, 40]
    # T-239 — 집 타일은 게임당 1회 뽑아 박제(시작은 랜덤, 게임 내내 같은 집으로 귀가).
    walker.setdefault("home", list(walker["pos"]))
    # NPC 시작 위치 = 마을 공용 장소 중 게임별 랜덤(사용자 요청 — 매 게임 다른 배치).
    # 집(스폰 영역)은 제외해 고정 유지. 시드가 game_id 기반이라 리로드엔 결정론.
    spawn_places = [a for k, a in _GAME_LOCATION_ADDR.items() if k != "집_차트"]
    for p in _personas.TRADER_PERSONAS:
        if p["id"] in walker["npcs"]:
            continue
        rng_n = random.Random(_walker_seed("walker", game_id, p["id"]))
        tile = _gamerun_rand_tile_for(rng_n.choice(spawn_places), rng_n)
        walker["npcs"][p["id"]] = list(tile) if tile else [70, 40]
    return walker


def _walk_via(cur: tuple, targets: list, rng: random.Random,
              ) -> tuple[list[list[int]], tuple, list[int | None]]:
    """목표들을 차례로 들르는 타일 경로(steps)와 최종 위치를 반환.

    목표는 주소 문자열(영역 내 임의 타일) 또는 정확한 타일 tuple(T-239 — 집처럼
    게임 내 고정이어야 하는 지점). T-296 — 목표별 도착 인덱스(steps 내 위치,
    해석 실패 목표는 None)를 함께 반환해 연출이 장소마다 멈춰 행동할 수 있게.
    """
    steps: list[list[int]] = []
    arrive: list[int | None] = []
    for tgt in targets:
        dest = tgt if isinstance(tgt, tuple) else _gamerun_rand_tile_for(tgt, rng)
        if dest is None:
            arrive.append(None)
            continue
        seg = _gamerun_path(cur, dest)
        if len(seg) > 1:
            steps.extend([list(t) for t in seg[1:]])
            cur = dest
            arrive.append(len(steps))
        elif tuple(cur) == tuple(dest):
            arrive.append(len(steps))   # 이미 그 자리 — 이동 없음, 행동은 재생
        else:
            # T-24 — 길찾기 실패(도달 불가). cur를 dest로 옮기면 다음 목표가 여기서
            # 길을 찾아 화면상 순간이동(벽 통과)이 된다 → cur 유지, 이 목표만 건너뜀.
            arrive.append(None)
    return steps, cur, arrive


# T-237 §12.1b — 8슬롯을 4시간대로 묶는다(슬롯 1·2=오전 … 7·8=저녁, day_loop와 동일).
_WALK_BANDS: tuple[tuple[str, tuple[int, int]], ...] = (
    ("오전", (1, 2)), ("점심", (3, 4)), ("오후", (5, 6)), ("저녁", (7, 8)))


def _meeting_approach(npc_tile: tuple, clone_tile: tuple) -> list[list[int]]:
    """T-299(사용자 "포켓몬처럼 가까이서 마주봐야 대화") — NPC가 클론 **옆 칸**까지
    실 길찾기로 걸어오는 경로. 이미 인접이면 빈 경로. 표현 계층 전용.

    기존 map.html의 L자 직선 휴리스틱(벽 무시·12타일 캡)을 대체 — 목적지는
    클론 4방 이웃 중 walkable하면서 NPC에 가장 가까운 타일.
    """
    if abs(npc_tile[0] - clone_tile[0]) + abs(npc_tile[1] - clone_tile[1]) <= 1:
        return []
    neighbors = [(clone_tile[0] + dx, clone_tile[1] + dy)
                 for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))]
    goals = sorted(
        (t for t in neighbors if _gamerun_walkable(t)),
        key=lambda t: abs(t[0] - npc_tile[0]) + abs(t[1] - npc_tile[1]))
    for goal in goals:
        seg = _gamerun_path(tuple(npc_tile), goal)
        if len(seg) > 1:
            return [list(t) for t in seg[1:]]
        if len(seg) == 1 and tuple(seg[0]) == goal:
            return []
    return []


def _banded_route(
    sched: dict[int, str], cur: tuple, rng: random.Random,
    home_tile: tuple | None = None,
) -> tuple[dict[str, list[list[int]]], tuple, dict[str, list[dict]]]:
    """일과를 시간대별 경로 구간으로 — 연출이 하루 단계와 동기화되도록(T-237).

    home_tile이 주어지면(클론) 저녁 구간 끝에 그 타일로 귀가한다 — 주소 영역 내
    임의 타일이 아니라 게임 내 고정된 '내 집'(T-239, 매일 같은 집으로). 일과 중
    집_차트 슬롯도 같은 타일을 쓴다. 구간 안에서만 연속 중복 목표를 접는다.

    T-296 — 밴드별 stops([{place, i}])도 반환: 들르는 장소마다 도착 인덱스를
    표시해, 연출이 각 장소에서 최소 1가지 행동을 재생할 수 있게(사용자 요청).
    """
    home_addr = _GAME_LOCATION_ADDR["집_차트"]
    segments: dict[str, list[list[int]]] = {}
    stops: dict[str, list[dict]] = {}
    for band, slots in _WALK_BANDS:
        targets: list = []
        names: list[str] = []
        for slot in slots:
            place = sched.get(slot, "")
            addr = _GAME_LOCATION_ADDR.get(place)
            if not addr:
                continue
            tgt = home_tile if (home_tile is not None and addr == home_addr) else addr
            if not targets or targets[-1] != tgt:
                targets.append(tgt)
                names.append(place)
        if band == "저녁" and home_tile is not None:
            if not targets or targets[-1] != home_tile:
                targets.append(home_tile)
                names.append("집_차트")
        segments[band], cur, arrive = _walk_via(cur, targets, rng)
        stops[band] = [{"place": n, "i": i}
                       for n, i in zip(names, arrive) if i is not None]
    return segments, cur, stops


def _place_labels(walker: dict) -> list[dict]:
    """T-240 — 맵 장소 라벨: 장소명 + 대표 좌표(주소 타일 중심점).

    운동은 광장과 같은 공원(주소 중복)이라 한 라벨로 접고, 집은 이 게임의
    박제 홈 타일(T-239)을 그대로 쓴다.
    """
    out: list[dict] = []
    seen_addrs: set[str] = set()
    for place in ("카페", "일터", "광장", "펍", "마켓", "도서관"):
        addr = _GAME_LOCATION_ADDR[place]
        if addr in seen_addrs:
            continue
        seen_addrs.add(addr)
        tiles = sorted(_maze().address_tiles.get(addr, []))
        if not tiles:
            continue
        cx = round(sum(t[0] for t in tiles) / len(tiles))
        cy = round(sum(t[1] for t in tiles) / len(tiles))
        out.append({"name": place, "pos": [cx, cy]})
    out.append({"name": "집", "pos": list(walker["home"])})
    return out


# --------------------------------------------------------------------------- #
# T-22 — 이동 맵을 새 감정 게임(EmoGameRun)에 연결.
# 위 GameRun용 좌표 브릿지(_ensure_game_walker/_banded_route/_meeting_approach/
# _place_labels)를 그대로 재사용한다 — game_id·8슬롯 스케줄·npc_scheds만 소비하므로
# 게임 무관. EmoGameRun은 하루 장소 1개라 day_schedule()이 8슬롯으로 확장해준다.
# 구 /control/game/day/* 와 map.html classic 경로는 무수정(신규 엔드포인트로 additive).
# --------------------------------------------------------------------------- #
def _emo_meetings(run) -> dict:
    """오늘 companion을 맵 만남으로(오후 밴드·그날 장소). 대사=체인은 Phase 3."""
    out: dict[str, list] = {b: [] for b, _ in _WALK_BANDS}
    npc = run.companion_id
    if npc:
        place = run.clone_route[run.day] if run.day < len(run.clone_route) else ""
        p = _personas.trader_by_id(npc)
        out["오후"].append({
            "id": npc, "name": p["name"] if p else npc,
            "role": p["role"] if p else "", "portrait": p["portrait"] if p else None,
            "place": place, "lines": [],
            "has_chain": run.pending_chain is not None})
    return out


@app.get("/emo/{game_id}/map/home")
def emo_map_home(game_id: str):
    """EmoGameRun 맵 부트스트랩 — 클론+NPC 스프라이트·초기 좌표·장소 라벨."""
    run = _emo_store.load_run(game_id)
    if run is None:
        return {"status": "error", "error": "no game"}
    walker = _ensure_game_walker(game_id, run.schedules)
    start = walker.get("day_start") if walker.get("day") == run.day else None
    pos = start["pos"] if start else walker["pos"]
    npcs = [
        {"id": p["id"], "name": p["name"], "sprite": p["sprite"],
         "pos": (start["npcs"].get(p["id"]) if start else None) or walker["npcs"][p["id"]]}
        for p in _personas.TRADER_PERSONAS]
    return {"status": "ok",
            "persona": {"original": "gamerun_clone", "underscore": _GAME_CLONE_SPRITE,
                        "initial": run.clone_name},   # T-28 — 맵 네임플레이트=클론 이름
            "pos": pos, "npcs": npcs, "places": _place_labels(walker)}


@app.get("/emo/{game_id}/map/walk")
def emo_map_walk(game_id: str):
    """그날 동선(8슬롯)을 실좌표 경로로 — 구 walk와 동일 계약, EmoGameRun 소스."""
    run = _emo_store.load_run(game_id)
    if run is None:
        return {"status": "error", "error": "no game"}
    walker = _ensure_game_walker(game_id, run.schedules)
    band_names = [b for b, _ in _WALK_BANDS]
    sched = run.day_schedule()
    if walker["day"] == run.day:
        if walker.get("day_resp"):
            return {**walker["day_resp"], "cached": True}
        return {"status": "ok", "steps": [], "npcs": {}, "cached": True,
                "segments": {b: [] for b in band_names},
                "stops": {b: [] for b in band_names},
                "npc_segments": {p["id"]: {b: [] for b in band_names}
                                 for p in _personas.TRADER_PERSONAS},
                "plan": {band: [sched[s] for s in slots if sched.get(s)]
                         for band, slots in _WALK_BANDS},
                "meetings_by_band": _emo_meetings(run)}
    day_start = {"pos": list(walker["pos"]),
                 "npcs": {p["id"]: list(walker["npcs"][p["id"]])
                          for p in _personas.TRADER_PERSONAS}}
    rng = random.Random(_walker_seed("emo_walk", game_id, run.day))
    segments, cur, stops = _banded_route(sched, tuple(walker["pos"]), rng,
                                         home_tile=tuple(walker["home"]))
    walker["pos"] = list(cur)
    steps = [xy for b in band_names for xy in segments[b]]
    npc_steps: dict[str, list[list[int]]] = {}
    npc_segments: dict[str, dict[str, list[list[int]]]] = {}
    for p in _personas.TRADER_PERSONAS:
        rng_n = random.Random(_walker_seed("emo_walk", game_id, p["id"], run.day))
        segs_n, n_cur, _s = _banded_route(
            run.schedules.get(p["id"], p["sched"]),
            tuple(walker["npcs"][p["id"]]), rng_n, home_tile=None)
        npc_segments[p["id"]] = segs_n
        npc_steps[p["id"]] = [xy for b in band_names for xy in segs_n[b]]
        walker["npcs"][p["id"]] = list(n_cur)
    walker["day"] = run.day
    plan = {band: [sched[s] for s in slots if sched.get(s)]
            for band, slots in _WALK_BANDS}
    meetings = _emo_meetings(run)
    pos_c = list(day_start["pos"])
    pos_n = {p["id"]: list(day_start["npcs"][p["id"]]) for p in _personas.TRADER_PERSONAS}
    for band in band_names:
        if segments[band]:
            pos_c = list(segments[band][-1])
        for nid, segs_b in npc_segments.items():
            if segs_b[band]:
                pos_n[nid] = list(segs_b[band][-1])
        for m in meetings[band]:
            m["approach"] = _meeting_approach(tuple(pos_n.get(m["id"], pos_c)), tuple(pos_c))
    resp = {"status": "ok", "steps": steps, "npcs": npc_steps,
            "segments": segments, "npc_segments": npc_segments, "plan": plan,
            "stops": stops, "meetings_by_band": meetings}
    walker["day_start"] = day_start
    walker["day_resp"] = resp
    return resp


@app.get("/emo/{game_id}/map/approach")
def emo_map_approach(game_id: str, fx: int, fy: int, cx: int, cy: int):
    """만남 시 NPC→클론 옆칸 실 길찾기(구 approach와 동일). 순수."""
    return {"steps": _meeting_approach((fx, fy), (cx, cy))}
