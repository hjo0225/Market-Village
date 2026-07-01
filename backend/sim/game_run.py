"""§12.4 step-able GameRun — 신 엔진 정본의 하루씩 플레이 세션 (D-E).

run_loop은 30일을 batch로 돈다. 플레이어는 하루씩 진행(전날밤→아침→위기→정산)
하므로 GameRun이 상태(클론·포트폴리오·day·stats·RunStore)를 들고 하루치 코어
(`run_loop.step_day`)를 1일씩 굴린다. batch와 동치(DRY). 결정론(회차 재현 기둥3).

/map은 이 세션의 state를 배경 연출로 연기한다(§12.0 엔진→표현 단방향).
"""

from __future__ import annotations

import random
from dataclasses import asdict

from .avoidance import avoid as _avoid_slots, clone_picks_npc
from .clone_spec import CloneSpec
from .clone_stats import MENTAL, stat_for_trap
from .day_loop import clone_disturbance, day_slots, overlap_meetings
from .tuning import clamp
from .fate_line import CATEGORIES, FateLine, load_fate_line
from .resistance import update_rapport
from .result_card import evaluate
from .run_loop import _DEFAULT_STATS, step_day
from .runs import DailySnapshot, RunStore, RunSummary
from . import social as _social
from .traps import get_trap
from .trap_pipeline import Intervention

# 일과 행동 메뉴(고정, §12.2) — 클론의 8슬롯에 순환 배치(결정론).
_MENU = ["카페", "일터", "광장", "운동", "집_차트"]
# NPC 일과(고정, 회차 불변 §9.2.1). 안정형 거북이 / 자극형 개구리.
_NPC_SCHEDS = {"turtle": {2: "일터", 5: "운동"}, "frog": {3: "광장", 7: "집_차트"}}
# NPC가 자극하는 함정(§9.2.1b 클론이 약점 자극 NPC에 끌림에서도 재사용). None=안정형.
_NPC_STIM_TRAP = {"turtle": None, "frog": "F1"}


class GameRun:
    """하루씩 진행 가능한 한 플레이어의 회차 세션."""

    def __init__(
        self,
        clone_spec: CloneSpec,
        *,
        category: str,
        start_price: float,
        days: int = 30,
        start_stats: dict | None = None,
        start_quantity: float = 1.0,
        start_cash: float = 0.0,
        fate_line: FateLine | None = None,
        store: RunStore | None = None,
        run_id: str = "run1",
        initial_rapport: float = 50.0,
        other_categories: tuple[str, ...] | None = None,
    ) -> None:
        self.clone_spec = clone_spec
        self.category = category
        self.start_price = start_price
        self.days = days
        self.fl = fate_line or load_fate_line()
        self.store = store or RunStore()
        self.run_id = run_id
        self.initial_rapport = initial_rapport
        self._start_quantity = start_quantity
        self._start_cash = start_cash
        # §8.3 T-210 — 보유하지 않은 감시 종목(M1 추격매수 컨텍스트). 기본값은
        # 나머지 전 카테고리(다자산 거울) — 명시로 좁히거나 끌 수 있다.
        self.other_categories = (
            other_categories if other_categories is not None
            else tuple(c for c in CATEGORIES if c != category)
        )
        self._base_stats = dict(start_stats or _DEFAULT_STATS)
        self._run_index = 0
        self.summary: RunSummary | None = None
        # §9.2.1 클론 일과(8슬롯 → 장소). 메뉴를 순환 배치(결정론). 회피로 순서만 바뀜.
        self.schedule = {i + 1: _MENU[i % len(_MENU)] for i in range(8)}
        self.npc_scheds = {k: dict(v) for k, v in _NPC_SCHEDS.items()}
        self._reset_run_state(run_id)

    # --- 회차 상태 ------------------------------------------------------- #
    def _reset_run_state(self, run_id: str) -> None:
        self.run_id = run_id
        self.stats = dict(self._base_stats)
        self.holding = {"avg_cost": self.start_price,
                        "quantity": self._start_quantity, "cash": self._start_cash}
        self.initial_total = self._start_cash + self._start_quantity * self.start_price
        self.day = 0
        self.last_price = self.start_price
        self.finished = False
        self.summary = None
        self.last_snap = None   # 표현 계층(§12.0)이 읽을 마지막 하루 결정
        self.last_event = None  # §5.4 그날의 클론 고유 이벤트(외란), 없으면 None
        self._prev_realized_pnl = 0.0  # §8.3 G2 — 직전 실현손익(자신감 문맥)
        run_state = self.store.start_run(run_id, self.initial_rapport)  # 래포·확증편향 리셋
        # §9.2.2/§11.4.4 — 위기개입과 1:1 권유가 공유하는 래포 풀. 회차마다 리셋.
        self.rapport: float = run_state["rapport"]
        self.crowd_mood: float = 50.0  # §9.2.3 FGI 단톡방 과열도(중립 시작)

    def new_run(self, run_id: str | None = None) -> None:
        """다음 회차 — 클론은 '처음 만남'으로 리셋, 요약은 누적(§13.8/§14.3)."""
        self._run_index += 1
        self._reset_run_state(run_id or f"run{self._run_index + 1}")

    # --- 하루 진행 ------------------------------------------------------- #
    def advance_day(self, *, news: dict | None = None, intervention=None,
                    strategy: str | None = None,
                    roll: float = 100.0, agent_pressure: float = 0.0):
        """하루를 1칸 진행. Day30 도달 시 정산. 끝났으면 None.

        개입은 두 방식: (1) `intervention` 객체를 직접 넘기면 그대로 사용(외부
        래포 오버라이드, batch/테스트용). (2) `strategy`만 넘기면 세션이 보유한
        `self.rapport`(1:1 권유와 공유하는 풀 §11.4.4)로 자동 구성하고, 결과에
        따라 `self.rapport`를 갱신한다 — 이게 "권유→위기개입 성공률"의 연결점.
        """
        if self.finished or self.day >= self.days:
            self.finished = True
            return None
        if intervention is None and strategy is not None:
            intervention = Intervention(strategy, self.rapport)
        plan = {"news": news, "intervention": intervention,
                "roll": roll, "agent_pressure": agent_pressure,
                "prev_realized_pnl": self._prev_realized_pnl,
                "crowd_mood": self.crowd_mood}
        res = step_day(self.clone_spec, self.stats, self.fl, self.category,
                       self.day, self.start_price, self.holding, plan,
                       other_categories=self.other_categories)
        self.day += 1
        snap = None
        if res is not None:
            snap, self.holding, self.last_price = res
            self.stats = snap.emotion_stats
            self.last_snap = snap
            self._prev_realized_pnl = snap.realized_pnl
            if intervention is not None and snap.trap is not None:
                # 개입이 실제로 관여한 위기 — 결과로 공유 래포 풀 갱신(§11.4.4).
                self.rapport = update_rapport(self.rapport, was_right=not snap.swayed)
            # §5.4 고유 이벤트 외란 — 멘탈회복만 작게(§12.3). 트리거 아님→수익률 무관.
            self.last_event = clone_disturbance(self.clone_spec, random.Random(1000 + self.day))
            if self.last_event is not None and "멘탈회복" in self.stats:
                self.stats["멘탈회복"] = clamp(
                    self.stats["멘탈회복"] + self.last_event["delta"], 0.0, 100.0)
            self.store.record_snapshot(self.run_id, snap)
        if self.day >= self.days:
            self._settle_run()
        return snap

    def _settle_run(self) -> None:
        self.finished = True
        # last_snap.total_asset은 다자산 포지션(§8.3)까지 포함한 정확한 값.
        final_total = (self.last_snap.total_asset if self.last_snap is not None
                       else self.holding["cash"] + self.holding["quantity"] * self.last_price)
        return_pct = ((final_total - self.initial_total) / self.initial_total * 100.0) \
            if self.initial_total else 0.0
        control = sum(self.stats.values()) / len(self.stats) if self.stats else 50.0
        self.summary = RunSummary(
            run_id=self.run_id, return_pct=round(return_pct, 2),
            emotion_overall=self.stats, grade=evaluate(return_pct, control),
            trap_counts={}, clone_spec_snapshot=dict(self.clone_spec.trap_scores),
        )
        self.store.record_summary(self.summary)

    # --- §9.2.1 전날밤 일과 미리보기 + 회피 ------------------------------ #
    def preview_day(self) -> dict:
        """내일 일과(8슬롯) + 변경 안 하면 마주칠 NPC.

        §9.2.1b — 후보가 여럿이면 *클론이* 고른다(플레이어 아님, 가장 약한 함정을
        자극하는 쪽에 끌림). `picks[slot]`로 그 선택 결과를 노출한다. (뉴스·위기는
        비공개 §12.4)
        """
        meetings = overlap_meetings(self.schedule, self.npc_scheds)
        picks = {
            slot: clone_picks_npc(candidates, self.clone_spec.trap_scores, _NPC_STIM_TRAP)
            for slot, candidates in meetings.items()
        }
        return {
            "slots": day_slots(),
            "schedule": dict(self.schedule),
            "meetings": meetings,
            "picks": picks,
        }

    def preview_crisis(self, *, news: dict | None = None) -> dict:
        """오늘 위기가 실제 발생하는지 부작용 없이 미리 판정(사용자 피드백:

        위기 개입은 상시 노출이 아니라 위기가 진짜 터진 순간에만 이벤트로
        떠야 한다). trap 감지(STEP1)는 intervention·roll과 무관하게 시장
        조건만으로 결정되므로, 여기서 개입 없이 계산해도 실제 advance_day
        결과와 항상 일치한다(결정론).
        """
        if self.finished or self.day >= self.days:
            return {"trap": None, "trap_name": None}
        plan = {"news": news, "intervention": None, "roll": 100.0,
                "agent_pressure": 0.0, "prev_realized_pnl": self._prev_realized_pnl,
                "crowd_mood": self.crowd_mood}
        res = step_day(self.clone_spec, self.stats, self.fl, self.category,
                       self.day, self.start_price, self.holding, plan,
                       other_categories=self.other_categories)
        if res is None:
            return {"trap": None, "trap_name": None}
        snap, _holding, _price = res
        trap = get_trap(snap.trap) if snap.trap else None
        return {"trap": snap.trap, "trap_name": trap.name if trap else None}

    def avoid(self, slot_a: int, slot_b: int) -> dict:
        """일과 항목 하나의 순서만 변경(두 슬롯 스왑) → 마주칠 NPC가 달라진다."""
        self.schedule = _avoid_slots(self.schedule, slot_a, slot_b)
        return overlap_meetings(self.schedule, self.npc_scheds)

    # --- §9.2.2 1:1 권유 + §9.2.3 FGI 단톡방 ------------------------------ #
    def persuade(self, npc_id: str, direction: str, roll: float = 100.0,
                escalation: float = 0.0) -> dict:
        """1:1 대화 중 권유 — 위기개입과 같은 래포 풀(§11.4.4), 방향만 격화/안정."""
        if npc_id not in _NPC_STIM_TRAP:
            return {"accepted": False, "success_prob": 0.0,
                    "stats": dict(self.stats), "rapport": self.rapport}
        trap_id = _NPC_STIM_TRAP[npc_id]
        stat_name = stat_for_trap(trap_id) if trap_id else MENTAL
        out = _social.apply_persuasion(direction, stat_name, self.stats,
                                       self.rapport, roll=roll, escalation=escalation)
        self.stats = out["stats"]
        self.rapport = out["rapport"]
        return out

    def fgi_post(self, tone: str, roll: float = 100.0) -> dict:
        """단톡방에 톤 얹기 — 래포 무관, 군중+클론(멘탈회복) 약하게(§9.2.3)."""
        out = _social.fgi_post(tone, self.crowd_mood, self.stats.get(MENTAL, 50.0), roll=roll)
        self.crowd_mood = out["crowd_mood"]
        self.stats[MENTAL] = out["clone_stat_value"]
        return out

    # --- 표현 계층이 읽는 스냅샷 ----------------------------------------- #
    def state(self) -> dict:
        return {
            "run_id": self.run_id,
            "day": self.day,
            "days": self.days,
            "finished": self.finished,
            "stats": dict(self.stats),
            "portfolio": dict(self.holding),
            "total_asset": round(
                self.last_snap.total_asset if self.last_snap is not None
                else self.holding["cash"] + self.holding["quantity"] * self.last_price, 4),
            "category": self.category,
            "last_event": self.last_event,
            "rapport": round(self.rapport, 2),
            "crowd_mood": round(self.crowd_mood, 2),
        }

    # --- 직렬화(§13.8 T-DB — MongoDB 영속화, 서버 재시작 후 game_id로 재개) --- #
    def to_doc(self) -> dict:
        """`fl`(고정 운명선, 전 세션 공유)은 제외 — 로드시 새로 얹는다."""
        return {
            "clone_spec": asdict(self.clone_spec),
            "category": self.category,
            "start_price": self.start_price,
            "days": self.days,
            "start_quantity": self._start_quantity,
            "start_cash": self._start_cash,
            "other_categories": list(self.other_categories),
            "base_stats": dict(self._base_stats),
            "run_index": self._run_index,
            "initial_rapport": self.initial_rapport,
            "schedule": {str(k): v for k, v in self.schedule.items()},
            "run_id": self.run_id,
            "stats": dict(self.stats),
            "holding": dict(self.holding),
            "initial_total": self.initial_total,
            "day": self.day,
            "last_price": self.last_price,
            "finished": self.finished,
            "summary": asdict(self.summary) if self.summary is not None else None,
            "last_snap": asdict(self.last_snap) if self.last_snap is not None else None,
            "last_event": self.last_event,
            "prev_realized_pnl": self._prev_realized_pnl,
            "rapport": self.rapport,
            "crowd_mood": self.crowd_mood,
            "store": self.store.to_dict(),
        }

    @classmethod
    def from_doc(cls, doc: dict, fate_line: FateLine | None = None) -> "GameRun":
        g = cls(
            CloneSpec(**doc["clone_spec"]),
            category=doc["category"], start_price=doc["start_price"], days=doc["days"],
            start_stats=doc["base_stats"], start_quantity=doc["start_quantity"],
            start_cash=doc["start_cash"], fate_line=fate_line,
            store=RunStore.from_dict(doc["store"]),
            run_id=doc["run_id"], initial_rapport=doc["initial_rapport"],
            other_categories=tuple(doc["other_categories"]),
        )
        # __init__이 새 회차로 리셋해버리므로, 저장된 실제 진행 상태를 그 위에 덮는다.
        g._run_index = doc["run_index"]
        g.schedule = {int(k): v for k, v in doc["schedule"].items()}
        g.stats = dict(doc["stats"])
        g.holding = dict(doc["holding"])
        g.initial_total = doc["initial_total"]
        g.day = doc["day"]
        g.last_price = doc["last_price"]
        g.finished = doc["finished"]
        g.summary = RunSummary(**doc["summary"]) if doc["summary"] is not None else None
        g.last_snap = DailySnapshot(**doc["last_snap"]) if doc["last_snap"] is not None else None
        g.last_event = doc["last_event"]
        g._prev_realized_pnl = doc["prev_realized_pnl"]
        g.rapport = doc["rapport"]
        g.crowd_mood = doc["crowd_mood"]
        return g
