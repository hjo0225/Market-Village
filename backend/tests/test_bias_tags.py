"""T-47b — 시나리오·체인 선택지의 편향 태그(bias_tags) 데이터 + 검증기.

2층 편향 5축(loss/fomo/disp/over/panic)을 '실제 행동' 신호로 다는 태깅.
시장 시나리오 = 투자결정에 직접 태깅. 체인 = 함정 NPC의 충동을 끌어안는
(감정델타가 함정쪽으로 움직이는) 선택에만 그 NPC bias. 나머지·멘토 NPC = 태그 없음.
"""

from __future__ import annotations

import copy

import pytest

from sim import chain as C
from sim import disposition as D
from sim import scenario as S


# ── 단일 소스 축 정합 ───────────────────────────────────────────────────
def test_bias_axes_match_expected_bias_keys():
    assert set(D.BIAS_AXES) == set(D.expected_bias("위험중립형").keys())


# ── 시장 시나리오 태그 (§ 투자결정) ─────────────────────────────────────
# T-48b 구성개념 정합(확정 매핑): panic(공포로 던지기)=cut·panic_sell /
# loss(손실 실현 거부=버티기)=hold·ignore / over=buy_dip·day_trade / fomo=chase.
# 예전엔 cut·panic_sell에 panic·loss가 함께 붙어 두 축 actual_bias가 항상 동일했다.
@pytest.mark.parametrize(
    "event,cid,tags",
    [
        ("market_crash", "cut", ["panic"]),
        ("market_crash", "hold", ["loss"]),
        ("market_crash", "buy_dip", ["over"]),
        ("market_surge", "chase", ["fomo", "over"]),
        ("rumor_spread", "panic_sell", ["panic"]),
        ("rumor_spread", "ignore", ["loss"]),
        ("market_volatile", "day_trade", ["over"]),
    ],
)
def test_scenario_choice_bias_tags(event, cid, tags):
    assert S.get_choice(event, cid).get("bias_tags") == tags


def test_scenario_disciplined_choices_untagged():
    # 관망·확인·자리뜸만 편향 없음(태그 부재). hold·ignore는 이제 loss(버티기)로 태깅.
    for event, cid in [("market_surge", "watch"),
                       ("rumor_spread", "verify"), ("market_volatile", "step_away")]:
        assert not S.get_choice(event, cid).get("bias_tags")


def test_panic_and_loss_are_decoupled():
    # T-48b — panic(공포로 던지기)과 loss(손실 실현 거부=버티기)는 서로 다른 선택에
    # 태깅돼야 한다. 한 선택에 둘 다 붙으면 actual_bias[panic]≡actual_bias[loss]로
    # 두 축이 영구히 구별 불가(원래 버그).
    for ev in S.load_scenarios().values():
        for ch in ev["choices"]:
            tags = ch.get("bias_tags") or []
            assert not ("panic" in tags and "loss" in tags), \
                f"{ch['id']}에 panic·loss 동시 태깅 — 두 축 구별 불가"


def test_scenarios_load_and_validate_clean():
    # 로더가 태그 붙은 데이터를 검증 통과로 읽는다
    assert S.validate_scenarios(S.load_scenarios()) is not None


def test_scenario_validator_rejects_bad_bias_tag():
    bad = copy.deepcopy(S.load_scenarios())
    bad["market_crash"]["choices"][0]["bias_tags"] = ["bogus"]
    with pytest.raises(S.ScenarioError):
        S.validate_scenarios(bad)


# ── 체인 태그 (끌어안는 응답만) ─────────────────────────────────────────
def _chain_choice(chains, npc, stage, cid):
    return next(c for c in chains[npc][stage]["choices"] if c["id"] == cid)


@pytest.mark.parametrize(
    "npc,stage,cid,tags",
    [
        ("panic_ant", 2, "A", ["panic"]),          # "그 새벽의 너를 이해해"(fear+)
        ("fomo_scalper", 2, "B", ["fomo"]),        # "나도 조급해"(greed+)
        ("conspiracy_influencer", 1, "A", ["fomo"]),  # "맞장구"(anxiety+)
        ("jackpot_gambler", 1, "A", ["over"]),     # "축하해요! 한 잔"(greed+)
    ],
)
def test_chain_embrace_choice_tagged(npc, stage, cid, tags):
    chains = C.load_chains()
    assert _chain_choice(chains, npc, stage, cid).get("bias_tags") == tags


def test_chain_mentor_npcs_untagged():
    # 멘토 NPC(정호·유리·태산·미나) 선택지는 편향 태그 없음
    chains = C.load_chains()
    for npc in ("value_investor", "quant_trader", "macro_whale", "contrarian"):
        for stage in (1, 2):
            for ch in chains[npc][stage]["choices"]:
                assert not ch.get("bias_tags")


def test_chains_validate_clean():
    assert C.validate_chains(C.load_chains()) is not None


def test_chain_validator_rejects_bad_bias_tag():
    bad = copy.deepcopy(C.load_chains())
    bad["panic_ant"][1]["choices"][0]["bias_tags"] = ["nope"]
    with pytest.raises(C.ChainDataError):
        C.validate_chains(bad)
