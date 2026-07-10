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
from . import coins as _coins
from . import ending as _ending
from . import place_effects as _place_effects
from . import scenario as _scenario
from . import story_texts as _story_texts
from .disposition import BIAS_AXES, build_initial_emotion_v2, diagnose
from .fate_line import CATEGORIES
from .personas import TRADER_PERSONAS, npc_scheds
from .player_emotion.deltas import apply_delta, consume_axis, decay_toward_equilibrium
from .player_emotion.log import EmotionLog, record_snapshot
from .player_emotion.state import PlayerEmotionState, get_axis
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

# T-52 (F4): 게시판 감정-소모 매매의 규모 계수. 매매액 = 감정 level 비례(level 100
# → 지갑의 이 비율까지). 충동 크기(감정)가 곧 행동 크기 → 자기 편향이 눈에 보인다
# (거울 강화, 4b). 🤖 council(2026-07-10, 3렌즈 만장일치): 모델 A 유지·계수만 1.0→0.6
# — 1.0은 탐욕 100에서 현금 100% 몰빵→다음 매수 불가 하자. 0.6이면 최대 60%로 드라마틱하되
# 판을 안 끝내고 거울도 살아있음. 잠정 튜닝 밴드 0.5~0.7(플레이테스트 확정).
TRADE_INTENSITY = 0.6

# T-50d — 장소 딜레마(disp 처분효과 결정점): 도서관=익절 복기, 마켓=현실소비 유혹.
# '이익을 너무 일찍 실현'(익절/소비) 선택 = disp 태깅 → 리포트에서 처분효과 측정
# (T-48e 흡수 — 반복 결정점이 생겨 disp가 리포트에서 살아난다). 그 장소에 도착하면
# 발동(연출 문맥). 감정 델타는 소폭(성찰), 날짜는 안 넘어간다.
_PLACE_DILEMMAS: dict[str, dict] = {
    "도서관": {
        "place": "도서관", "title": "복기",
        "text": "지난 수익 종목의 차트를 다시 연다. 그때 팔았으면… 지금이라도 익절할까, 원래 계획대로 더 지켜볼까?",
        "choices": [
            {"id": "take_profit", "label": "지금 익절한다", "bias_tags": ["disp"],
             "deltas": {"greed": -3, "anxiety": -3, "composure": 3}},
            {"id": "hold_plan", "label": "계획대로 더 본다",
             "deltas": {"composure": 4, "restlessness": -2}},
        ],
    },
    "마켓": {
        "place": "마켓", "title": "장보기",
        "text": "수익이 조금 났다. 진열대의 갖고 싶던 물건이 눈에 밟힌다. 수익 일부를 빼서 지금 살까, 계좌에 그대로 둘까?",
        "choices": [
            {"id": "spend", "label": "수익 빼서 산다", "bias_tags": ["disp"],
             "deltas": {"greed": -2, "restlessness": -3, "composure": 2}},
            {"id": "keep", "label": "그대로 둔다",
             "deltas": {"composure": 3, "greed": 1}},
        ],
    },
}


# v3 §C1 — 원인 카드(attribution) 정적 텍스트 4종. "방어/공격" = 어제 선택의
# position 부호(방어 = position<0 = 위험자산↓, 공격 = position>0 = 위험자산↑),
# "성공/손해" = 오늘 actual_pnl_pct가 counterfactual_pnl_pct보다 나았는지(delta>=0).
# {label}=어제 선택 라벨, {cf}=반사실 낙폭(양수로 표시), {actual}=실제 낙폭/상승폭.
_ATTRIBUTION_TEMPLATES = {
    ("defense", True): "어제 「{label}」로 리스크를 줄인 덕분에 −{cf}% 대신 −{actual}%에 그쳤다.",
    ("defense", False): "어제 「{label}」로 리스크를 줄였지만, 오늘은 오히려 +{cf}% 반등 대신 {actual}%에 머물렀다.",
    ("aggressive", True): "어제 「{label}」로 더 태운 덕분에 +{cf}% 대신 +{actual}%를 얻었다.",
    ("aggressive", False): "어제 「{label}」로 더 태웠지만, 오늘은 −{cf}% 대신 −{actual}%로 더 물렸다.",
}


def _attribution_bucket(position: float) -> str:
    """어제 선택의 방향 버킷 — attribution 텍스트 선택용(scenario._bucket_of와
    유사하나 관망(position≈0)은 방어 쪽에 붙여 4종 템플릿에 맞춘다)."""
    return "aggressive" if position > 0 else "defense"


def _attribution_text(bucket: str, success: bool, label: str,
                       actual_pct: float, counterfactual_pct: float) -> str:
    """§C1 — 방어성공/방어손해/공격성공/공격손해 4종 정적 템플릿 렌더링(I5: 고정
    문구, LLM 아님). 퍼센트는 부호를 문구가 이미 표현하므로 절대값으로 채운다."""
    template = _ATTRIBUTION_TEMPLATES[(bucket, success)]
    return template.format(
        label=label, cf=abs(round(counterfactual_pct, 2)), actual=abs(round(actual_pct, 2)),
    )


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
# T-50b — 마켓·도서관 편입(맵 주소 有, 정호=도서관·미나=마켓 배치). 5→7곳.
_ROUTE_CYCLE = ("카페", "광장", "펍", "일터", "운동", "마켓", "도서관")


def _day_rng(seed: int, day: int) -> random.Random:
    """(seed, day)로 결정론 rng — 같은 날은 항상 같은 게시판(재생 가능)."""
    return random.Random(seed * 1000 + day)


def _default_route(n: int, seed: int = 0) -> list[str]:
    """일수만큼 기본 동선(장소 순환). T-50a — 회차(seed)마다 순서를 셔플해 재플레이
    변화·순서효과 통제(같은 seed는 결정론 재생). 플레이어가 avoid로 재배치할 수 있다."""
    cycle = list(_ROUTE_CYCLE)
    random.Random(seed).shuffle(cycle)
    return [cycle[i % len(cycle)] for i in range(n)]


def _emotion_to_dict(e: PlayerEmotionState) -> dict[str, float]:
    """§5.1 settlement 직렬화용 — 감정 상태를 5축 dict로."""
    return {"fear": e.fear, "greed": e.greed, "anxiety": e.anxiety,
            "restlessness": e.restlessness, "composure": e.composure}


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
    place_dilemmas_done: list[str] = field(default_factory=list)   # T-50d — 처리한 "{day}:{place}"(멱등)
    last_market: dict[str, float] = field(default_factory=dict)   # T-35 — 마지막 정산일 카테고리별 수익률(%)
    # T-47c — 1층 정적 성향 진단(시작 시 diagnose, 플레이 중 불변) + 2층 실제 행동
    # 편향 원장/집계. bias_tally[axis] = {"hits","opportunities"} → actual_bias 비율식.
    disposition: dict | None = None
    choice_history: list[dict] = field(default_factory=list)
    bias_tally: dict[str, dict[str, int]] = field(default_factory=dict)
    # T-47f — 엔딩 리포트 서술(LLM or 결정론). 게임당 1회 생성 후 캐시(과금 상한·멱등).
    report_narrative: list[str] | None = None
    # §2.2 — 오늘의 일과 편성(플랜). {"오전":장소,"오후":장소,"저녁":장소} or None(미제출).
    day_plan: dict[str, str] | None = None
    plan_locked_day: int | None = None   # 플랜을 잠근 날짜(하루 1회 제출 가드, I4)
    last_settlement: dict | None = None   # §5.1 — 마지막 choose() 정산 캐스케이드(1회성, state에 유지)
    # v3 §C1 — 원인 카드(attribution): "어제 리밸런스 안 했으면" 반사실 보유액.
    # choose()가 정산 직후·리밸런스 직전(오늘 시장 실현 반영, 오늘 선택의 매매는
    # 미반영)의 보유액 스냅샷을 저장해두면, 다음날 choose()가 그 스냅샷에 그날
    # 수익률을 적용해 "리밸런스 안 했을 경우"의 pnl을 계산할 수 있다.
    counterfactual_holdings: dict[str, float] | None = None
    counterfactual_choice_label: str | None = None   # 반사실의 원인이 된 어제 선택 라벨
    counterfactual_choice_position: float = 0.0   # 그 선택의 position(방어/공격 버킷 판정용)

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
            clone_route=_default_route(len(events), seed),   # T-50a — 회차별 셔플
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

    # --- per-코인 지정 매매 (T-52, F4) ----------------------------------- #
    def _board_trade_size(self, level: float, wallet: float) -> float:
        """감정 비례 매매 규모 — 감정 level(0~100)에 비례해 wallet의 일부.
        level 100 → wallet×TRADE_INTENSITY, level 20 → 그 1/5(찔끔). [0,1] 클램프."""
        frac = max(0.0, min(1.0, level / 100.0 * TRADE_INTENSITY))
        return round(wallet * frac, 2)

    def _buy_coin(self, cat: str, amount: float) -> float:
        """현금 → cat 코인 1개 매수(가용 현금 한도). 실제 이동액 반환. _rebalance의
        버킷 자동배분과 달리 지정 코인 1개에만 태운다(F4 3액션)."""
        cash = self.holdings.get(CASH, 0.0)
        moved = round(min(max(0.0, amount), cash), 2)
        if moved <= 0.0:
            return 0.0
        self.holdings[CASH] = round(cash - moved, 2)
        self.holdings[cat] = round(self.holdings.get(cat, 0.0) + moved, 2)
        return moved

    def _sell_coin(self, cat: str, amount: float) -> float:
        """cat 코인 1개 → 현금 매도(보유 한도). 실제 이동액 반환. 보유 없으면 무매매."""
        held = self.holdings.get(cat, 0.0)
        moved = round(min(max(0.0, amount), held), 2)
        if moved <= 0.0:
            return 0.0
        self.holdings[cat] = round(held - moved, 2)
        self.holdings[CASH] = round(self.holdings.get(CASH, 0.0) + moved, 2)
        return moved

    # --- 상태 조회 -------------------------------------------------------- #
    @property
    def is_over(self) -> bool:
        return self.day >= len(self.events)

    @property
    def emotion_log(self) -> EmotionLog:
        return self.log

    def _biggest_move_symbol(self) -> str | None:
        """§B — 오늘(self.day) |변동률| 최대인 카테고리의 실명 심볼(결정론).
        동률이면 CATEGORIES 순서상 먼저 나오는 쪽(안정적 tie-break). 데이터
        없으면 None."""
        best_cat: str | None = None
        best_abs = -1.0
        for cat in CATEGORIES:
            series = self.cat_returns.get(cat, [])
            if self.day >= len(series):
                continue
            move = abs(series[self.day])
            if move > best_abs:
                best_abs = move
                best_cat = cat
        if best_cat is None:
            return None
        return _coins.coin_for_category(best_cat)["symbol"] or None

    def board(self) -> dict:
        """현재 날의 게시판(표시용, 멱등). 감정/상태를 변이하지 않는다.

        §4.2 — scenario.choices는 6개 풀에서 (seed, day, event_id)로 결정론
        추첨한 3개(방어/관망/공격 1개씩)만 노출한다(I2/I4).
        §B — scenario.text의 {coin} 플레이스홀더는 오늘 |변동률| 최대
        카테고리의 실명 심볼로 치환된다(I1 불변 — cat_returns는 읽기만 함)."""
        if self.is_over:
            raise RuntimeError("game is over")
        return board_exposure.render_board(
            self.events[self.day], _day_rng(self.seed, self.day),
            seed=self.seed, day=self.day,
            coin_symbol=self._biggest_move_symbol(),
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
        구 GameRun.schedule과 같은 형태({슬롯:장소})라 좌표 기계가 그대로 소비한다.

        §2.2 — 오늘 플랜이 잠겨 있으면(day_plan/plan_locked_day==day) 오전(슬롯2)·
        저녁(슬롯7)을 플랜의 장소로 교체한다. 점심(슬롯4=게시판 강제노출)·오후(슬롯
        5·6=동행 만남)는 플랜과 무관하게 불변(I6 — 기존 동행·게시판 로직 보호)."""
        place = self.clone_route[self.day] if self.day < len(self.clone_route) else "집_차트"
        others = [p for p in _ROUTE_CYCLE if p != place] or [place]
        a = others[self.day % len(others)]
        c = others[(self.day + 2) % len(others)]
        # T-50c — 낮 방문 3~4곳 가변(짝수날=4: 오전에 b 한 곳 더, 홀수날=3). 오후(5·6)=P 불변.
        b = others[(self.day + 4) % len(others)] if self.day % 2 == 0 else a
        if self.day_plan is not None and self.plan_locked_day == self.day:
            a = self.day_plan.get("오전", a)
            c = self.day_plan.get("저녁", c)
        return {1: "집_차트", 2: a, 3: b, 4: place,
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

    def choose(self, choice_id: str, coin_target: str | None = None) -> None:
        """하루 결산(T-53, F4): 시장 실현(진입 배분) → 감정 소모(매수=탐욕/매도=공포/
        유지=평정) → 플랜 장소 효과 → 밤 감쇠 → per-코인 매매(다음 날 노출 반영) →
        다음 날 진입.

        재산은 행동의 결과다: 오늘 시장 이동은 '어제 정한 배분'만큼 각 카테고리에
        맞고, 오늘 선택의 매매(매수=현금→지정코인, 매도=지정코인→현금)는 '다음 날'
        이동에 반영된다. 매매 규모는 소모 전 감정 level에 비례(충동 크기=행동 크기).
        coin_target은 매수/매도에 필수(CATEGORIES 중 1), 유지는 무매매(무시).

        §5.1 — last_settlement에 「선택 → 수익률 → 감정」 캐스케이드를 기록한다.
        I1: market/portfolio는 오늘의 선택과 무관(cat_returns 그대로) — 선택은
        매매(다음 날 노출)에만 반영된다.

        노출-풀 검증(노출 안 된 id로 choose 시 400)은 HTTP 레이어(emo_api.choose)에서
        board()의 오늘자 3액션 노출과 비교해 수행한다."""
        if self.is_over:
            raise RuntimeError("game is over")
        event_id = self.events[self.day]
        choice = _scenario.get_choice(event_id, choice_id)   # 검증 먼저(변이 전, 3액션 풀)
        action = choice.get("action")
        if action in ("buy", "sell") and coin_target not in CATEGORIES:
            raise ValueError(
                f"action {action!r} requires coin_target in CATEGORIES, got {coin_target!r}")
        self._record_bias(_scenario.get_scenario(event_id)["choices"], choice, "scenario")

        day_for_settlement = self.day
        emotion_before = self.emotion

        # 1) 오늘 시장 실현: 진입 시점 보유액에 카테고리별 수익률(I1 — cat_returns 불가침).
        #    T-35 — 그날 카테고리별 수익률(%)을 기록해 저녁 리포트에서 '오늘의 장'으로.
        self.last_market = {}
        portfolio_before = self.portfolio_value
        market_steps = []
        for cat in CATEGORIES:
            series = self.cat_returns.get(cat, [])
            ret = series[self.day] if self.day < len(series) else 0.0
            self.last_market[cat] = round(ret * 100, 2)
            before = self.holdings.get(cat, 0.0)
            after = round(before * (1.0 + ret), 2)
            self.holdings[cat] = after
            market_steps.append({
                "category": cat, "pct": round(ret * 100, 2),
                "before": before, "after": after,
            })
        portfolio_after_market = self.portfolio_value

        # v3 §C1 — 원인 카드(attribution): 어제 저장해둔 counterfactual_holdings
        # (어제 정산 직후·리밸런스 전 보유액)에 **오늘** 수익률을 적용하면 "어제
        # 리밸런스를 안 했을 경우"의 오늘 성과가 나온다. day 0은 어제가 없으므로
        # 생략(스펙). 값을 쓰고 나서 바로 오늘의 스냅샷으로 덮어써 다음날에 대비한다.
        attribution: dict | None = None
        if day_for_settlement > 0 and self.counterfactual_holdings is not None:
            cf_before = sum(self.counterfactual_holdings.values())
            cf_after = 0.0
            for cat in CATEGORIES:
                series = self.cat_returns.get(cat, [])
                ret = series[self.day] if self.day < len(series) else 0.0
                cf_after += self.counterfactual_holdings.get(cat, 0.0) * (1.0 + ret)
            cf_after += self.counterfactual_holdings.get(CASH, 0.0)   # 현금은 수익률 0
            actual_pnl_pct = (
                round((portfolio_after_market - portfolio_before) / portfolio_before * 100, 2)
                if portfolio_before else 0.0
            )
            counterfactual_pnl_pct = (
                round((cf_after - cf_before) / cf_before * 100, 2) if cf_before else 0.0
            )
            delta_pct = round(actual_pnl_pct - counterfactual_pnl_pct, 2)
            bucket = _attribution_bucket(self.counterfactual_choice_position)
            success = delta_pct >= 0
            attribution = {
                "actual_pnl_pct": actual_pnl_pct,
                "counterfactual_pnl_pct": counterfactual_pnl_pct,
                "delta_pct": delta_pct,
                "cause_choice_label": self.counterfactual_choice_label,
                "text": _attribution_text(
                    bucket, success, self.counterfactual_choice_label or "",
                    actual_pnl_pct, counterfactual_pnl_pct,
                ),
            }

        # 오늘 정산 직후(리밸런스 전) 보유액 스냅샷 — 내일 attribution의 반사실
        # 기준(오늘 리밸런스를 안 했을 경우)이 된다. cash 포함 전체 카테고리.
        self.counterfactual_holdings = dict(self.holdings)
        self.counterfactual_choice_label = choice["label"]
        self.counterfactual_choice_position = float(choice.get("position", 0.0))

        # 2) 감정 캐스케이드: 선택 → (플랜 장소) → (체인은 낮에 이미 반영됨) → 밤 감쇠.
        # 각 step의 deltas는 '실제 상태 변화량'(클램프 반영 후 차분)이라 클램핑으로
        # 잘려도 emotion_before + Σsteps == emotion_after가 정확히 성립한다(스펙 §5.1).
        emotion_steps: list[dict] = []

        def _push_step(source: str, label: str, prev: PlayerEmotionState,
                        nxt: PlayerEmotionState, extra: dict | None = None) -> None:
            actual = {
                axis: round(getattr(nxt, axis) - getattr(prev, axis), 4)
                for axis in ("fear", "greed", "anxiety", "restlessness", "composure")
            }
            if any(v != 0 for v in actual.values()):
                step = {"source": source, "label": label, "deltas": actual}
                if extra:
                    step.update(extra)
                emotion_steps.append(step)

        state = emotion_before
        # T-53: 선택 = 감정 소모(매수=탐욕/매도=공포/유지=평정). 소모 전 level은
        # 매매 규모(감정 비례)에 쓰고, 소모 자체가 '선택의 여파' step이 된다.
        consume_axis_name = choice["consume_axis"]
        level_before = get_axis(state, consume_axis_name)
        next_state, consumed = consume_axis(state, consume_axis_name, float(choice["consume_fraction"]))
        _push_step("choice", "선택의 여파", state, next_state)
        state = next_state

        if self.day_plan is not None and self.plan_locked_day == self.day:
            for band in _place_effects.PLAN_BANDS:
                place = self.day_plan.get(band)
                if place is None:
                    continue
                # v4 §1.2 — I3: GET /plan이 보여준 것과 같은 함수(activity_for)로
                # 그날의 활동을 재도출해 적용한다(activity_id/activity_name도
                # step에 실어 프론트가 라벨을 그대로 재사용할 수 있게 한다).
                activity = _place_effects.activity_for(self.seed, day_for_settlement, band, place)
                next_state = apply_delta(state, activity["deltas"])
                _push_step(
                    "place", f"「{activity['name']}」 후", state, next_state,
                    {"place": place, "activity_id": activity["id"],
                     "activity_name": activity["name"]},
                )
                state = next_state

        self.emotion = state
        self.log = record_snapshot(self.log, self.day, self.emotion)

        risk_share_before = self._risk_share()
        # 3) 매매행동(T-53): 코인 1개 지정 매수/매도, 규모=소모 전 감정 level 비례.
        #    유지=무매매(평정만 소모). I1 — 오늘의 선택은 '내일의 노출'에만 영향.
        traded = 0.0
        if action == "buy":
            traded = self._buy_coin(
                coin_target, self._board_trade_size(level_before, self.holdings.get(CASH, 0.0)))
        elif action == "sell":
            traded = self._sell_coin(
                coin_target, self._board_trade_size(level_before, self.holdings.get(coin_target, 0.0)))
        risk_share_after = self._risk_share()

        state_before_decay = self.emotion
        self.day += 1
        self._enter_day()   # is_over가 아니면 내부에서 decay_toward_equilibrium 적용
        _push_step("decay", "하루가 저물며", state_before_decay, self.emotion)
        emotion_after = self.emotion

        self.last_settlement = {
            "day": day_for_settlement,
            "choice": {"id": choice["id"], "label": choice["label"],
                       "position": float(choice.get("position", 0.0)),
                       "action": action, "consume_axis": consume_axis_name,
                       "consumed": round(consumed, 2), "coin_target": coin_target,
                       "traded": traded},
            "market": market_steps,
            "portfolio": {
                "before": portfolio_before, "after": portfolio_after_market,
                "pnl_pct": (round((portfolio_after_market - portfolio_before) / portfolio_before * 100, 2)
                            if portfolio_before else 0.0),
            },
            "rebalance": {
                "risk_share_before": round(risk_share_before, 4),
                "risk_share_after": round(risk_share_after, 4),
            },
            "emotion_steps": emotion_steps,
            "emotion_before": _emotion_to_dict(emotion_before),
            "emotion_after": _emotion_to_dict(emotion_after),
            "attribution": attribution,   # v3 §C1 — day 0은 None(어제가 없음)
        }

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

    # --- 시세 현황판 (§B) --------------------------------------------------- #
    def ticker(self) -> list[dict]:
        """§B — 카테고리별 실시간 시세 현황판(헤더 티커/포트폴리오 드로어).

        index는 시작(=100) 기준 누적곱(I1 — 운명선 cat_returns 그대로, 손대지
        않는다). **이미 정산된(choose()가 실현한) 날까지만** 반영한다 — 실현된
        날은 0..self.day-1(choose()가 cat_returns[self.day]를 실현한 뒤
        self.day를 ++하는 순서라, 아직 정산 전인 self.day 당일은 포함하지
        않는다: 미래 누출 금지). 하루도 정산되지 않았으면(day 0, 첫 정산 전)
        index=100·day_pct=0. day_pct는 마지막으로 정산된 날의 단일일 변동률."""
        settled = self.day   # 정산 완료된 날 수 = 0..settled-1
        out: list[dict] = []
        for cat in CATEGORIES:
            series = self.cat_returns.get(cat, [])
            index = 100.0
            day_pct = 0.0
            n = min(settled, len(series))
            for d in range(n):
                index *= (1.0 + series[d])
            if n > 0:
                day_pct = round(series[n - 1] * 100, 2)
            coin = _coins.coin_for_category(cat)
            out.append({
                "category": cat,
                "symbol": coin["symbol"],
                "name": coin["name"],
                "day_pct": day_pct,
                "index": round(index, 4),
            })
        return out

    # --- 장소 딜레마 (T-50d) — disp 결정점 ------------------------------- #
    def band_places(self) -> dict[str, str]:
        """오늘 시간대(밴드)별 대표 장소 — 프론트가 '그 장소 도착' 시 장소 딜레마를
        띄우게. 밴드=day_schedule 8슬롯 묶음(오전1·2/점심3·4/오후5·6/저녁7·8).
        대표=각 밴드의 낮 장소(오전2·점심4·오후5·저녁7). 점심(게시판)·오후(동행)와
        겹치지 않게 장소 딜레마는 오전·저녁만 소비한다(프론트 규칙)."""
        s = self.day_schedule()
        return {"오전": s[2], "점심": s[4], "오후": s[5], "저녁": s[7]}

    def place_dilemma(self, place: str) -> dict | None:
        """그날 그 장소에서 발동하는 disp 딜레마(도서관/마켓). 오늘 동선에 그 장소가
        없거나 미정의 장소면 None. 순수 GET(멱등, 상태 불변) — 표시용."""
        if self.is_over:
            return None
        d = _PLACE_DILEMMAS.get(place)
        if d is None or place not in self.day_schedule().values():
            return None
        return d

    def resolve_place_dilemma(self, place: str, choice_id: str) -> None:
        """장소 딜레마 선택 적용(감정 델타 + disp 원장 적립). 날짜는 안 넘어간다.
        같은 (day, place)는 멱등 — 이미 처리했으면 무시(리로드 재요청 이중적용 방지, 4c)."""
        d = _PLACE_DILEMMAS.get(place)
        if d is None or place not in self.day_schedule().values():
            raise RuntimeError(f"no place dilemma at {place!r} today")
        chosen = next((c for c in d["choices"] if c["id"] == choice_id), None)
        if chosen is None:
            raise ValueError(f"unknown place dilemma choice {choice_id!r}")
        key = f"{self.day}:{place}"
        if key in self.place_dilemmas_done:
            return   # 멱등 — 이미 처리
        self._record_bias(d["choices"], chosen, "place")   # disp 적립
        self.emotion = apply_delta(self.emotion, chosen.get("deltas", {}))
        self.place_dilemmas_done.append(key)

    # --- 일과 편성 플랜 (§2.2) --------------------------------------------- #
    def plan_locked(self) -> bool:
        """오늘 플랜이 이미 제출·잠겼는지(I4 — 하루 1회 제출 가드)."""
        return self.day_plan is not None and self.plan_locked_day == self.day

    def _plan_band_npcs(self, band: str, place: str) -> list[dict]:
        """그 밴드가 커버하는 슬롯(오전→슬롯2, 오후→슬롯5·6, 저녁→슬롯7)에 그
        장소 일정이 있는 personas.py NPC 목록(npc_id/name/portrait)."""
        slots = {"오전": (2,), "오후": (5, 6), "저녁": (7,)}.get(band, ())
        out: list[dict] = []
        seen: set[str] = set()
        for p in TRADER_PERSONAS:
            sched = p.get("sched", {})
            if any(sched.get(s) == place for s in slots) and p["id"] not in seen:
                seen.add(p["id"])
                out.append({"npc_id": p["id"], "name": p["name"], "portrait": p["portrait"]})
        return out

    def plan_preview(self) -> dict:
        """GET /plan 응답 본문(순수·멱등, I4) — 스펙 §2.2."""
        board = self.board() if not self.is_over else None
        fixed_label = board["scenario"]["text"] if board else ""
        current_plan = dict(self.day_plan) if self.plan_locked() else None
        bands = []
        for band in _place_effects.PLAN_BANDS:
            options = []
            for place in _place_effects.PLAN_PLACES:
                npcs = self._plan_band_npcs(band, place)
                npc_ids = [n["npc_id"] for n in npcs]
                # v4 §1.2 — 오늘의 활동(activity_for)이 cost/forecast의 유일한
                # 소스(I3): 밤 정산(choose)이 같은 함수로 같은 활동을 재도출한다.
                activity = _place_effects.activity_for(self.seed, self.day, band, place)
                options.append({
                    "place": place,
                    "activity_id": activity["id"],
                    "activity_name": activity["name"],
                    "cost": activity["cost"],
                    "forecast": dict(activity["deltas"]),
                    "npcs": npcs,
                    "badges": _place_effects.place_badges(place, npcs),
                    # §2(v2) — NPC-aware 플레이버: 밴드에 NPC가 있으면
                    # PLACE_NPC_FLAVOR[(place, npc_id 정렬 첫번째)] 우선, 없으면
                    # PLACE_FLAVOR[place] 폴백(story_texts.place_flavor).
                    "flavor": _story_texts.place_flavor(place, npc_ids),
                })
            bands.append({"band": band, "options": options})
        return {
            "day": self.day,
            "budget": _place_effects.PLAN_BUDGET,
            "locked": self.plan_locked(),
            "current_plan": current_plan,
            "fixed": {"점심": {"kind": "board", "label": "단톡방 확인", "text": fixed_label}},
            "bands": bands,
            # §1(v2/v3) — 아침 내레이션(데이 프레임). total_days를 넘겨 마지막
            # 날·전야를 항상 그 자리에 고정한다(v3 §A). 그 외 날은 나머지
            # 프레임을 앞에서부터 순환.
            "morning": {"day": self.day, "text": _story_texts.day_frame(self.day, len(self.events))},
        }

    def submit_plan(self, plan: dict[str, str]) -> None:
        """POST /plan — 플랜 검증·잠금·오늘 band_places(day_schedule) 반영.

        검증 실패는 ValueError(→ 400), 이미 잠겼거나 게임 종료면 RuntimeError
        (→ 409)."""
        if self.is_over:
            raise RuntimeError("game is over")
        if self.plan_locked():
            raise RuntimeError("plan already submitted for today")
        # v4 §1.2 — I3: 오늘의 활동 비용(같은 seed/day로 GET /plan이 보여준 것과
        # 동일 소스)으로 예산을 검증한다.
        _place_effects.validate_plan(plan, seed=self.seed, day=self.day)   # ValueError → 400(호출자)
        self.day_plan = {b: plan[b] for b in _place_effects.PLAN_BANDS}
        self.plan_locked_day = self.day
        self._resolve_companion()   # a/c 변경은 companion에 영향 없음(오후=P 불변)이지만 명시적으로 재확정

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
            "place_dilemmas_done": list(self.place_dilemmas_done),   # T-50d
            "last_market": self.last_market,
            "disposition": self.disposition,       # T-47c — str키 dict(BSON 안전)
            "choice_history": self.choice_history,
            "bias_tally": self.bias_tally,
            "report_narrative": self.report_narrative,   # T-47f — 캐시된 리포트 서술
            "day_plan": self.day_plan,                    # §2.2
            "plan_locked_day": self.plan_locked_day,      # §2.2
            "last_settlement": self.last_settlement,      # §5.1
            "counterfactual_holdings": self.counterfactual_holdings,   # v3 §C1
            "counterfactual_choice_label": self.counterfactual_choice_label,   # v3 §C1
            "counterfactual_choice_position": self.counterfactual_choice_position,   # v3 §C1

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
            clone_route=list(doc.get("clone_route") or _default_route(n, doc.get("seed", 0))),
            designations={int(k): v for k, v in (doc.get("designations") or {}).items()},
            companion_id=doc.get("companion_id"),
            special_event_count=doc.get("special_event_count", 0),
            chain_progress={k: int(v) for k, v in (doc.get("chain_progress") or {}).items()},
            rapport={k: float(v) for k, v in (doc.get("rapport") or {}).items()},
            pending_chain=doc.get("pending_chain"),
            cashout_offered=bool(doc.get("cashout_offered", False)),
            place_dilemmas_done=list(doc.get("place_dilemmas_done") or []),   # T-50d
            last_market={k: float(v) for k, v in (doc.get("last_market") or {}).items()},
            disposition=doc.get("disposition"),   # T-47c — 구 doc엔 없음(None)
            choice_history=list(doc.get("choice_history") or []),
            bias_tally={k: dict(v) for k, v in (doc.get("bias_tally") or {}).items()},
            report_narrative=doc.get("report_narrative"),   # T-47f
            day_plan=doc.get("day_plan"),                    # §2.2 — 구 doc엔 없음(None)
            plan_locked_day=doc.get("plan_locked_day"),       # §2.2
            last_settlement=doc.get("last_settlement"),       # §5.1
            counterfactual_holdings=doc.get("counterfactual_holdings"),   # v3 §C1 — 구 doc엔 없음(None)
            counterfactual_choice_label=doc.get("counterfactual_choice_label"),   # v3 §C1
            counterfactual_choice_position=float(doc.get("counterfactual_choice_position", 0.0)),   # v3 §C1
        )
