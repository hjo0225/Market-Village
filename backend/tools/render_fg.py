# -*- coding: utf-8 -*-
"""the_ville 전경 오버레이(the_ville_fg.png) 렌더러 — T-277.

/map(Phaser)은 배경 1장(the_ville_full.png, depth<10) 위에 스프라이트(depth 10),
그 위에 전경 1장(the_ville_fg.png, depth 15)을 얹는 3층 구조다. 전경 PNG에 들어간
타일은 캐릭터를 항상 가리므로, "머리 위" 타일(키 큰 가구 상단·캐릭터가 뒤에 설 수
있는 것)만 전경에 넣어야 한다.

T-263은 "Interior Furniture L2 " 레이어 전체를 전경에 넣어 카펫·침대·의자 같은
바닥 데코까지 캐릭터를 덮었다(몸 뚫림 리포트). T-277: 아래 규칙으로 선별한다.

선별 규칙(조건부 레이어의 타일 (x,y)):
  keep = blocked(x,y) or blocked(x,y+1)
  - blocked = 게임 실충돌(collision_maze ∪ SOLID_OBJECTS 가구, market_live_server와
    동일 정의). 캐릭터가 설 수 없는 칸의 타일은 전경에 둬도 무해하고(원래 모습 유지),
    바로 아래 칸이 막힌 타일은 "키 큰 가구의 상단"(캐릭터가 그 뒤에 서는 칸)이다.
  - 둘 다 아니면(자기 칸도 아래 칸도 걸을 수 있음) 바닥 데코(카펫·러그·의자·침대
    발치 등) → 전경 제외(배경 the_ville_full.png에는 이미 베이크돼 있어 그대로 보임).

실행:  python backend/tools/render_fg.py
출력:  environment/.../visuals/the_ville_fg.png (기존 파일은 백업 후 덮어씀)
"""
import json
import os
import sys
from collections import Counter

from PIL import Image

# --------------------------------------------------------------------------- #
# 설정 (튜닝은 여기만)
# --------------------------------------------------------------------------- #
_HERE = os.path.dirname(os.path.abspath(__file__))          # backend/tools/
_BACKEND = os.path.normpath(os.path.join(_HERE, ".."))      # backend/
_REPO = os.path.normpath(os.path.join(_BACKEND, ".."))      # repo root
VISUALS = os.path.join(_REPO, "environment", "frontend_server",
                       "static_dirs", "assets", "the_ville", "visuals")

MAP_JSON = os.path.join(VISUALS, "the_ville_jan7.json")     # T-263과 동일한 지도

# 전량 전경에 넣는 레이어(원본 the_ville도 캐릭터 위에 그리던 층).
FULL_LAYERS = ["Foreground L1", "Foreground L2"]
# 선별 규칙으로 걸러 넣는 레이어. (주의: 원본 지도에서 이름 끝에 공백이 있다.)
CONDITIONAL_LAYERS = ["Interior Furniture L2 "]
# GID 강제 제외/포함(선별 규칙이 틀린 개별 타일이 나오면 여기 추가; 플립 플래그 제거
# 후의 원시 GID 기준, 그 GID의 모든 배치에 적용).
FORCE_EXCLUDE_GIDS: set[int] = set()
FORCE_KEEP_GIDS: set[int] = set()

# 타일셋 원본 탐색 경로(순서대로 시도). v1/interiors 등은 이 레포 map_assets에 없고
# 사용자의 generative_agents 원본 레포에 있다(T-263과 동일 소스, 무수정 읽기 전용).
TILESET_ROOTS = [
    VISUALS,
    r"C:\Users\ABC\Desktop\Project\generative_agents\environment\frontend_server\static_dirs\assets\the_ville\visuals",
]

OUT_PATH = os.path.join(VISUALS, "the_ville_fg.png")
BACKUP_PATH = os.path.join(VISUALS, "the_ville_fg.backup_before_T277.png")

TILE = 32
# Tiled GID 상위 3비트 = 플립 플래그
FLIP_H, FLIP_V, FLIP_D = 0x80000000, 0x40000000, 0x20000000
FLIP_MASK = 0x1FFFFFFF

# --------------------------------------------------------------------------- #
# 게임 실충돌(경로탐색과 동일): collision_maze ∪ SOLID_OBJECTS 가구.
# --------------------------------------------------------------------------- #
sys.path.insert(0, _BACKEND)


def build_blocked_grid():
    """market_live_server._blocked_maze()와 같은 정의의 bool 그리드."""
    from maze import Maze                      # backend/maze.py (the_ville 유틸)
    from utils import collision_block_id       # backend/utils.py
    # market_live_server.SOLID_OBJECTS와 동일(C-018). import 순환을 피하려 복사하지
    # 않고 서버 모듈에서 그대로 읽는다(서버 앱 생성 부작용 없음 — 모듈 import만).
    from market_live_server import SOLID_OBJECTS
    m = Maze("the_ville")
    cid = str(collision_block_id)
    grid = [[False] * m.maze_width for _ in range(m.maze_height)]
    for y in range(m.maze_height):
        for x in range(m.maze_width):
            if str(m.collision_maze[y][x]) == cid or \
                    m.tiles[y][x]["game_object"] in SOLID_OBJECTS:
                grid[y][x] = True
    return grid


# --------------------------------------------------------------------------- #
# 타일셋 로딩/블리팅
# --------------------------------------------------------------------------- #
def _find_tileset(rel_path):
    for root in TILESET_ROOTS:
        p = os.path.join(root, rel_path.replace("/", os.sep))
        if os.path.isfile(p):
            return p
    raise FileNotFoundError(
        f"타일셋을 찾을 수 없음: {rel_path} (탐색: {TILESET_ROOTS})")


_sheet_cache: dict[str, Image.Image] = {}


def _load_sheet(rel_path):
    if rel_path not in _sheet_cache:
        img = Image.open(_find_tileset(rel_path)).convert("RGBA")
        # tmx의 trans="ff00ff": 마젠타 키 컬러 → 투명 처리
        px = img.load()
        w, h = img.size
        for yy in range(h):
            for xx in range(w):
                r, g, b, a = px[xx, yy]
                if (r, g, b) == (255, 0, 255):
                    px[xx, yy] = (0, 0, 0, 0)
        _sheet_cache[rel_path] = img
    return _sheet_cache[rel_path]


def make_tile_fetcher(tilesets):
    ordered = sorted(tilesets, key=lambda t: t["firstgid"])

    def fetch(gid):
        """플립 플래그 포함 GID → 32x32 RGBA 타일."""
        raw = gid & FLIP_MASK
        ts = None
        for t in ordered:
            if raw >= t["firstgid"]:
                ts = t
            else:
                break
        idx = raw - ts["firstgid"]
        sheet = _load_sheet(ts["image"])
        cols = ts["columns"]
        sx, sy = (idx % cols) * TILE, (idx // cols) * TILE
        tile = sheet.crop((sx, sy, sx + TILE, sy + TILE))
        # Tiled 플립 순서: 대각(축 교환) → 수평 → 수직
        if gid & FLIP_D:
            tile = tile.transpose(Image.TRANSPOSE)
        if gid & FLIP_H:
            tile = tile.transpose(Image.FLIP_LEFT_RIGHT)
        if gid & FLIP_V:
            tile = tile.transpose(Image.FLIP_TOP_BOTTOM)
        return tile

    return fetch


# --------------------------------------------------------------------------- #
# 메인
# --------------------------------------------------------------------------- #
def main():
    d = json.load(open(MAP_JSON, encoding="utf-8"))
    W, H = d["width"], d["height"]
    layers = {L["name"]: L for L in d["layers"]}
    fetch = make_tile_fetcher(d["tilesets"])
    blocked = build_blocked_grid()

    def is_blocked(x, y):
        return 0 <= y < H and blocked[y][x]

    canvas = Image.new("RGBA", (W * TILE, H * TILE), (0, 0, 0, 0))
    stats = Counter()

    def blit(x, y, gid):
        canvas.alpha_composite(fetch(gid), (x * TILE, y * TILE))

    for name in FULL_LAYERS:
        for i, gid in enumerate(layers[name]["data"]):
            if not gid:
                continue
            blit(i % W, i // W, gid)
            stats[f"{name}: 포함"] += 1

    excluded_by_gid = Counter()
    for name in CONDITIONAL_LAYERS:
        for i, gid in enumerate(layers[name]["data"]):
            if not gid:
                continue
            x, y = i % W, i // W
            raw = gid & FLIP_MASK
            if raw in FORCE_KEEP_GIDS:
                keep = True
            elif raw in FORCE_EXCLUDE_GIDS:
                keep = False
            else:
                # 자기 칸이 막혔거나(캐릭터가 못 서는 칸 — 무해) 바로 아래 칸이
                # 막혔으면(키 큰 가구 상단 — 캐릭터가 뒤에 섬) 전경 유지.
                keep = is_blocked(x, y) or is_blocked(x, y + 1)
            if keep:
                blit(x, y, gid)
                stats[f"{name}: 포함"] += 1
            else:
                stats[f"{name}: 제외(바닥 데코)"] += 1
                excluded_by_gid[raw] += 1

    # 기존 파일 백업(최초 1회만 — 재실행이 백업을 덮어쓰지 않게)
    if os.path.exists(OUT_PATH) and not os.path.exists(BACKUP_PATH):
        os.replace(OUT_PATH, BACKUP_PATH)
        print("백업:", BACKUP_PATH)
    canvas.save(OUT_PATH)
    print("저장:", OUT_PATH, f"({W * TILE}x{H * TILE})")
    for k in sorted(stats):
        print(f"  {k}: {stats[k]}")
    if excluded_by_gid:
        print("  제외 GID:", dict(sorted(excluded_by_gid.items())))


if __name__ == "__main__":
    main()
