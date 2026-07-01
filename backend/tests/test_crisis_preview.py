"""사용자 피드백(2026-07-01) · "위기 개입은 위기가 실제 발생했을 때만 갑작스러운
이벤트로 튀어나와야 한다" — 매일 상시 A/B/C 버튼 노출은 실제 서비스 흐름이 아님.

`GameRun.preview_crisis()` — 부작용 없이 "오늘 위기가 있는지"만 미리 계산한다.
`intervention`은 저항 판정에만 영향을 주고 위기 발생 자체와는 무관하므로
(trap_pipeline.run_crisis STEP1은 intervention 이전에 결정됨), 프리뷰가 실제
advance_day 결과와 항상 일치해야 한다(결정론).
"""

from __future__ import annotations

from sim.game_run import GameRun
from sim import clone_spec as CS
from sim.trap_pipeline import Intervention
from sim.resistance import STRATEGY_B

CLONE = CS.build_clone_spec({"q_panic": 1.0, "q_fomo": 1.0})


def _g(**kw):
    base = dict(category="meme", start_price=100.0, run_id="run1")
    base.update(kw)
    return GameRun(CLONE, **base)


def test_preview_calm_day_returns_no_trap():
    g = _g()
    # day0은 평온한 날(위 픽스처 조사에서 확인) — 프리뷰도 동일해야 함.
    preview = g.preview_crisis()
    assert preview["trap"] is None
    assert g.day == 0   # 부작용 없음 — day가 안 늘어남


def test_preview_does_not_mutate_state():
    g = _g()
    before = g.state()
    g.preview_crisis()
    assert g.state() == before
    assert g.store.get_snapshot("run1", 0) is None   # 스냅샷도 기록 안 됨


def test_preview_matches_actual_trap_on_crisis_day():
    g = _g()
    for _ in range(21):
        g.advance_day()   # day0..20 소진, day21이 위기일(픽스처 조사에서 확인)
    preview = g.preview_crisis()
    assert preview["trap"] == "G1"
    assert preview["trap_name"] == "익절 거부"

    snap = g.advance_day()   # 실제 진행 — 프리뷰와 같은 trap이어야(결정론)
    assert snap.trap == "G1"


def test_preview_result_independent_of_intervention_presence():
    """intervention 유무·roll은 위기 '발생' 자체엔 영향 없다(저항 판정에만 영향)."""
    g_a = _g(run_id="a")
    g_b = _g(run_id="b")
    for _ in range(21):
        g_a.advance_day()
        g_b.advance_day(intervention=Intervention(STRATEGY_B, 80.0), roll=10.0)
    assert g_a.preview_crisis()["trap"] == g_b.preview_crisis()["trap"] == "G1"


def test_preview_after_finished_run_returns_no_trap():
    g = _g()
    for _ in range(30):
        g.advance_day()
    assert g.finished is True
    assert g.preview_crisis()["trap"] is None


def test_preview_bundle_matches_single_trap_when_only_one_fires():
    # T-216 — 단일 트리거 날엔 bundle이 정확히 1개, trap 필드와 일치(회귀 없음).
    g = _g()
    for _ in range(21):
        g.advance_day()
    preview = g.preview_crisis()
    assert len(preview["bundle"]) == 1
    assert preview["bundle"][0]["category"] == "meme"
    assert preview["bundle"][0]["trap"] == preview["trap"] == "G1"


def test_preview_bundle_empty_on_calm_day():
    g = _g()
    assert g.preview_crisis()["bundle"] == []
