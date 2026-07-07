"""T-20: NPC 체인 24편 데이터 검증 (문서 §6).

data/npc_chains.json이 스키마(8 NPC × 3단계, 4축 효과)를 만족하는지, 그리고
로더가 int 단계 키로 변환하는지 확인한다.
"""

from sim.chain import CHAIN_NPCS, load_chains, validate_chains


def test_data_loads_and_validates():
    chains = load_chains()
    assert chains, "npc_chains.json 비어있음(T-20 데이터 필요)"
    validate_chains(chains)   # 위반 시 ChainDataError


def test_all_8_npcs_three_stages():
    chains = load_chains()
    for npc in CHAIN_NPCS:
        assert set(chains[npc]) == {1, 2, 3}, f"{npc} 단계 누락"


def test_stage3_has_reward_no_choices():
    chains = load_chains()
    for npc in CHAIN_NPCS:
        s3 = chains[npc][3]
        assert not s3.get("choices")
        assert (s3.get("reward") or {}).get("deltas"), f"{npc} 단계3 보상 없음"


def test_every_text_nonempty():
    chains = load_chains()
    for npc in CHAIN_NPCS:
        for stage in (1, 2, 3):
            assert chains[npc][stage]["text"].strip(), f"{npc} {stage} 텍스트 비어있음"
