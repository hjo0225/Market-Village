"""사용자 지시(2026-07-01) — 실 업비트 데이터로 운명선 교체.

build_online()은 실제 네트워크 호출을 한다 — 테스트는 `_fetch_candles`를
monkeypatch해 오프라인·결정론으로 변환 로직(지수정규화·스키마)만 검증한다.
"""

from __future__ import annotations

from tools import seed_market_village as SMV

# Upbit 응답 형식(내림차순 — 최신이 앞) 축소 샘플. day0(가장 과거) open=1000 기준.
_FAKE_CANDLES_DESC = [
    {"opening_price": 1300.0, "high_price": 1350.0, "low_price": 1280.0, "trade_price": 1320.0},
    {"opening_price": 1100.0, "high_price": 1150.0, "low_price": 1080.0, "trade_price": 1300.0},
    {"opening_price": 1000.0, "high_price": 1120.0, "low_price": 990.0, "trade_price": 1100.0},
]


def test_fetch_candles_reverses_to_chronological_order(monkeypatch):
    calls = []

    def fake_urlopen(url, timeout):
        calls.append(url)
        class R:
            def __enter__(self_): return self_
            def __exit__(self_, *a): return False
            def read(self_):
                import json
                return json.dumps(_FAKE_CANDLES_DESC).encode("utf-8")
        return R()

    monkeypatch.setattr(SMV.urllib.request, "urlopen", fake_urlopen)
    rows = SMV._fetch_candles("KRW-BTC", 3, "2024-07-01 00:00:00")
    assert rows[0]["opening_price"] == 1000.0   # 가장 과거가 맨 앞(오름차순)
    assert rows[-1]["opening_price"] == 1300.0  # 가장 최근이 맨 뒤
    assert "KRW-BTC" in calls[0] and "2024-07-01" in calls[0]


def test_normalize_ohlc_indexes_day0_close_to_100():
    candles = [
        {"opening_price": 1000.0, "high_price": 1120.0, "low_price": 990.0, "trade_price": 1100.0},
        {"opening_price": 1100.0, "high_price": 1150.0, "low_price": 1080.0, "trade_price": 1300.0},
    ]
    rows = SMV._normalize_ohlc(candles)
    assert rows[0][3] == 100.0                                # day0 종가 강제 100(§6.1)
    assert rows[0][0] == round(1000.0 / 1100.0 * 100.0, 4)    # day0 시가 정규화
    assert rows[0][1] >= 100.0 and rows[0][2] <= 100.0        # low<=open/close<=high 불변식


def test_build_online_writes_expected_schema(monkeypatch, tmp_path):
    def fake_fetch(market, count, to):
        return _FAKE_CANDLES_DESC[::-1]   # 이미 오름차순으로 준다고 가정

    monkeypatch.setattr(SMV, "_fetch_candles", fake_fetch)
    out = tmp_path / "seed.json"
    data = SMV.build_online(out)

    assert out.exists()
    assert data["schema"] == "market_village_market_seed/v1"
    assert set(data["categories"]) == {"large_stable", "mid_alt", "meme", "stable"}
    for cat, info in data["categories"].items():
        assert info["ohlc"][0][3] != 0
        assert info["_meta_blind"] is True
        assert "upbit:" in info["_meta_origin"]   # 실데이터 출처 표시(내부 메타만)
