"""T-10: NPC 8+8 → 4축 톤 가중치 + 게시판 톤→플레이어 델타.

기존 personas.py(5축)를 수정하지 않고, 새 npc_tone 레이어에서 4축
(fear/greed/anxiety/restlessness) 톤 벡터를 결정론적으로 파생한다. 게시판
전체 톤이 플레이어 감정 델타의 방향·크기에 반영됨을 검증한다.
"""

from sim.npc_tone import TONE_AXES, board_tone_delta, npc_tone
from sim.personas import SNS_PERSONAS, TRADER_PERSONAS


def test_all_16_npcs_have_4axis_tone():
    for p in TRADER_PERSONAS + SNS_PERSONAS:
        tone = npc_tone(p["id"])
        assert set(tone) == set(TONE_AXES)
        assert all(0.0 <= v <= 1.0 for v in tone.values())


def test_tone_differs_by_disposition():
    # 공포팔이(둠포스터)와 치어리더는 미는 축이 다르다.
    doom = npc_tone("doomposter")
    cheer = npc_tone("cheerleader")
    assert doom["fear"] > cheer["fear"]
    assert cheer["greed"] > doom["greed"]
    # 주축(argmax)이 서로 다르다.
    assert max(doom, key=doom.get) != max(cheer, key=cheer.get)


def test_rumor_spreaders_push_anxiety():
    # 루머 민감 페르소나(conspiracy/doomposter/newbie)는 anxiety 톤이 높다.
    assert npc_tone("conspiracy_influencer")["anxiety"] > npc_tone("value_investor")["anxiety"]


def test_unknown_id_is_zero_tone():
    tone = npc_tone("clone")
    assert all(v == 0.0 for v in tone.values())


def test_board_tone_delta_reflects_crowd_composition():
    # 공포 크라우드 → fear 델타가 양수로 크게.
    fearful = [
        {"author_id": "doomposter", "stance": "down", "text": "폭락 온다",
         "comments": [{"author_id": "newbie", "stance": "down", "text": "무서워요"}]},
    ]
    d = board_tone_delta(fearful)
    assert set(d) == set(TONE_AXES)
    assert d["fear"] > 0
    # 공포 게시판은 greed보다 fear를 더 민다.
    assert d["fear"] > d["greed"]


def test_board_tone_delta_greedy_crowd_pushes_greed():
    greedy = [
        {"author_id": "bull_hoper", "stance": "up", "text": "가즈아",
         "comments": [{"author_id": "cheerleader", "stance": "up", "text": "더 간다"}]},
    ]
    d = board_tone_delta(greedy)
    assert d["greed"] > d["fear"]


def test_empty_board_is_no_delta():
    assert board_tone_delta([]) == {}
