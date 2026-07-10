"""§B — 코인 실감: 카테고리 → 실명 종목 {symbol, name_kr, color} (신규 모듈).

market_seed.json의 `_meta_origin`(예: "upbit:KRW-DOGE:2021-04-20 00:00:00")이
블라인드 리빌(fate_line.reveal, T-49c)의 유일한 소스다. 이 모듈은 그 심볼만
뽑아 **날짜는 절대 포함하지 않고**(엔딩 전까지 시기 블라인드 유지, 스펙 §B
"설계 전환") 카탈로그/티커에 쓸 표시용 매핑을 만든다.

I5(LLM 금지)·I2(결정론): 전부 정적 데이터 파생, 랜덤 없음.
"""

from __future__ import annotations

from .fate_line import CATEGORIES, load_fate_line

# 심볼 → 한글 이름(fate_line.reveal의 _coin 표와 동일 소스 값 — 여기서 재정의해
# reveal()의 날짜 포함 출력과 분리, 플레이 중(catalog/ticker)엔 날짜가 절대
# 섞이지 않게 한다).
_SYMBOL_NAME_KR: dict[str, str] = {
    "BTC": "비트코인", "XRP": "리플", "DOGE": "도지코인",
    "USDT": "테더", "ETH": "이더리움",
}

# 심볼 → 표시 색(티커/배분 화면 UI 톤). 코인 성격에 맞춘 고정 팔레트(결정론).
_SYMBOL_COLOR: dict[str, str] = {
    "BTC": "#f7931a",
    "XRP": "#23292f",
    "DOGE": "#c2a633",
    "USDT": "#26a17b",
    "ETH": "#627eea",
}
_DEFAULT_COLOR = "#888888"


def _symbol_of(origin: str) -> str:
    """`_meta_origin`("upbit:KRW-DOGE:2021-04-20 00:00:00")에서 심볼만 추출.
    날짜 파트는 절대 반환하지 않는다."""
    parts = str(origin or "").split(":")
    return parts[1].replace("KRW-", "") if len(parts) > 1 else ""


def category_coin_map() -> dict[str, dict]:
    """카테고리 → {category, symbol, name, color}. 날짜 없음(시기 블라인드 유지).

    market_seed.json의 실제 블라인드 자산 매핑(fate_line._meta_origin)에서
    카테고리별 심볼을 뽑는다 — 리빌(reveal)과 같은 소스지만 날짜를 뺀 부분집합."""
    fate = load_fate_line()
    out: dict[str, dict] = {}
    for cat in CATEGORIES:
        info = fate._data.get("categories", {}).get(cat, {})  # noqa: SLF001 — 같은 패키지 내부 접근
        symbol = _symbol_of(info.get("_meta_origin", ""))
        out[cat] = {
            "category": cat,
            "symbol": symbol,
            "name": _SYMBOL_NAME_KR.get(symbol, symbol),
            "color": _SYMBOL_COLOR.get(symbol, _DEFAULT_COLOR),
        }
    return out


def catalog() -> list[dict]:
    """GET /emo/catalog 페이로드 — 카테고리별 실명 코인 리스트. 날짜 없음."""
    return [category_coin_map()[cat] for cat in CATEGORIES]


def coin_for_category(cat: str) -> dict:
    """단일 카테고리의 코인 표시 정보. 미지의 카테고리는 빈 심볼로 폴백."""
    m = category_coin_map()
    return m.get(cat, {"category": cat, "symbol": "", "name": cat, "color": _DEFAULT_COLOR})
