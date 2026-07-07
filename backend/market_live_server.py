"""Market Village LIVE server.

신 엔진 정본(``backend.sim.game_run.GameRun``)이 유일한 게임 경로다(§12.4,
Next.js ``/play``가 소비). 구 엔진(``sim.engine.GameSession``, 마을 NPC 라운드
모델)은 2026-07-01 실서비스 전환 정리에서 완전히 제거됐다(``/game``·``/demo``
위젯과 함께 — Next.js가 이미 유일 진입점이라 병행 유지할 이유가 없어짐).

reverie의 ``Maze``+``path_finder``는 지도 경로탐색 유틸로만 재사용한다(the_ville
타일맵) — ``/control/game/day/{home,walk}``(§12.0 GameRun↔맵 좌표 브릿지)가 이걸
쓴다. reverie의 인지 루프 자체는 안 쓴다.

Run from backend/:
    cd backend && python -m uvicorn market_live_server:app --port 8100
"""

from __future__ import annotations

import dataclasses
import json
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
from pydantic import BaseModel  # noqa: E402

from maze import Maze  # noqa: E402  (the_ville map util)
from path_finder import path_finder  # noqa: E402  (path util)
from utils import collision_block_id  # noqa: E402  (config)

from backend.sim import news as _news  # noqa: E402
from backend.sim import personas as _personas  # noqa: E402
from backend.sim import meeting_talk as _meeting_talk  # noqa: E402  (T-281)
from backend.sim import npc_traders as _npc_traders  # noqa: E402
from backend.sim import clone_stats as _clone_stats  # noqa: E402
from backend.sim import clone_spec as _clone_spec  # noqa: E402
from backend.sim import result_card as _result_card  # noqa: E402
from backend.sim import runs as _runs  # noqa: E402
from backend.sim import db as _db  # noqa: E402  (T-DB 게임 세션 영속화, 실패시 인메모리 폴백)
from backend.sim import emo_api as _emo_api  # noqa: E402  (신 감정 4축 게임 라우터, 컷오버 시 구 라우터 대체)
from backend.sim import emo_store as _emo_store  # noqa: E402  (T-22 맵 브릿지가 emo 게임 조회)
from backend.sim.trap_pipeline import Intervention as _Intervention  # noqa: E402
from backend.sim.traps import get_trap as _traps_get  # noqa: E402
from backend.sim.game_run import GameRun as _GameRun  # noqa: E402
from backend.sim import presentation as _presentation  # noqa: E402
from backend.sim import interview_llm as _interview_llm  # noqa: E402
from backend.sim.interview import question_by_id as _question_by_id  # noqa: E402
from backend.sim.fate_line import category_for_symbol as _category_for_symbol  # noqa: E402
from backend.sim import tuning as _T  # noqa: E402

# T-302(사용자) — 서비스 시뮬레이션 길이. 엔진 GameRun 기본값(30)과 별개로
# 서비스 계층이 명시 전달한다(운명선 시드는 30일 그대로 — 앞 10일만 사용).
GAME_DAYS = 10

# §12.4 step-able GameRun 세션 맵 (game_id → GameRun). 신 엔진 정본 플레이 경로.
# 이게 항상 1차 진실 소스 — MongoDB(T-DB)는 서버 재시작 후 재개용 보조 저장소일 뿐.
_GAMES: dict[str, _GameRun] = {}
# §5.3 대화형 인터뷰 세션 맵 (session_id → 지금까지 답변). 게임 시작 전 독립 진행.
_INTERVIEWS: dict[str, dict] = {}


def _get_game(game_id: str) -> "_GameRun | None":
    """인메모리 우선, 없으면(서버 재시작 등) MongoDB에서 재구성 시도(T-DB)."""
    g = _GAMES.get(game_id)
    if g is not None:
        return g
    doc = _db.load_game(game_id)
    if doc is None:
        return None
    g = _GameRun.from_doc(doc)
    _GAMES[game_id] = g
    return g


def _persist_game(game_id: str, g: "_GameRun") -> None:
    """실패해도 무시(인메모리가 진실 소스 — DB는 재개용 보조일 뿐)."""
    _db.save_game(game_id, g.to_doc())


# the_ville 정적 자원(맵 이미지·스프라이트) — /control/game/day/{home,walk}(§12.0)의
# 맵 표현 계층이 쓴다.
ASSETS_DIR = join(_REPO, "environment", "frontend_server", "static_dirs", "assets")

# --------------------------------------------------------------------------- #
# App + shared state
# --------------------------------------------------------------------------- #
app = FastAPI(title="Market Village Live")
app.include_router(_emo_api.router)   # /emo/* — 신 감정 4축 게임(프론트 /play 브릿지)

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
    candidates = [t for t in sorted(tiles) if _gamerun_walkable(t)]
    return rng.choice(candidates or sorted(tiles))


def _gamerun_path(a, b) -> list[tuple[int, int]]:
    if a is None or b is None:
        return []
    try:
        p = path_finder(_blocked_maze(), list(a), list(b), collision_block_id)
        return [(t[0], t[1]) for t in p]
    except Exception:
        return [tuple(a), tuple(b)]


def _walker_seed(*parts) -> int:
    """워커용 고정 시드 — hash()는 프로세스마다 소금이 달라 재시작 안정성이 없음
    (_news_seed와 같은 이유로 crc32, /review에서 일관성 지적)."""
    return zlib.crc32(":".join(str(p) for p in parts).encode())


def _meetings_by_band(g: "_GameRun", game_id: str = "") -> dict:
    """T-249 — 오늘의 만남(픽)을 시간대별로(맵 대화 연출용). 순수 조회.

    T-281 — 폰 채팅창용 role·portrait·lines(결정론 대사) 동봉(사용자 반복
    피드백: 1:1 대화는 맵 말풍선이 아니라 핸드폰 채팅으로).
    """
    band_names = [b for b, _ in _WALK_BANDS]
    out: dict[str, list] = {b: [] for b in band_names}
    prev = g.preview_day()
    stats = dict(getattr(g, "stats", None) or {})
    for slot, pick in (prev.get("picks") or {}).items():
        if not pick:
            continue
        band = band_names[(int(slot) - 1) // 2]
        p = _personas.trader_by_id(pick)
        out[band].append({
            "id": pick,
            "name": p["name"] if p else pick,
            "role": p["role"] if p else "",
            "portrait": p["portrait"] if p else None,
            # T-304 — 만남 슬롯의 장소: 맵이 밴드 끝이 아니라 이 장소 stop에서 연다.
            "place": g.schedule.get(int(slot), ""),
            "lines": _meeting_talk.dialogue(game_id, g.day, pick, stats)})
    return out


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
    scheds = npc_scheds or {}
    for p in _personas.TRADER_PERSONAS:
        if p["id"] in walker["npcs"]:
            continue
        # NPC 시작 위치 = 자기 일과의 첫 장소(결정론, game_id·npc_id 시드).
        sched = scheds.get(p["id"], p["sched"])
        first_place = sched[min(sched)]
        rng_n = random.Random(_walker_seed("walker", game_id, p["id"]))
        tile = _gamerun_rand_tile_for(_GAME_LOCATION_ADDR[first_place], rng_n)
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
        steps.extend([list(t) for t in seg[1:]] if len(seg) > 1 else [])
        arrive.append(len(steps))
        cur = dest
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


@app.get("/control/game/day/home")
def control_game_home(game_id: str):
    """GameRun 클론+NPC 8종의 맵 스프라이트 정보 + 초기 좌표(§12.0 부트스트랩)."""
    g = _get_game(game_id)
    if g is None:
        return {"status": "error", "error": "no game"}
    walker = _ensure_game_walker(game_id, g.npc_scheds)
    # T-294 — 오늘 walk가 이미 소비됐으면(워커 pos=하루 끝) 하루 시작 위치를 준다:
    # 하루 중간에 iframe이 리부트돼도 멱등 walk 재생과 좌표가 이어진다(집 순간이동 방지).
    start = walker.get("day_start") if walker.get("day") == g.day else None
    pos = start["pos"] if start else walker["pos"]
    npcs = [
        {"id": p["id"], "name": p["name"], "sprite": p["sprite"],
         "pos": (start["npcs"].get(p["id"]) if start else None) or walker["npcs"][p["id"]]}
        for p in _personas.TRADER_PERSONAS
    ]
    return {"status": "ok",
            "persona": {"original": "gamerun_clone", "underscore": _GAME_CLONE_SPRITE,
                        "initial": g.clone_name},   # T-303 — 맵 이름표에 지은 이름
            "pos": pos, "npcs": npcs, "places": _place_labels(walker)}


@app.get("/control/game/day/walk")
def control_game_walk(game_id: str):
    """그날 일과(8슬롯)를 실좌표 경로로 — 클론이 걷고 카메라가 따라간다(§12.0).

    NPC 8종도 각자 고정 일과(§9.2.1)를 따라 같은 날 함께 걷는다(T-221, 순수 연출).
    하루당 1회만 새 경로를 낸다(day 캐시) — 같은 날 재호출은 빈 steps+cached.
    """
    g = _get_game(game_id)
    if g is None:
        return {"status": "error", "error": "no game"}
    walker = _ensure_game_walker(game_id, g.npc_scheds)
    band_names = [b for b, _ in _WALK_BANDS]
    if walker["day"] == g.day:
        # T-294 — 재요청=빈 경로였던 것을 멱등 재생으로: 같은 날은 첫 응답을 그대로.
        # (iframe 리로드 후에도 하루 걷기를 다시 재생할 수 있다 — 집 순간이동 방지)
        if walker.get("day_resp"):
            return {**walker["day_resp"], "cached": True}
        return {"status": "ok", "steps": [], "npcs": {}, "cached": True,
                "segments": {b: [] for b in band_names},
                "stops": {b: [] for b in band_names},
                "npc_segments": {p["id"]: {b: [] for b in band_names}
                                 for p in _personas.TRADER_PERSONAS},
                "plan": {band: [g.schedule[s] for s in slots if g.schedule.get(s)]
                         for band, slots in _WALK_BANDS},
                "meetings_by_band": _meetings_by_band(g, game_id)}

    # T-237 — 클론·NPC 모두 시간대 4구간으로 분해(연출이 하루 단계와 동기).
    # flat(steps/npcs)은 구간의 순차 연결 — 구버전 map.html 하위호환.
    # T-294 — 하루 시작 위치를 박제(home이 리부트 시 이 좌표를 준다).
    day_start = {"pos": list(walker["pos"]),
                 "npcs": {p["id"]: list(walker["npcs"][p["id"]])
                          for p in _personas.TRADER_PERSONAS}}
    rng = random.Random(_walker_seed("walk", game_id, g.day))
    segments, cur, stops = _banded_route(g.schedule, tuple(walker["pos"]), rng,
                                         home_tile=tuple(walker["home"]))
    walker["pos"] = list(cur)
    steps = [xy for b in band_names for xy in segments[b]]

    npc_steps: dict[str, list[list[int]]] = {}
    npc_segments: dict[str, dict[str, list[list[int]]]] = {}
    for p in _personas.TRADER_PERSONAS:
        rng_n = random.Random(_walker_seed("walk", game_id, p["id"], g.day))
        # T-273 — 연출 경로도 게임의 npc_scheds(프리셋 반영) 단일 소스.
        segs_n, n_cur, _stops_n = _banded_route(
            g.npc_scheds.get(p["id"], p["sched"]),
            tuple(walker["npcs"][p["id"]]), rng_n, home_tile=None)
        npc_segments[p["id"]] = segs_n
        npc_steps[p["id"]] = [xy for b in band_names for xy in segs_n[b]]
        walker["npcs"][p["id"]] = list(n_cur)
    walker["day"] = g.day
    # T-242 — 말풍선용 클론 일정(시간대→장소명). 표현 계층이 "어디로/뭐 하는 중"을 그린다.
    plan = {band: [g.schedule[s] for s in slots if g.schedule.get(s)]
            for band, slots in _WALK_BANDS}
    meetings = _meetings_by_band(g, game_id)
    # T-299 — 만남마다 접근 경로 동봉: NPC 밴드 종료 타일 → 클론 옆 칸(실 길찾기).
    pos_c = list(day_start["pos"])
    pos_n = {p["id"]: list(day_start["npcs"][p["id"]]) for p in _personas.TRADER_PERSONAS}
    for band in band_names:
        if segments[band]:
            pos_c = list(segments[band][-1])
        for nid, segs_b in npc_segments.items():
            if segs_b[band]:
                pos_n[nid] = list(segs_b[band][-1])
        for m in meetings[band]:
            m["approach"] = _meeting_approach(
                tuple(pos_n.get(m["id"], pos_c)), tuple(pos_c))
    resp = {"status": "ok", "steps": steps, "npcs": npc_steps,
            "segments": segments, "npc_segments": npc_segments, "plan": plan,
            "stops": stops,   # T-296 — 장소별 도착 지점(연출: 장소마다 1행동)
            "meetings_by_band": meetings}
    walker["day_start"] = day_start
    walker["day_resp"] = resp
    return resp


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
                        "initial": "내 클론"},
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


# --------------------------------------------------------------------------- #
# Request models
# --------------------------------------------------------------------------- #
class InterviewAnswerBody(BaseModel):
    session_id: str
    qid: str
    text: str
    use_llm: bool = False


class ClonePreviewBody(BaseModel):
    answers: dict


@app.post("/control/clone/preview")
def control_clone_preview(body: ClonePreviewBody):
    """T-231 §5.5 — 인터뷰 확정 화면용 성향 프리뷰(순수, 게임 미생성).

    답변이 만들 클론의 함정별 취약점을 보여주고, 사용자가 '확정'한 뒤에야
    포트폴리오 단계로 넘어간다(한 페이지 한 목적).
    """
    spec = _clone_spec.build_clone_spec(body.answers)
    traits = [
        {"id": trap_id, "name": _traps_get(trap_id).name, "score": round(score, 1)}
        for trap_id, score in spec.trap_scores.items()
    ]
    return {"status": "ok", "trap_scores": spec.trap_scores, "traits": traits}


@app.get("/control/interview/next")
def control_interview_next(session_id: str, use_llm: bool = False):
    """§5.3 대화형 인터뷰 — 다음 질문(구조는 고정, 표현은 opt-in LLM)."""
    answers = _INTERVIEWS.setdefault(session_id, {})
    q = _interview_llm.next_question_llm(answers, use_llm=use_llm)
    return {"status": "ok", "done": q is None, "next": q}


@app.post("/control/interview/answer")
def control_interview_answer(body: InterviewAnswerBody):
    """§5.3 자유 텍스트 답변 → 옵션 스케일로 해석(§5.3.2 출력 스키마 고정) 후 저장."""
    if _question_by_id(body.qid) is None:
        return {"status": "error", "error": "unknown qid"}
    answers = _INTERVIEWS.setdefault(body.session_id, {})
    answers[body.qid] = _interview_llm.interpret_answer(body.qid, body.text, use_llm=body.use_llm)
    q = _interview_llm.next_question_llm(answers, use_llm=body.use_llm)
    if q is not None:
        return {"status": "ok", "done": False, "next": q}
    return {"status": "ok", "done": True, "answers": dict(answers)}


class GameStartBody(BaseModel):
    game_id: str
    answers: dict = {}
    symbol: str = "DOGE"
    start_price: float = 100.0
    start_stats: dict | None = None
    # T-215 D1 — "분산해서 시작" 토글. {category: 0~100 비중, 합계 100} 주면
    # 최대 비중 카테고리가 주력, 나머지는 day0부터 2차 포지션으로 채워진다.
    # 없으면(기본) 기존 단일종목(symbol) 경로 그대로.
    allocations: dict[str, float] | None = None
    # T-273 — 마을 분위기 프리셋(balanced|aggressive|conservative).
    village: str = "balanced"
    # T-303 — 플레이어가 지은 에이전트 이름(미지정=기본 문구).
    clone_name: str | None = None


# T-265 — /day/advance 멱등성 캐시: game_id → (마지막 idem_key, 그 응답).
# /review(2026-07-03): ①체크-후-쓰기 레이스 — FastAPI가 sync 핸들러를 스레드풀로
# 돌려 같은 키 2건이 동시에 캐시 미스로 통과할 수 있다 → 게임별 락으로 직렬화.
# ②무한 성장 — 게임당 응답 1건이 영구 잔류 → 상한 초과 시 FIFO 축출.
_ADVANCE_IDEM: dict[str, tuple[str, dict]] = {}
_ADVANCE_IDEM_MAX = 256
_ADVANCE_LOCKS: dict[str, threading.Lock] = {}
_ADVANCE_LOCKS_GUARD = threading.Lock()


def _advance_lock(game_id: str) -> threading.Lock:
    with _ADVANCE_LOCKS_GUARD:
        lock = _ADVANCE_LOCKS.get(game_id)
        if lock is None:
            if len(_ADVANCE_LOCKS) >= _ADVANCE_IDEM_MAX:
                _ADVANCE_LOCKS.pop(next(iter(_ADVANCE_LOCKS)))
            lock = _ADVANCE_LOCKS[game_id] = threading.Lock()
        return lock


class GameAdvanceBody(BaseModel):
    game_id: str
    news_id: str | None = None
    strategy: str | None = None
    # None(기본) = GameRun.rapport(1:1 대화와 공유하는 §11.4.4 래포 풀)를 자동
    # 사용. 값을 명시하면 그걸로 오버라이드(배치/테스트 전용) — 일반 플레이에서
    # 프론트가 이 필드를 보내면 실제 래포가 무시되는 버그였다(사용자 피드백
    # 2026-07-01 "1:1대화가 제대로 진행이 안돼").
    rapport: float | None = None
    roll: float = 100.0
    agent_pressure: float = 0.0
    # T-265(게이트 4c) — 클라이언트 생성 멱등성 키. 같은 키 재전송이면 하루를 다시
    # 진행하지 않고 저장된 응답을 반환한다(응답 유실 → 재시도 → 이중 적용 차단).
    idem_key: str | None = None


class GameNewRunBody(BaseModel):
    game_id: str
    run_id: str | None = None


@app.post("/control/game/start")
def control_game_start(body: GameStartBody):
    """§12.4 — 인터뷰 답변으로 클론 생성 → 회차 세션 시작(신 엔진 정본).

    T-302(사용자 "30일 너무 길다") — 서비스 길이는 GAME_DAYS(10일). 엔진
    기본값(30)은 run_loop 동치성·기존 테스트를 위해 불변.
    """
    spec = _clone_spec.build_clone_spec(body.answers)
    allocations = {c: p for c, p in (body.allocations or {}).items() if p and p > 0}
    if allocations:
        # 최대 비중 = 주력(§8.3 T-215 D4 전제). 전 카테고리가 day0 지수정규화로
        # 거의 동일가(§6.1.1)라 start_price를 공통 기준가로 그대로 쓴다(기존
        # 단일종목 경로와 동일한 근사 수준 — 별도 fate_line day0 조회 불필요).
        primary_cat = max(allocations, key=allocations.get)
        total = body.start_price
        primary_qty = (allocations[primary_cat] / 100.0) * total / body.start_price
        initial_positions = {
            cat: {"avg_cost": body.start_price, "quantity": (pct / 100.0) * total / body.start_price}
            for cat, pct in allocations.items() if cat != primary_cat
        }
        g = _GameRun(spec, category=primary_cat, start_price=body.start_price,
                     start_stats=body.start_stats, start_quantity=primary_qty,
                     initial_positions=initial_positions, run_id="run1",
                     village=body.village, days=GAME_DAYS,
                     clone_name=body.clone_name or "내 클론")
    else:
        g = _GameRun(spec, category=_category_for_symbol(body.symbol),
                     start_price=body.start_price, start_stats=body.start_stats,
                     run_id="run1", village=body.village, days=GAME_DAYS,
                     clone_name=body.clone_name or "내 클론")
    _GAMES[body.game_id] = g
    _persist_game(body.game_id, g)
    return {"status": "ok", "state": g.state()}


@app.get("/control/game/state")
def control_game_state(game_id: str):
    g = _get_game(game_id)
    if g is None:
        return {"status": "error", "error": "no game"}
    return {"status": "ok", "state": g.state()}


def _news_seed(game_id: str, day: int) -> int:
    """(game_id, day) 고정 시드 — hash()는 프로세스마다 달라 재시작 안정성이 없음."""
    return zlib.crc32(f"news:{game_id}:{day}".encode())


def _drawn_news_today(game_id: str, g: "_GameRun") -> list[dict]:
    """그날 뽑힌 3지선다(서버가 정본) — /news 응답과 게시판 트리거가 공유."""
    return _news.draw_three(_news.load_news_pool(),
                            random.Random(_news_seed(game_id, g.day)))


@app.get("/control/game/news")
def control_game_news(game_id: str, seed: int | None = None):
    """§7 그날 아침 뉴스 3지선다.

    seed 미지정이면 (game_id, day)로 파생 — 같은 날엔 같은 3개, 날이 바뀌면 새 3개.
    (T-223에서 수정: 프론트가 seed=0 고정으로 불러 43개 풀에서 매일 같은 3개만
    나오던 결함. 명시 seed는 배치/테스트용으로 유지.)
    """
    g = _get_game(game_id)
    if seed is None and g is not None:
        picked = _drawn_news_today(game_id, g)
    else:
        picked = _news.draw_three(_news.load_news_pool(), random.Random(seed or 0))
    return {"status": "ok", "news": [
        {"id": n["id"], "tone": n["tone"], "headline": n["headline"],
         "triggers": n.get("triggers", [])} for n in picked]}


class GameAvoidBody(BaseModel):
    game_id: str
    slot_a: int
    slot_b: int


@app.get("/control/game/day/preview")
def control_game_preview(game_id: str):
    """§9.2.1 전날밤 — 내일 일과 + 마주칠 NPC(뉴스·위기는 비공개)."""
    g = _get_game(game_id)
    if g is None:
        return {"status": "error", "error": "no game"}
    return {"status": "ok", **g.preview_day()}


@app.post("/control/game/day/avoid")
def control_game_avoid(body: GameAvoidBody):
    """§9.2.1 회피 — 일과 항목 하나의 순서만 바꿔 마주칠 NPC를 피한다."""
    g = _get_game(body.game_id)
    if g is None:
        return {"status": "error", "error": "no game"}
    meetings = g.avoid(body.slot_a, body.slot_b)
    _persist_game(body.game_id, g)
    return {"status": "ok", "schedule": dict(g.schedule), "meetings": meetings}


def _siren_today(game_id: str, day: int) -> bool:
    """T-271 — 사이렌 발생 판정. game_id 시드 결정론(회차 무관 — §13.6 거울:
    run이 달라도 같은 날 떠야 회차 비교가 같은 시험지가 된다)."""
    return zlib.crc32(f"siren:{game_id}:{day}".encode()) % 100 < _T.SIREN_PROB_PCT


@app.get("/control/game/day/siren")
def control_game_siren(game_id: str):
    """T-271 — 오늘 사이렌이 뜨는 날인지 + 이미 소비했는지. 순수 조회(무변이)."""
    g = _get_game(game_id)
    if g is None:
        return {"status": "error", "error": "no game"}
    return {"status": "ok", "day": g.day,
            "active": _siren_today(game_id, g.day) and not g.finished,
            "used": g.day in g._siren_log}


class GameSirenBody(BaseModel):
    game_id: str
    day: int
    choice: str   # bad | good | skip


@app.post("/control/game/day/siren")
def control_game_siren_choose(body: GameSirenBody):
    """T-271 — 사이렌 선택 적용. 그날의 사이렌 1개(자연 멱등, 4c ①),
    _advance_lock으로 동시 POST·advance와 직렬화(4c ②)."""
    g = _get_game(body.game_id)
    if g is None:
        return {"status": "error", "error": "no game"}
    with _advance_lock(body.game_id):
        if not _siren_today(body.game_id, body.day):
            return {"status": "error", "error": "no siren today"}
        try:
            eff = g.siren_choice(body.day, body.choice)
        except ValueError as e:
            return {"status": "error", "error": str(e)}
    _persist_game(body.game_id, g)
    return {"status": "ok", **eff, "state": g.state()}


@app.get("/control/game/history")
def control_game_history(game_id: str):
    """T-269 — 진행 이력(발자취): 일별 뉴스 선택·만남·소셜 액션·일과. 순수 조회.

    T-300 — 일별 npc_trades(그날 매매한 다른 에이전트, 결정론 파생)도 동봉.
    """
    g = _get_game(game_id)
    if g is None:
        return {"status": "error", "error": "no game"}
    days = g.history()
    for d in days:
        d["npc_trades"] = [
            {"id": p["id"], "name": p["name"], "action": action}
            for p in _personas.TRADER_PERSONAS
            if (action := _npc_traders.npc_action_on_day(p, g.fl, g.category, d["day"]))]
    return {"status": "ok", "run_id": g.run_id, "days": days}


@app.get("/control/game/chat_log")
def control_game_chat_log(game_id: str, npc_id: str):
    """T-288 — 메신저 대화방: 이 NPC와의 일자별 대화 로그. 순수 조회.

    만남 대사는 결정론 재생성(meeting_talk, 그날 밤 스탯 스냅샷 기준 —
    표시 당시와 동일 시드), 권유는 방향·성패 요약(당시 문장은 래포/기억
    의존이라 박제하지 않았음 — 요약으로 충분, §9.2.2).
    """
    g = _get_game(game_id)
    if g is None:
        return {"status": "error", "error": "no game"}
    snaps = g.store.snapshots(g.run_id)
    # 오늘(아직 스냅샷 없음)의 권유도 보여야 한다 — 소셜 로그 날짜와 합집합.
    social_days = {e.get("day") for e in g._social_log
                   if e.get("kind") == "persuade" and e.get("npc_id") == npc_id}
    days = []
    for day in sorted(set(snaps) | social_days):
        s = snaps.get(day)
        entries = []
        if s is not None and npc_id in (s.met or []):
            entries.append({
                "kind": "meeting",
                "lines": _meeting_talk.dialogue(
                    game_id, day, npc_id, dict(s.emotion_stats or {}))})
        for e in g._social_log:
            if (e.get("day") == day and e.get("kind") == "persuade"
                    and e.get("npc_id") == npc_id):
                entries.append({"kind": "persuade",
                                "direction": e.get("direction"),
                                "accepted": bool(e.get("accepted"))})
        if entries:
            days.append({"day": day, "entries": entries})
    return {"status": "ok", "npc_id": npc_id, "days": days}


class GameRelocateBody(BaseModel):
    game_id: str
    slot: int
    place: str


@app.post("/control/game/day/relocate")
def control_game_relocate(body: GameRelocateBody):
    """T-272b — 전날밤: 이 슬롯의 행선지를 지정(스왑 등가 — 회피와 동일 파워).

    같은 (slot, place) 재전송은 no-op(자연 멱등 — 게이트 4c ①). 스왑 대상
    슬롯 탐색은 서버가 수행(클라이언트 stale schedule 무해 — 4c ②).
    """
    g = _get_game(body.game_id)
    if g is None:
        return {"status": "error", "error": "no game"}
    try:
        preview = g.relocate(body.slot, body.place)
    except ValueError as e:
        return {"status": "error", "error": str(e)}
    _persist_game(body.game_id, g)
    return {"status": "ok", **preview}


class GameDesignateBody(BaseModel):
    game_id: str
    slot: int
    npc_id: str | None = None   # None = 지정 해제(클론에게 맡김)


@app.post("/control/game/day/designate")
def control_game_designate(body: GameDesignateBody):
    """T-272a — 전날밤: 이 슬롯의 대화 상대를 플레이어가 지정(§9.2.1b 덮어쓰기).

    같은 (slot, npc) 재전송은 같은 결과(자연 멱등 — 게이트 4c ①). 후보 밖
    NPC는 거부. 지정은 그날 하루만 유효.
    """
    g = _get_game(body.game_id)
    if g is None:
        return {"status": "error", "error": "no game"}
    try:
        preview = g.designate(body.slot, body.npc_id)
    except ValueError as e:
        return {"status": "error", "error": str(e)}
    _persist_game(body.game_id, g)
    return {"status": "ok", **preview}


class GamePersuadeBody(BaseModel):
    game_id: str
    npc_id: str
    direction: str  # "calm" | "escalate"
    roll: float = 100.0
    escalation: float = 0.0


class GameFgiBody(BaseModel):
    game_id: str
    tone: str
    roll: float = 100.0


@app.post("/control/game/social/persuade")
def control_game_persuade(body: GamePersuadeBody):
    """§9.2.2 1:1 권유 — 위기개입과 같은 래포 풀(§11.4.4)."""
    g = _get_game(body.game_id)
    if g is None:
        return {"status": "error", "error": "no game"}
    out = g.persuade(body.npc_id, body.direction, roll=body.roll, escalation=body.escalation)
    _persist_game(body.game_id, g)
    return {"status": "ok", **out}


@app.post("/control/game/social/fgi")
def control_game_fgi(body: GameFgiBody):
    """§9.2.3 FGI 단톡방 — 익명 톤 얹기(래포 무관, 약하고 불확실)."""
    g = _get_game(body.game_id)
    if g is None:
        return {"status": "error", "error": "no game"}
    out = g.fgi_post(body.tone, roll=body.roll)
    _persist_game(body.game_id, g)
    return {"status": "ok", **out}


@app.get("/control/game/day/board")
def control_game_board(game_id: str, use_llm: bool = False):
    """T-223/T-253 게시판 — 이벤트 날만 열림, 같은 날 재호출 = 같은 피드.

    LLM 대화 생성은 서버 env `MV_BOARD_LLM=1`(운영자 스위치)이나 use_llm 쿼리로
    켠다 — 키 없음·실패·검증 탈락이면 오프라인 결정론 대화로 폴백(과금 게이트).
    """
    g = _get_game(game_id)
    if g is None:
        return {"status": "error", "error": "no game"}
    llm_on = use_llm or os.environ.get("MV_BOARD_LLM") == "1"
    board = g.board_today(_drawn_news_today(game_id, g), use_llm=llm_on)
    _persist_game(game_id, g)
    # T-303 — 게시글/댓글의 클론 표기를 지은 이름으로(표현만, 아카이브 불변).
    def _rename(posts):
        for p in posts or []:
            if p.get("author_id") == "clone":
                p["author"] = g.clone_name
            for c in p.get("comments", []):
                if c.get("author_id") == "clone":
                    c["author"] = g.clone_name
    _rename(board.get("posts"))
    if board.get("recent"):
        _rename(board["recent"].get("posts"))
    return {"status": "ok", **board}


@app.get("/control/game/day/approach")
def control_game_approach(game_id: str, fx: int, fy: int, cx: int, cy: int):
    """T-304 — 만남 시점 실좌표 접근 경로(순수 함수, 무변이·멱등 GET).

    맵이 만남 직전 NPC의 실제 타일에서 클론 옆 칸까지의 실 길찾기 경로를 받아
    벽 뚫기 없이 걸어오게 한다(정적 approach는 밴드 종료 시점 기준이라 어긋남).
    """
    _ = game_id   # 시그니처 일관성용(경로는 게임 무관 순수 함수)
    return {"status": "ok", "steps": _meeting_approach((fx, fy), (cx, cy))}


@app.get("/control/game/day/crisis_check")
def control_game_crisis_check(game_id: str, news_id: str | None = None):
    """오늘 위기가 실제 발생하는지 부작용 없이 미리 조회(사용자 피드백 — 위기
    개입은 상시 노출이 아니라 실제 위기가 터진 순간에만 이벤트로 뜬다)."""
    g = _get_game(game_id)
    if g is None:
        return {"status": "error", "error": "no game"}
    news_item = None
    if news_id:
        pool = _news.load_news_pool()
        news_item = next((n for n in pool.news if n["id"] == news_id), None)
    preview = g.preview_crisis(news=news_item)
    return {"status": "ok", **preview}


@app.post("/control/game/day/advance")
def control_game_advance(body: GameAdvanceBody):
    """하루 1칸 진행 — 뉴스 선택·개입(A/B/C) 반영 후 정산. Day30이면 카드.

    T-265 — 같은 idem_key 재전송이면 저장된 응답 반환(재적용 없음). 게임별 락으로
    동시 재시도를 직렬화(체크-후-쓰기 레이스 차단, 게이트 4c-②).
    """
    with _advance_lock(body.game_id):
        return _do_advance(body)


def _do_advance(body: GameAdvanceBody):
    g = _get_game(body.game_id)
    if g is None:
        return {"status": "error", "error": "no game"}
    if body.idem_key is not None:
        cached = _ADVANCE_IDEM.get(body.game_id)
        if cached is not None and cached[0] == body.idem_key:
            return cached[1]
    news_item = None
    if body.news_id:
        pool = _news.load_news_pool()
        news_item = next((n for n in pool.news if n["id"] == body.news_id), None)
    # rapport 명시 시에만 오버라이드(intervention 직접 구성) — 그 외엔 strategy만
    # 넘겨 GameRun이 자신의 공유 래포 풀(self.rapport)을 쓰게 한다.
    intervention = (_Intervention(body.strategy, body.rapport)
                    if (body.strategy and body.rapport is not None) else None)
    strategy_arg = body.strategy if intervention is None else None
    snap = g.advance_day(news=news_item, intervention=intervention, strategy=strategy_arg,
                         roll=body.roll, agent_pressure=body.agent_pressure)
    out = {"status": "ok", "state": g.state()}
    if snap is not None:
        out["day_result"] = {"trap": snap.trap, "swayed": snap.swayed,
                             "fund_flow": snap.fund_flow, "realized_pnl": snap.realized_pnl,
                             "stats": snap.emotion_stats, "bundle": snap.bundle}
        # T-301(사용자 "하루 끝나면 모달로") — 매매 서사를 정산 응답에 동봉:
        # history()와 동일 산식(단일 소스), npc_trades는 그날 결정론 파생.
        hist = g.history()
        if hist:
            out["day_result"]["trade"] = hist[-1]["trade"]
        out["day_result"]["npc_trades"] = [
            {"id": p["id"], "name": p["name"], "action": action}
            for p in _personas.TRADER_PERSONAS
            if (action := _npc_traders.npc_action_on_day(p, g.fl, g.category, snap.day))]
    if g.finished and g.summary is not None:
        # 게이트 4c-③(부분쓰기): advance_day(변이) 뒤에 예외가 나면 캐시 미기록
        # 상태로 500 → 클라이언트 재시도가 하루를 이중 적용한다. 카드 실패는
        # 응답에서 빼되 캐시·정산은 반드시 완료(카드는 /card로 재조회 가능).
        try:
            out["card"] = _result_card.result_card(g.summary)
        except Exception:  # noqa: BLE001
            pass
    if body.idem_key is not None:
        if len(_ADVANCE_IDEM) >= _ADVANCE_IDEM_MAX:
            _ADVANCE_IDEM.pop(next(iter(_ADVANCE_IDEM)))
        _ADVANCE_IDEM[body.game_id] = (body.idem_key, out)
    _persist_game(body.game_id, g)
    return out


@app.get("/control/game/day/scene")
def control_game_scene(game_id: str, use_llm: bool = False):
    """§12.0 표현 — 마지막 하루 결정을 연출명령+대사로(맵이 연기). LLM은 opt-in."""
    g = _get_game(game_id)
    if g is None or g.last_snap is None:
        return {"status": "error", "error": "no scene"}
    return {"status": "ok",
            "scene": _presentation.narrate(g.last_snap, g.clone_spec, use_llm=use_llm)}


@app.get("/control/game/card")
def control_game_card(game_id: str):
    """§14 회차 결과카드(완주 시)."""
    g = _get_game(game_id)
    if g is None or g.summary is None:
        return {"status": "error", "error": "not finished"}
    return {"status": "ok", "card": _result_card.result_card(g.summary)}


@app.post("/control/game/newrun")
def control_game_newrun(body: GameNewRunBody):
    """§13 다음 회차 — 같은 운명선 다시(클론 리셋, 요약 누적)."""
    g = _get_game(body.game_id)
    if g is None:
        return {"status": "error", "error": "no game"}
    g.new_run(run_id=body.run_id)
    _persist_game(body.game_id, g)
    return {"status": "ok", "state": g.state()}


@app.get("/control/game/leaderboard")
def control_game_leaderboard(game_id: str):
    """T-245 §13.7 — 마을 수익률 순위(클론+NPC 8, 배경 정보 톤 — 경쟁 목표화 금지 M4)."""
    g = _get_game(game_id)
    if g is None:
        return {"status": "error", "error": "no game"}
    total = (g.last_snap.total_asset if g.last_snap is not None
             else g.holding["cash"] + g.holding["quantity"] * g.last_price)
    clone_pct = round((total - g.initial_total) / g.initial_total * 100.0, 2) \
        if g.initial_total else 0.0
    board = [{"id": "clone", "name": g.clone_name, "return_pct": clone_pct}]
    for p in _personas.TRADER_PERSONAS:
        board.append({"id": p["id"], "name": p["name"],
                      "return_pct": _npc_traders.npc_return_pct(p, g.fl, g.category, g.day)})
    board.sort(key=lambda e: e["return_pct"], reverse=True)
    clone_rank = next(i + 1 for i, e in enumerate(board) if e["id"] == "clone")
    return {"status": "ok", "board": board, "clone_rank": clone_rank, "total": len(board)}


@app.get("/control/game/day/trades")
def control_game_trades(game_id: str, day: int | None = None):
    """T-256 — 그날 매매 순간 가시화용. 순수 파생(무변이).

    기본 day = 마지막으로 정산된 날(g.day-1). 클론은 그날 스냅샷의 fund_flow,
    NPC는 npc_action_on_day(수익률 규칙과 단일 소스).
    """
    g = _get_game(game_id)
    if g is None:
        return {"status": "error", "error": "no game"}
    d = day if day is not None else max(0, g.day - 1)
    trades = []
    # 리뷰 수정 — fund_flow 전체 매핑: hold_winner(익절 거부)는 거래가 없으므로
    # 연출 생략(안 한 거래를 "매수!"로 보여주던 왜곡), 번들이면 첫 실거래 사용.
    _FLOW_ACTION = {"to_cash": "sell", "to_stable": "sell",
                    "to_hotter": "buy", "concentrate": "buy"}
    if g.last_snap is not None and g.day - 1 == d:
        flows = ([b.get("fund_flow") for b in (g.last_snap.bundle or [])]
                 or [g.last_snap.fund_flow])
        action = next((_FLOW_ACTION[f] for f in flows if f in _FLOW_ACTION), None)
        if action:
            trades.append({"id": "gamerun_clone", "name": g.clone_name, "action": action})
    for p in _personas.TRADER_PERSONAS:
        action = _npc_traders.npc_action_on_day(p, g.fl, g.category, d)
        if action:
            trades.append({"id": p["id"], "name": p["name"], "action": action})
    return {"status": "ok", "day": d, "trades": trades}


@app.get("/control/game/compare_days")
def control_game_compare_days(game_id: str, run_a: str, run_b: str):
    """T-227 §13.6 — 두 회차의 행동이 갈린 날 목록(비교 화면의 탭 소스)."""
    g = _get_game(game_id)
    if g is None:
        return {"status": "error", "error": "no game"}
    if not _runs.runs_comparable(g.store, run_a, run_b):
        return {"status": "error", "error": "unknown or empty run"}
    return {"status": "ok", "days": _runs.diverging_days(g.store, run_a, run_b)}


@app.get("/control/game/compare")
def control_game_compare(game_id: str, run_a: str, run_b: str, day: int):
    """§13.6 회차 비교 — 한 게임의 두 회차를 같은 Day로 겹쳐 본다(거울)."""
    g = _get_game(game_id)
    if g is None:
        return {"status": "error", "error": "no game"}
    cmp = _runs.compare_runs(g.store, run_a, run_b, day)
    return {"status": "ok", **cmp}


@app.get("/control/game/summaries")
def control_game_summaries(game_id: str):
    """결과 카드 모음(§14) — 이 게임에서 완주한 전 회차 요약 목록."""
    g = _get_game(game_id)
    if g is None:
        return {"status": "error", "error": "no game"}
    return {"status": "ok", "summaries": [dataclasses.asdict(s) for s in g.store.summaries()]}
