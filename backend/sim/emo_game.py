"""T-7: 미연시 턴 루프 본체 — EmoGameRun (신규 모듈).

하루 턴: 시장이벤트 → 게시판 강제노출(감정 델타 1회 적용) → 선택지 → 결과반영
→ 다음 날. 30일(events 길이)만큼 반복 후 종료. 종료 시 감정 압축판정(T-4)과
재산 수준으로 엔딩 입력(T-13)을 낸다.

설계상 기존 game_run.py(구 "AI 클론 30일 관찰" 게임, 라이브)를 대체하지만,
라이브 안전을 위해 그 파일을 수정하지 않고 별개 상태머신으로 둔다(컷오버 시
구 엔진 삭제). 구 6함정 확률판정 없음 — 결과는 오직 플레이어 선택.

멱등 불변식(PLAN-READY 4d): 노출 델타는 '그 날에 진입할 때' 딱 1회 적용된다.
board()는 순수 표시(재계산)라 몇 번 불러도 감정/상태를 바꾸지 않는다. 직렬화
복원(from_doc)은 이미 진입한 날의 노출을 재적용하지 않는다.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from . import avoidance, board_exposure, chain, companion
from . import ending as _ending
from . import scenario as _scenario
from .disposition import BIAS_AXES, build_initial_emotion_v2, diagnose
from .fate_line import CATEGORIES
from .personas import npc_scheds
from .player_emotion.deltas import apply_delta, decay_toward_equilibrium
from .player_emotion.log import EmotionLog, record_snapshot
from .player_emotion.state import PlayerEmotionState
from .player_emotion.verdict import compute_verdict

START_VALUE = 1_000_000.0

# T-47c (RETRO 4b) — 편향축 표본이 이 미만이면 actual_bias에서 비노출(과소표본
# 왜곡 방지). 비율식이라 1/1=100%처럼 과장되는 걸 막는다.
BIAS_MIN_SAMPLE = 3

DEFAULT_CLONE_NAME = "내 클론"   # T-28 — 이름 미입력 시 기본값
_MAX_NAME_LEN = 12


def _clean_name(name: str | None) -> str:
    """플레이어 입력 이름을 정리 — 공백 제거·길이 제한, 비면 기본값."""
    cleaned = (name or "").strip()[:_MAX_NAME_LEN]
    return cleaned or DEFAULT_CLONE_NAME

# 재산 축(T-11/T-30): 포트폴리오 = 시장 4카테고리 + 현금(cash·KRW·시장무관·0수익).
# 스테이블코인(USDT)과 현금(KRW)을 분리(#3) — 손절 도피처는 **현금**(완전 이탈),
# USDT는 보유 중인 패시브 스테이블코인(시장에 남아있음). cash는 시장 시리즈가 없어
# 수익률 0으로 자동 취급(fate_line.change_rate 미존재 카테고리→0) — 시드 불요.
CASH = "cash"
PORTFOLIO_CATEGORIES = (*CATEGORIES, CASH)
_STABLE = "stable"                                    # USDT — 패시브 스테이블코인
_HAVEN = CASH                                         # 손절 도피처(완전 이탈=현금)
_RISK = tuple(c for c in CATEGORIES if c != _STABLE)  # 위험자산(대형·알트·밈)

# T-30c 캐시아웃 딜레마 트리거(🙋 잠정 튜닝치 — council). **감정 정점** 기반: 탐욕이나
# 공포가 임계 이상으로 치솟은 중반에 "지금 현금화할까 계속 갈까" 1회 발동. 포트폴리오
# 스윙 기반은 분산투자자(스윙 0~3%)에겐 절대 안 떠 폐기 — 이 게임은 감정 패턴이 핵심이라
# 감정 정점(탐욕에 눈멀거나 공포에 질린 순간)이 현금화 성찰의 자연스러운 방아쇠다.
CASHOUT_MIN_DAY = 3            # 이 날 이후부터(초반 제외)
CASHOUT_EMOTION_PEAK = 72     # 탐욕 or 공포가 이 이상(감정 정점)일 때
CASHOUT_RISK_SHARE = 0.35     # 위험자산 비중(뺄 게 있어야 함)
_CASHOUT_FRAC = 0.7           # 현금화 선택 시 위험자산의 이 비율을 현금으로


def _holdings_from_allocation(allocation: dict[str, float] | None) -> dict[str, float]:
    """배분 분수(합≈1)를 카테고리별 초기 보유액으로. None/빈 값·합0이면 균등 분배."""
    even = {c: 1.0 / len(PORTFOLIO_CATEGORIES) for c in PORTFOLIO_CATEGORIES}
    if not allocation:
        w = even
    else:
        raw = {c: max(0.0, float(allocation.get(c, 0.0))) for c in PORTFOLIO_CATEGORIES}
        total = sum(raw.values())
        w = {c: raw[c] / total for c in PORTFOLIO_CATEGORIES} if total > 0 else even
    return {c: round(START_VALUE * w[c], 2) for c in PORTFOLIO_CATEGORIES}

# 클론이 하루에 머무는 장소 순환(동행 후보 = 그 장소에 일과가 있는 NPC).
_ROUTE_CYCLE = ("카페", "광장", "펍", "일터", "운동")


def _day_rng(seed: int, day: int) -> random.Random:
    """(seed, day)로 결정론 rng — 같은 날은 항상 같은 게시판(재생 가능)."""
    return random.Random(seed * 1000 + day)


def _default_route(n: int) -> list[str]:
    """일수만큼 기본 동선(장소 순환). 플레이어가 avoid로 재배치할 수 있다."""
    return [_ROUTE_CYCLE[i % len(_ROUTE_CYCLE)] for i in range(n)]


@dataclass
class EmoGameRun:
    emotion: PlayerEmotionState
    events: list[str]
    cat_returns: dict[str, list[float]]   # 카테고리별 일별 수익률(분수) — 실 FateLine
    seed: int
    day: int = 0
    clone_name: str = "내 클론"   # T-28 — 플레이어가 정한 클론 이름(게임 내내 표시)
    # 재산 축(T-11): 카테고리별 보유액(KRW). 재산=합. 선택의 매매가 배분을 조절.
    holdings: dict[str, float] = field(default_factory=dict)
    log: EmotionLog = field(default_factory=EmotionLog)
    # 동행배치(T-18): 클론 동선·야간 지정·오늘의 companion.
    clone_route: list[str] = field(default_factory=list)
    schedules: dict[str, dict[int, str]] = field(default_factory=npc_scheds)
    designations: dict[int, str] = field(default_factory=dict)
    companion_id: str | None = None
    special_event_count: int = 0   # 체인 이벤트(T-19)가 증가시킴 → E5 히든 엔딩
    # 동행 체인(T-19): NPC별 발동 단계·개별 rapport·오늘의 미해결 체인.
    chain_progress: dict[str, int] = field(default_factory=dict)
    rapport: dict[str, float] = field(default_factory=dict)
    pending_chain: dict | None = None
    chains: dict = field(default_factory=chain.load_chains)
    cashout_offered: bool = False   # T-30c — 캐시아웃 딜레마는 게임당 1회만
    last_market: dict[str, float] = field(default_factory=dict)   # T-35 — 마지막 정산일 카테고리별 수익률(%)
    # T-47c — 1층 정적 성향 진단(시작 시 diagnose, 플레이 중 불변) + 2층 실제 행동
    # 편향 원장/집계. bias_tally[axis] = {"hits","opportunities"} → actual_bias 비율식.
    disposition: dict | None = None
    choice_history: list[dict] = field(default_factory=list)
    bias_tally: dict[str, dict[str, int]] = field(default_factory=dict)
    # T-47f — 엔딩 리포트 서술(LLM or 결정론). 게임당 1회 생성 후 캐시(과금 상한·멱등).
    report_narrative: list[str] | None = None

    # --- 생성 ------------------------------------------------------------- #
    @classmethod
    def new(
        cls,
        answers: dict,
        events: list[str],
        cat_returns: dict[str, list[float]],
        seed: int,
        allocation: dict[str, float] | None = None,
        name: str | None = None,
    ) -> "EmoGameRun":
        run = cls(
            emotion=build_initial_emotion_v2(answers),
            events=list(events),
            cat_returns={c: list(cat_returns.get(c, [])) for c in CATEGORIES},
            seed=seed,
            clone_name=_clean_name(name),
            holdings=_holdings_from_allocation(allocation),
            clone_route=_default_route(len(events)),
            disposition=diagnose(answers),   # T-47c — 1층 선언(시작 시 확정, 불변)
            bias_tally={axis: {"hits": 0, "opportunities": 0} for axis in BIAS_AXES},
        )
        run._enter_day()   # day 0 노출 델타 1회 + companion 결정
        return run

    # --- 재산(다자산) ---------------------------------------------------- #
    @property
    def portfolio_value(self) -> float:
        """카테고리별 보유액 합 = 총자산."""
        return round(sum(self.holdings.values()), 2)

    def _rebalance(self, shift: float) -> None:
        """매매행동을 자산 배분 이동으로 번역. shift>0=현금(cash)→위험자산(추격),
        shift<0=위험자산→현금(손절). 손절 후 위험자산 반등을 놓치는 행동적 인과.
        도피처는 현금(_HAVEN=cash) — USDT(stable)는 손대지 않는 패시브 보유."""
        if shift == 0.0:
            return
        if shift < 0.0:                       # 손절: 위험자산 → 현금
            frac = min(1.0, -shift)
            moved = 0.0
            for cat in _RISK:
                m = self.holdings.get(cat, 0.0) * frac
                self.holdings[cat] = round(self.holdings.get(cat, 0.0) - m, 2)
                moved += m
            self.holdings[_HAVEN] = round(self.holdings.get(_HAVEN, 0.0) + moved, 2)
        else:                                 # 추격: 현금 → 위험자산(현 위험 비중대로)
            frac = min(1.0, shift)
            moved = self.holdings.get(_HAVEN, 0.0) * frac
            self.holdings[_HAVEN] = round(self.holdings.get(_HAVEN, 0.0) - moved, 2)
            risk_total = sum(self.holdings.get(c, 0.0) for c in _RISK)
            for cat in _RISK:
                w = (self.holdings.get(cat, 0.0) / risk_total
                     if risk_total > 0 else 1.0 / len(_RISK))
                self.holdings[cat] = round(self.holdings.get(cat, 0.0) + moved * w, 2)

    # --- 상태 조회 -------------------------------------------------------- #
    @property
    def is_over(self) -> bool:
        return self.day >= len(self.events)

    @property
    def emotion_log(self) -> EmotionLog:
        return self.log

    def board(self) -> dict:
        """현재 날의 게시판(표시용, 멱등). 감정/상태를 변이하지 않는다."""
        if self.is_over:
            raise RuntimeError("game is over")
        return board_exposure.render_board(
            self.events[self.day], _day_rng(self.seed, self.day)
        )

    # --- 진행 ------------------------------------------------------------- #
    def _enter_day(self) -> None:
        """그 날에 진입할 때 노출 델타 1회 적용 + 오늘의 companion 결정."""
        if self.is_over:
            self.companion_id = None
            return
        if self.day > 0:
            # T-27 (4b) — 밤사이 평형 회귀(누적 포화 방지). 첫날(진단 직후)은 유지.
            self.emotion = decay_toward_equilibrium(self.emotion)
        board = self.board()
        delta = board_exposure.exposure_delta(self.events[self.day], board["threads"])
        self.emotion = apply_delta(self.emotion, delta)
        self._resolve_companion()
        self._maybe_start_chain()

    # --- 동행배치 (T-18) -------------------------------------------------- #
    def _resolve_companion(self) -> None:
        """오늘 장소의 후보 중 companion 결정(지정 우선, 없으면 4축 끌림). 멱등."""
        place = self.clone_route[self.day]
        cands = companion.daily_candidates(place, self.schedules)
        self.companion_id = companion.pick_companion(
            cands, self.emotion, self.designations.get(self.day)
        )

    def companion(self) -> str | None:
        """오늘의 companion NPC id(그날 1회 결정된 값, 멱등 GET)."""
        return self.companion_id

    def day_schedule(self) -> dict[int, str]:
        """맵 브릿지(T-22)용 8슬롯 스케줄 — 아침 집→낮 여러 장소→저녁 귀가.
        낮을 한 장소로 접으면(구 방식) 하루가 단조롭고 집↔장소 긴 단일 이동이라
        스프라이트가 목표에 못 미쳐 순간이동처럼 튄다 → 오전 다른 곳(a) → 오후
        오늘의 장소(P) → 저녁 다른 곳(c)으로 돌려 이동을 짧게 쪼갠다. **오후(슬롯
        5·6)는 반드시 오늘의 장소 P** — 동행이 거기서 만나므로(_emo_meetings 오후
        밴드). a·c는 P가 아닌 곳에서 날짜 결정론으로 뽑는다(같은 날 재생 가능).
        구 GameRun.schedule과 같은 형태({슬롯:장소})라 좌표 기계가 그대로 소비한다."""
        place = self.clone_route[self.day] if self.day < len(self.clone_route) else "집_차트"
        others = [p for p in _ROUTE_CYCLE if p != place] or [place]
        a = others[self.day % len(others)]
        c = others[(self.day + 2) % len(others)]
        return {1: "집_차트", 2: a, 3: a, 4: place,
                5: place, 6: place, 7: c, 8: "집_차트"}

    # --- 동행 체인 (T-19) ------------------------------------------------- #
    def _maybe_start_chain(self) -> None:
        """companion 확정 직후 체인 발동 판정(문서 §5.1). 선택 있는 단계는
        pending으로, 선택 없는 완성 단계(3)는 보상 즉시 적용."""
        self.pending_chain = None
        npc = self.companion_id
        if not npc or npc not in self.chains:
            return
        stage = chain.maybe_trigger(
            self.seed, self.day, npc, self.chain_progress, self.rapport.get(npc, 0.0)
        )
        if stage is None or stage not in self.chains[npc]:
            return
        event = self.chains[npc][stage]
        if event.get("choices"):
            self.pending_chain = {"npc_id": npc, "stage": stage}
        else:   # 완성 보상(단계3) — 선택 없이 즉시 발동.
            self.emotion = chain.apply_chain_reward(self.emotion, event)
            self.chain_progress[npc] = stage
            self.special_event_count += 1

    def chain_event(self) -> dict | None:
        """오늘 미해결 체인 이벤트(만남 서사+선택지) 또는 None(멱등 GET)."""
        if not self.pending_chain:
            return None
        npc, stage = self.pending_chain["npc_id"], self.pending_chain["stage"]
        return {"npc_id": npc, "stage": stage, **self.chains[npc][stage]}

    def chain_choose(self, choice_id: str) -> None:
        """미해결 체인 선택지 해결 → 4축 델타 + rapport 적용, 단계 완료·카운터++."""
        if not self.pending_chain:
            raise RuntimeError("no pending chain event")
        npc, stage = self.pending_chain["npc_id"], self.pending_chain["stage"]
        event = self.chains[npc][stage]
        chosen = next((c for c in event.get("choices", []) if c["id"] == choice_id), None)
        if chosen is not None:
            self._record_bias(event.get("choices", []), chosen, "chain")
        self.emotion, new_rap = chain.apply_chain_choice(
            self.emotion, self.rapport.get(npc, 0.0), event, choice_id
        )
        self.rapport[npc] = new_rap
        self.chain_progress[npc] = stage
        self.special_event_count += 1
        self.pending_chain = None

    def designate(self, npc_id: str) -> None:
        """전날 밤 개입 — 오늘 대화 상대를 지정(오늘 장소의 후보여야 함)."""
        if self.is_over:
            raise RuntimeError("game is over")
        place = self.clone_route[self.day]
        if npc_id not in companion.daily_candidates(place, self.schedules):
            raise ValueError(f"{npc_id!r} is not a candidate at {place!r}")
        self.designations[self.day] = npc_id
        self._resolve_companion()

    def avoid(self, day_a: int, day_b: int) -> None:
        """전날 밤 개입 — 두 날의 동선(장소)을 맞바꿔 만남을 회피/설계한다."""
        route = {i: p for i, p in enumerate(self.clone_route)}
        route = avoidance.avoid(route, day_a, day_b)
        self.clone_route = [route[i] for i in range(len(self.clone_route))]
        if not self.is_over:
            self._resolve_companion()

    # --- 편향 원장 (T-47c) ----------------------------------------------- #
    def _record_bias(self, all_choices: list, chosen: dict, kind: str) -> None:
        """한 결정점 기록 — 그 자리에 걸린 편향(opportunities: 어느 선택이든 태그된
        축) + 실제로 고른 선택의 편향(hits)을 집계하고 원장에 남긴다. bias_tags
        없는 선택점(대부분의 대화)은 무영향."""
        opp = {t for ch in all_choices for t in ch.get("bias_tags", [])}
        hit = set(chosen.get("bias_tags", []))
        for axis in opp:
            self.bias_tally.setdefault(axis, {"hits": 0, "opportunities": 0})
            self.bias_tally[axis]["opportunities"] += 1
        for axis in hit:
            self.bias_tally.setdefault(axis, {"hits": 0, "opportunities": 0})
            self.bias_tally[axis]["hits"] += 1
        if opp:
            self.choice_history.append({
                "day": self.day, "kind": kind, "choice_id": chosen.get("id"),
                "hits": sorted(hit), "opportunities": sorted(opp),
            })

    def actual_bias(self) -> dict[str, int]:
        """2층 실제 편향(hits/opportunities×100). 표본 n<BIAS_MIN_SAMPLE 축은
        비노출(RETRO 4b — 과소표본 비율 왜곡 방지). 리포트(T-47d)가 소비."""
        out: dict[str, int] = {}
        for axis, t in self.bias_tally.items():
            opp = t.get("opportunities", 0)
            if opp >= BIAS_MIN_SAMPLE:
                out[axis] = round(t.get("hits", 0) / opp * 100)
        return out

    def choose(self, choice_id: str) -> None:
        """하루 결산: 시장 실현(진입 배분) → 감정 델타+스냅샷 → 매매행동으로 배분
        리밸런싱 → 다음 날 진입.

        재산은 행동의 결과다: 오늘 시장 이동은 '어제 정한 배분'만큼 각 카테고리에
        맞고, 오늘 선택의 매매(손절=현금↑, 추격=위험자산↑)는 '다음 날' 이동에
        반영된다. 손절 후 반등을 놓치고, 버티면 반등을 타는 행동적 인과가 생긴다."""
        if self.is_over:
            raise RuntimeError("game is over")
        event_id = self.events[self.day]
        choice = _scenario.get_choice(event_id, choice_id)   # 검증 먼저(변이 전)
        self._record_bias(_scenario.get_scenario(event_id)["choices"], choice, "scenario")

        # 1) 오늘 시장 실현: 진입 시점 보유액에 카테고리별 수익률.
        #    T-35 — 그날 카테고리별 수익률(%)을 기록해 저녁 리포트에서 '오늘의 장'으로.
        self.last_market = {}
        for cat in CATEGORIES:
            series = self.cat_returns.get(cat, [])
            ret = series[self.day] if self.day < len(series) else 0.0
            self.last_market[cat] = round(ret * 100, 2)
            self.holdings[cat] = round(self.holdings.get(cat, 0.0) * (1.0 + ret), 2)

        self.emotion = apply_delta(self.emotion, choice["deltas"])
        self.log = record_snapshot(self.log, self.day, self.emotion)

        # 2) 매매행동 → 배분 리밸런싱(다음 날 이동에 반영).
        self._rebalance(float(choice.get("position", 0.0)))
        self.day += 1
        self._enter_day()

    # --- 캐시아웃 딜레마 (T-30c, #3-A) ----------------------------------- #
    def _risk_share(self) -> float:
        pv = self.portfolio_value
        if pv <= 0:
            return 0.0
        return sum(self.holdings.get(c, 0.0) for c in _RISK) / pv

    def cashout_available(self) -> bool:
        """현금화 딜레마 발동 조건 — 게임당 1회, 중반, 감정 정점 + 위험 비중 있음."""
        if self.cashout_offered or self.is_over or self.day < CASHOUT_MIN_DAY:
            return False
        if self._risk_share() < CASHOUT_RISK_SHARE:
            return False
        return (self.emotion.greed >= CASHOUT_EMOTION_PEAK
                or self.emotion.fear >= CASHOUT_EMOTION_PEAK)

    def cashout_event(self) -> dict | None:
        """딜레마 표시용(순수). 발동 조건 미충족이면 None. 탐욕/공포 정점에 따라 문구."""
        if not self.cashout_available():
            return None
        gain = self.emotion.greed >= self.emotion.fear   # 탐욕 주도 vs 공포 주도
        text = (
            "탐욕이 머리끝까지 찼다. 지금 현금으로 확정하고 빠질까, 더 태울까?"
            if gain else
            "불안이 목까지 차올랐다. 지금이라도 현금으로 빼서 지킬까, 버틸까?"
        )
        return {
            "title": "현금화할까, 계속 갈까",
            "text": text,
            "gain": gain,
            "choices": [
                {"id": "cash_out", "label": "현금으로 뺀다"},
                {"id": "stay", "label": "계속 안고 간다"},
            ],
        }

    # 현금화=안심(위축 완화)이지만 반등 기회 상실(탐욕↓). 유지=계속 노출(탐욕·불안↑).
    _CASHOUT_DELTAS = {
        "cash_out": {"fear": -6, "anxiety": -6, "greed": -4, "restlessness": -4, "composure": 5},
        "stay": {"greed": 5, "anxiety": 5, "restlessness": 3, "composure": -3},
    }

    def cashout(self, choice_id: str) -> None:
        """딜레마 선택 적용(감정 + 현금화 리밸런싱). 날짜는 안 넘어간다(하루 중 성찰)."""
        if not self.cashout_available():
            raise RuntimeError("cashout dilemma not available")
        if choice_id not in self._CASHOUT_DELTAS:
            raise ValueError(f"unknown cashout choice {choice_id!r}")
        self.emotion = apply_delta(self.emotion, self._CASHOUT_DELTAS[choice_id])
        if choice_id == "cash_out":
            self._rebalance(-_CASHOUT_FRAC)   # 위험자산 → 현금
        self.cashout_offered = True

    # --- 종료 ------------------------------------------------------------- #
    def ending_inputs(self) -> dict:
        """엔딩 분기 입력(T-13): 감정 압축판정 + 재산 수준 + 특수이벤트 누적."""
        return {
            "verdict": compute_verdict(self.emotion),
            "wealth_level": "high" if self.portfolio_value >= START_VALUE else "low",
            "portfolio_value": self.portfolio_value,
            "special_count": self.special_event_count,
            "composure": self.emotion.composure,   # T-37 — 평정(자기통제)
        }

    def ending(self) -> dict:
        """최종 엔딩(E1~E5 + 등급 + 에필로그). 문서 §4."""
        ei = self.ending_inputs()
        return _ending.decide_ending(
            ei["verdict"], ei["wealth_level"], ei["special_count"], ei["composure"]
        )

    # --- 직렬화 (T-14 영속화가 소비) ------------------------------------- #
    def to_doc(self) -> dict:
        return {
            "emotion": {
                "fear": self.emotion.fear, "greed": self.emotion.greed,
                "anxiety": self.emotion.anxiety, "restlessness": self.emotion.restlessness,
                "composure": self.emotion.composure,
            },
            "events": self.events,
            "cat_returns": self.cat_returns,
            "seed": self.seed,
            "day": self.day,
            "clone_name": self.clone_name,
            "holdings": self.holdings,
            "portfolio_value": self.portfolio_value,   # 파생(외부 리더 편의)
            "clone_route": self.clone_route,
            "designations": {str(k): v for k, v in self.designations.items()},
            "companion_id": self.companion_id,
            "special_event_count": self.special_event_count,
            "chain_progress": self.chain_progress,
            "rapport": self.rapport,
            "pending_chain": self.pending_chain,
            "cashout_offered": self.cashout_offered,
            "last_market": self.last_market,
            "disposition": self.disposition,       # T-47c — str키 dict(BSON 안전)
            "choice_history": self.choice_history,
            "bias_tally": self.bias_tally,
            "report_narrative": self.report_narrative,   # T-47f — 캐시된 리포트 서술

            "log": [
                {"turn": s.turn, "emotion": {
                    "fear": s.state.fear, "greed": s.state.greed,
                    "anxiety": s.state.anxiety, "restlessness": s.state.restlessness,
                    "composure": s.state.composure,
                }}
                for s in self.log.snapshots
            ],
        }

    @classmethod
    def from_doc(cls, doc: dict) -> "EmoGameRun":
        """복원 — 이미 진입한 날의 노출은 재적용하지 않는다(_enter_day 호출 안 함)."""
        from .player_emotion.log import EmotionSnapshot

        snaps = tuple(
            EmotionSnapshot(turn=s["turn"], state=PlayerEmotionState(**s["emotion"]))
            for s in doc.get("log", [])
        )
        n = len(doc["events"])
        # 재산 복원(하위호환): 신 doc는 holdings/cat_returns, 구 doc는 파생.
        holdings = doc.get("holdings")
        if not holdings:
            pv = doc.get("portfolio_value", START_VALUE)
            holdings = {c: round(pv / len(CATEGORIES), 2) for c in CATEGORIES}
        cat_returns = doc.get("cat_returns")
        if cat_returns is None:
            old = doc.get("returns") or []
            cat_returns = {c: list(old) for c in CATEGORIES}
        return cls(
            emotion=PlayerEmotionState(**doc["emotion"]),
            events=list(doc["events"]),
            cat_returns={c: list(cat_returns.get(c, [])) for c in CATEGORIES},
            seed=doc["seed"],
            day=doc["day"],
            clone_name=_clean_name(doc.get("clone_name")),   # 구 doc은 기본값
            holdings={c: float(holdings.get(c, 0.0)) for c in PORTFOLIO_CATEGORIES},
            log=EmotionLog(snapshots=snaps),
            clone_route=list(doc.get("clone_route") or _default_route(n)),
            designations={int(k): v for k, v in (doc.get("designations") or {}).items()},
            companion_id=doc.get("companion_id"),
            special_event_count=doc.get("special_event_count", 0),
            chain_progress={k: int(v) for k, v in (doc.get("chain_progress") or {}).items()},
            rapport={k: float(v) for k, v in (doc.get("rapport") or {}).items()},
            pending_chain=doc.get("pending_chain"),
            cashout_offered=bool(doc.get("cashout_offered", False)),
            last_market={k: float(v) for k, v in (doc.get("last_market") or {}).items()},
            disposition=doc.get("disposition"),   # T-47c — 구 doc엔 없음(None)
            choice_history=list(doc.get("choice_history") or []),
            bias_tally={k: dict(v) for k, v in (doc.get("bias_tally") or {}).items()},
            report_narrative=doc.get("report_narrative"),   # T-47f
        )
