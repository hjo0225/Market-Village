"""T-a~T-c · 살아있는 마을 — 에이전트 메모리 (agent_state 순수 파생 봉인).

T-a 골격: 상수는 tuning 단일 소스, 순수성·결정론·전 페르소나 baseline 계약.
T-b 감쇠: 수렴·폭주 차단(밴드 25)·절대 클램프 [0,100]·미래 누설 없음(R6).
T-e 기억 발화: speech_flavor(공개 트랙 archive만 입력) + offline_conversation 배선.
T-c NPC별 래포+대화 기억: 플레이어 트랙(_social_log만 입력), persuade 이중 계약.
"""

from __future__ import annotations

import copy
import random

from sim import agent_state, board_v2, personas, resistance, tuning
from sim import clone_spec as CS
from sim.game_run import GameRun

_ALL_PERSONAS = personas.TRADER_PERSONAS + personas.SNS_PERSONAS
_HIGH_FEAR = {"id": "n_reg", "headline": "규제 전격 발표", "tone": "fear",
              "intensity": "high"}


def _delta_archive(aid: str, axis: str, days: int, delta: float = 8.0) -> dict:
    """스탠스 없는 합성 아카이브 — 감정 델타만(기억 발화 미발동, 감쇠 검증용)."""
    return {f"{d}:e": {"agent_deltas": {aid: {axis: delta}}} for d in range(days)}


# ========================= T-a 골격 봉인 ================================== #

def test_constants_single_source_in_tuning():
    # R6/R7 표준화 — agent_state 상수는 tuning이 단일 진실 소스(재수출).
    assert tuning.AGENT_EMOTION_DECAY == 0.15
    assert tuning.AGENT_EMOTION_BAND == 25.0
    assert agent_state.DECAY == tuning.AGENT_EMOTION_DECAY
    assert agent_state.BAND == tuning.AGENT_EMOTION_BAND


def test_agent_emotions_pure_no_input_mutation():
    # 순수성 — n회 호출 == 1회 호출, 입력 archive는 절대 변이되지 않는다(R1).
    conv = board_v2.offline_conversation(
        "fear", {}, [_HIGH_FEAR], random.Random(7))
    archive = {"0:n_reg": conv}
    snapshot = copy.deepcopy(archive)
    once = agent_state.agent_emotions("doomposter", archive, 5)
    for _ in range(3):
        assert agent_state.agent_emotions("doomposter", archive, 5) == once
    assert archive == snapshot                       # 입력 무변이


def test_all_16_personas_have_full_baseline():
    # 전 출연진(매매 8 + 관중 8) — 빈 아카이브면 감정 == baseline(5축 전부).
    assert len(_ALL_PERSONAS) == 16
    for p in _ALL_PERSONAS:
        emo = agent_state.agent_emotions(p["id"], {}, 0)
        assert set(emo) == set(agent_state.AXES)
        for axis in agent_state.AXES:
            assert emo[axis] == float(p[axis])


def test_unknown_agent_returns_safe_default():
    assert agent_state.agent_emotions("nope", {}, 3) == {}


def test_agent_emotions_deterministic():
    # RNG 없음 — 같은 입력이면 언제 몇 번을 불러도 같은 출력.
    archive = _delta_archive("newbie", "fear", days=4)
    a = agent_state.agent_emotions("newbie", archive, 10)
    b = agent_state.agent_emotions("newbie", dict(archive), 10)
    assert a == b


# ========================= T-b 감쇠 봉인 (R6) ============================= #

def test_deviation_converges_to_baseline():
    # 이벤트 1회 후 무이벤트 15일 — 주축 편차 < 3 (0.85^15 ≈ 0.087).
    archive = _delta_archive("newbie", "fear", days=1)   # day 0에 +8 한 번
    baseline = next(float(p["fear"]) for p in _ALL_PERSONAS if p["id"] == "newbie")
    emo = agent_state.agent_emotions("newbie", archive, 15)
    assert 0 < abs(emo["fear"] - baseline) < 3


def test_runaway_blocked_at_band():
    # 30일 연속 +8 델타 — 편차는 정확히 밴드 25에서 멈춘다(폭주 구조 차단).
    archive = _delta_archive("bull_hoper", "fear", days=30)   # baseline fear 20
    emo = agent_state.agent_emotions("bull_hoper", archive, 29)
    assert emo["fear"] == 20.0 + agent_state.BAND             # == 45.0


def test_absolute_clamp_0_100():
    # baseline 92 + 밴드 25 = 117 → 절대 클램프 100에서 캡.
    archive = _delta_archive("jackpot_gambler", "greed", days=30)
    emo = agent_state.agent_emotions("jackpot_gambler", archive, 29)
    assert emo["greed"] == 100.0


def test_no_future_leakage():
    # day N+1 이벤트는 upto_day=N 계산에 영향을 주지 않는다.
    archive = {"5:e": {"agent_deltas": {"newbie": {"fear": 8.0}}}}
    assert (agent_state.agent_emotions("newbie", archive, 4)
            == agent_state.agent_emotions("newbie", {}, 4))


# ========================= T-e 기억 발화 ================================== #

_MARKERS = (agent_state.MEM_MATCHED, agent_state.MEM_MISSED, agent_state.MEM_SPLIT)


def _stance_conv(aid: str, stance: str, verdict: str) -> dict:
    return {"verdict": verdict, "agent_deltas": {},
            "threads": [{"author_id": aid, "stance": stance, "text": "x",
                         "comments": []}]}


def test_speech_flavor_memory_markers():
    # 지난 대화의 내 스탠스 vs 마을 결론 — 맞힘/틀림/갈림 3분기.
    assert agent_state.speech_flavor(
        "newbie", {"0:e": _stance_conv("newbie", "up", "up")}, 2) \
        == agent_state.MEM_MATCHED
    assert agent_state.speech_flavor(
        "newbie", {"0:e": _stance_conv("newbie", "up", "down")}, 2) \
        == agent_state.MEM_MISSED
    assert agent_state.speech_flavor(
        "newbie", {"0:e": _stance_conv("newbie", "up", "split")}, 2) \
        == agent_state.MEM_SPLIT


def test_speech_flavor_no_prior_event_none():
    # 첫 이벤트 날(과거 없음) — 기억도 감정 여운도 없으면 None.
    assert agent_state.speech_flavor("newbie", {}, 0) is None
    # 미래 누설 없음 — 같은 날(upto_day) 이벤트는 '지난번'이 아니다.
    assert agent_state.speech_flavor(
        "newbie", {"3:e": _stance_conv("newbie", "up", "up")}, 3) is None


def test_speech_flavor_emotion_fallback():
    # 기억(스탠스 참여)이 없을 때만 — 주축 편차 ≥ 10이면 축별 고정 마커.
    archive = _delta_archive("panic_ant", "fear", days=3)   # 편차 ≈ 17.5
    flavor = agent_state.speech_flavor("panic_ant", archive, 2)
    assert flavor == agent_state.EMO_MARKER["fear"]
    # 편차가 작으면(1회 이벤트 후 오래 지남) 발화 없음.
    calm = _delta_archive("panic_ant", "fear", days=1)
    assert agent_state.speech_flavor("panic_ant", calm, 15) is None


def test_speech_flavor_at_most_one():
    # 기억+감정이 겹쳐도 향미는 1개(기억 우선) — 감정 마커가 덧붙지 않는다.
    archive = _delta_archive("panic_ant", "fear", days=3)
    archive["0:s"] = _stance_conv("panic_ant", "up", "up")
    flavor = agent_state.speech_flavor("panic_ant", archive, 4)
    assert flavor == agent_state.MEM_MATCHED
    assert agent_state.EMO_MARKER["fear"] not in flavor


def _offline(seed=7, archive=None, day=0, stats=None):
    return board_v2.offline_conversation(
        "fear", stats or {}, [_HIGH_FEAR], random.Random(seed),
        archive=archive, day=day)


def test_offline_conversation_flavor_wiring():
    # ① 첫 이벤트 날 — 기억 접두 없음 / 둘째 이벤트 날 같은 작성자 — 접두 있음.
    conv0 = board_v2.offline_conversation(
        "fear", {}, [_HIGH_FEAR], random.Random(7))   # 기존 시그니처 무수정 호출
    for th in conv0["threads"]:
        assert not th["text"].startswith(_MARKERS)
    authors0 = {th["author_id"] for th in conv0["threads"]}
    conv1 = _offline(seed=8, archive={"0:n_reg": conv0}, day=3)
    flavored = [th for th in conv1["threads"] if th["author_id"] in authors0]
    assert flavored and all(th["text"].startswith(_MARKERS) for th in flavored)
    # 향미는 글 작성자만 — 댓글은 접두 없음(⑤ 발화당 최대 1개와 짝).
    for th in conv1["threads"]:
        for c in th["comments"]:
            assert not c["text"].startswith(_MARKERS)


def test_offline_conversation_flavor_determinism_and_purity():
    conv0 = _offline(seed=7)
    archive = {"0:n_reg": conv0}
    a = _offline(seed=8, archive=archive, day=3)
    b = _offline(seed=8, archive=archive, day=3)
    assert a == b                                     # ② 같은 archive = 같은 텍스트
    # ③ 클론 스탯이 달라도 생성 대화는 동일(공개 트랙 순수성, council F2).
    c = _offline(seed=8, archive=archive, day=3, stats={"급락패닉저항": 5.0})
    assert c == a


def test_offline_conversation_flavor_schema_contracts():
    # ④ validate 스키마 통과 + to_posts 계약 불변(접두가 텍스트에 보존).
    conv0 = _offline(seed=7)
    conv1 = _offline(seed=8, archive={"0:n_reg": conv0}, day=3)
    assert board_v2.validate(conv1) is not None
    posts = board_v2.to_posts(conv1)
    assert posts and all(
        {"author", "author_id", "stance", "text", "comments"} <= set(p) for p in posts)
    assert any(p["text"].startswith(_MARKERS) for p in posts)


# ========================= T-c NPC별 래포+대화 기억 ======================== #

CLONE = CS.build_clone_spec({"q_panic": 0.5})


def _g(run_id="ags"):
    return GameRun(CLONE, category="meme", start_price=100.0, run_id=run_id)


def test_npc_rapport_step_mirrors_shared_pool():
    # 공유 풀과 같은 폭(±8) — resistance._RAPPORT_STEP과 어긋나면 즉시 적발.
    assert agent_state.NPC_RAPPORT_STEP == resistance._RAPPORT_STEP


def test_persuade_dual_contract():
    # ① 기존 키 계약 불변(공유 풀 공식 그대로) + 신규 npc_rapport/npc_line 동시.
    g = _g()
    out = g.persuade("value_investor", direction="calm", roll=0.0)
    assert {"accepted", "success_prob", "stats", "rapport"} <= set(out)
    assert out["accepted"] is True
    assert out["rapport"] == 58.0 and g.rapport == 58.0     # 기존 공유 풀 공식
    assert out["npc_rapport"] == 58.0                        # 개별 래포도 +8
    assert isinstance(out["npc_line"], str) and out["npc_line"]
    # ② 다른 NPC의 개별 래포는 불변(50 시작 그대로).
    assert agent_state.npc_rapport("panic_ant", g._social_log, g.day) == 50.0


def test_npc_rapport_decays_toward_50():
    # ③ 마지막 대화 후 7일 — 50 방향으로 감쇠(R6: 0.10/일·클램프 0~100·평형 50).
    log = [{"day": 0, "kind": "persuade", "npc_id": "panic_ant",
            "direction": "calm", "accepted": True},
           {"day": 0, "kind": "fgi", "tone": "calm"}]     # fgi는 개별 래포 무관
    day0 = agent_state.npc_rapport("panic_ant", log, 0)
    assert day0 == 58.0
    day7 = agent_state.npc_rapport("panic_ant", log, 7)
    assert 50.0 < day7 < day0                          # 58 → 50 방향으로 회귀
    assert abs(day7 - (50.0 + 8.0 * 0.9 ** 7)) < 1e-9  # 결정론 공식 그대로


def test_npc_rapport_clamped_0_100():
    accepts = [{"day": 0, "kind": "persuade", "npc_id": "x",
                "direction": "calm", "accepted": True}] * 10
    rejects = [{**e, "accepted": False} for e in accepts]
    assert agent_state.npc_rapport("x", accepts, 0) == 100.0
    assert agent_state.npc_rapport("x", rejects, 0) == 0.0


def test_npc_line_reflects_previous_record():
    # ⑤ 연속 수락 — 두 번째 응답은 "저번에 네 말 듣길 잘했지" 신뢰 접두.
    g = _g()
    first = g.persuade("value_investor", direction="calm", roll=0.0)
    assert not first["npc_line"].startswith(
        (agent_state.NPC_MEM_ACCEPTED, agent_state.NPC_MEM_REJECTED))
    second = g.persuade("value_investor", direction="calm", roll=0.0)
    assert second["npc_line"].startswith(agent_state.NPC_MEM_ACCEPTED)
    # 직전이 거절이었다면 "또 너냐" 접두(템플릿 결정론).
    line = agent_state.npc_reply_line(
        "value_investor", "calm", True, 50.0,
        [{"day": 0, "kind": "persuade", "npc_id": "value_investor",
          "direction": "calm", "accepted": False}])
    assert line.startswith(agent_state.NPC_MEM_REJECTED)


def test_npc_chat_memory_recent_past_only():
    log = [{"day": d, "kind": "persuade", "npc_id": "panic_ant",
            "direction": "calm", "accepted": bool(d % 2)} for d in range(5)]
    mem = agent_state.npc_chat_memory("panic_ant", log, 3)
    assert [e["day"] for e in mem] == [1, 2, 3]        # 최근 3건, 최신이 마지막
    assert agent_state.npc_chat_memory("panic_ant", log, 0) == log[:1]  # 당일 포함


def test_new_run_resets_npc_rapport():
    # ⑥ 회차 리셋(R4) — 빈 로그의 fold == 50.
    g = _g()
    g.persuade("value_investor", direction="calm", roll=0.0)
    g.new_run("ags2")
    assert g._social_log == []
    assert agent_state.npc_rapport("value_investor", g._social_log, g.day) == 50.0


def test_npc_rapport_survives_doc_roundtrip():
    # ⑦ to_doc/from_doc — social_log 경유로 개별 래포 보존(신규 직렬화 키 0).
    g = _g()
    g.persuade("value_investor", direction="calm", roll=0.0)
    g2 = GameRun.from_doc(g.to_doc(), fate_line=g.fl)
    assert (agent_state.npc_rapport("value_investor", g2._social_log, g2.day)
            == agent_state.npc_rapport("value_investor", g._social_log, g.day))


def test_state_does_not_expose_individual_rapport():
    # ⑧ M6 — 상태 전용 대시보드 금지: state()에 개별 래포 노출 없음.
    g = _g()
    g.persuade("value_investor", direction="calm", roll=0.0)
    assert "npc_rapport" not in g.state()
