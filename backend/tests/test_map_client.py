"""C-015 맵 뷰어: 서버가 HTML을 서빙 + 참조 엔드포인트 전부 존재."""

from __future__ import annotations

import re

import market_live_server as mls


def test_map_route_serves_html_and_uses_existing_endpoints():
    resp = mls.map_client()
    body = resp.body.decode("utf-8")
    assert resp.status_code == 200
    assert "Phaser" in body and "Market Village" in body
    referenced = set(re.findall(r'"(/(?:control|api)/[a-z/_]+)"', body))
    registered = {r.path for r in mls.app.routes if hasattr(r, "path")}
    missing = {p for p in referenced if p not in registered}
    assert not missing, f"맵 뷰어가 없는 엔드포인트를 호출함: {missing}"
