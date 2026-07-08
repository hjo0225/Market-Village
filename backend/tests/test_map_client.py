"""C-015 맵 뷰어: 서버가 HTML을 서빙 + 참조 엔드포인트 전부 존재."""

from __future__ import annotations

import re

import market_live_server as mls


def test_map_route_serves_html_and_uses_existing_endpoints():
    resp = mls.map_client()
    body = resp.body.decode("utf-8")
    assert resp.status_code == 200
    assert "Phaser" in body and "Market Village" in body
    # T-15 컷오버 — 맵 브릿지는 emo 경로만 쓴다. 구 /control 참조가 남아있으면 실패.
    assert "/control/" not in body, "맵 뷰어에 삭제된 classic(/control) 참조가 남아있음"
    # 맵이 소비하는 emo 엔드포인트(문자열 연결 베이스 /emo/…/map/{ep})가 서버에 등록돼 있는지.
    registered = {r.path for r in mls.app.routes if hasattr(r, "path")}
    emo_map_bases = {"/emo/{game_id}/map/home", "/emo/{game_id}/map/walk",
                     "/emo/{game_id}/map/approach"}
    assert emo_map_bases <= registered, f"emo 맵 엔드포인트 미등록: {emo_map_bases - registered}"
