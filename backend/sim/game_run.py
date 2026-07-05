"""§12.4 step-able GameRun — 신 엔진 정본의 하루씩 플레이 세션 (D-E).

run_loop은 30일을 batch로 돈다. 플레이어는 하루씩 진행(전날밤→아침→위기→정산)
하므로 GameRun이 상태(클론·포트폴리오·day·stats·RunStore)를 들고 하루치 코어
(`run_loop.step_day`)를 1일씩 굴린다. batch와 동치(DRY). 결정론(회차 재현 기둥3).

/map은 이 세션의 state를 배경 연출로 연기한다(§12.0 엔진→표현 단방향).
"""

from __future__ import annotations

import random
import zlib
from dataclasses import asdict

from .avoidance import avoid as _avoid_slots, clone_picks_npc
from .clone_spec import CloneSpec
from .clone_stats import MENTAL, stat_for_trap
from .day_loop import clone_disturbance, day_slots, overlap_meetings, shuffle_schedule
from . import tuning as _T
from .tuning import clamp
from . import personas as _personas
from .fate_line import CATEGORIES, FateLine, load_fate_line
from .resistance import update_rapport
from .result_card import evaluate
from .run_loop import _DEFAULT_STATS, step_day
from .runs import DailySnapshot, RunStore, RunSummary
from . import social as _social
from . import board_v2 as _board_v2
from . import agent_state as _agent_state
from .traps import get_trap
from .trap_pipeline import Intervention

# 일과 행동 메뉴(고정, §12.2) — 클론의 8슬롯에 순환 배치(결정론).
# T-241 — 8슬롯=8곳(하루가 전부 다른 장소). 앞 5개 순서는 기존과 동일(슬롯 1~5
# 배치·만남 회귀 없음), 6~8에 펍·마켓·도서관 추가(the_ville 미사용 장소 활용).
_MENU = ["카페", "일터", "광장", "운동", "집_차트", "펍", "마켓", "도서관"]
# NPC 풀(§9.5.3 매매 에이전트 8종, T-221) — 데이터 원본은 personas.py.
# 일과는 고정·회차 불변(§9.2.1), stim_trap은 §9.2.1b 끌림·persuade가 재사용.
_NPC_SCHEDS = _personas.npc_scheds()
_NPC_STIM_TRAP = _personas.npc_stim_traps()


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
        initial_positions: dict[str, dict] | None = None,
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
        # §6.2/T-215 D1 — 분산 시작(주력 외 day0부터 보유하는 2차 포지션들).
        # {category: {avg_cost, quantity}}. 없으면 기존 단일종목 경로 그대로.
        self._initial_positions = dict(initial_positions or {})
        # §8.3 T-210 — 보유하지 않은 감시 종목(M1 추격매수 컨텍스트). 기본값은
        # 나머지 전 카테고리(다자산 거울)에서 day0부터 이미 보유한 것들은 제외
        # — 이미 들고 있는 종목은 "추격"할 대상이 아니다.
        self.other_categories = (
            other_categories if other_categories is not None
            else tuple(c for c in CATEGORIES if c != category and c not in self._initial_positions)
        )
        self._base_stats = dict(start_stats or _DEFAULT_STATS)
        self._run_index = 0
        self.summary: RunSummary | None = None
        # §9.2.1/§12.2 클론 일과(8슬롯 → 장소) — 종류는 고정 메뉴, 순서는 매일
        # 결정론 셔플(T-248). 회피는 그날 일과 위에만 적용(다음 날 이월 없음).
        self.schedule = self._schedule_for_day(0)
        self.npc_scheds = {k: dict(v) for k, v in _NPC_SCHEDS.items()}
        # T-252 — 게시판 대화 아카이브(공개 트랙): "day:news_id" → conversation.
        # **게임 레벨**(회차 무관) — 같은 날 같은 뉴스면 회차가 달라도 같은 대화
        # (같은 시험지 보호). new_run(_reset_run_state)에서 리셋하지 않는다.
        self.board_archive: dict[str, dict] = {}
        self._reset_run_state(run_id)

    def _schedule_for_day(self, day: int) -> dict[int, str]:
        """§12.2/T-248 — 그날의 일과 순서(결정론 셔플, 종류 집합은 불변)."""
        rng = random.Random(zlib.crc32(f"sched:{self.run_id}:{day}".encode()))
        order = shuffle_schedule(_MENU, rng)
        return {i + 1: order[i] for i in range(8)}

    # --- 회차 상태 ------------------------------------------------------- #
    def _reset_run_state(self, run_id: str) -> None:
        self.run_id = run_id
        self.schedule = self._schedule_for_day(0)   # T-248 — 새 회차 day0 일과
        self.stats = dict(self._base_stats)
        self.holding = {"avg_cost": self.start_price,
                        "quantity": self._start_quantity, "cash": self._start_cash}
        if self._initial_positions:
            self.holding["positions"] = {c: dict(p) for c, p in self._initial_positions.items()}
        self.initial_total = self._start_cash + self._start_quantity * self.start_price + sum(
            p["quantity"] * p["avg_cost"] for p in self._initial_positions.values())
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
        self._board: dict | None = None  # T-223 오늘의 게시판(하루 1회 확정, 캐시)
        # T-272a — 플레이어의 대화 상대 지정(슬롯→npc). 그날 하루만 유효(§9.2.1b
        # 기본은 여전히 클론의 선택 — 지정은 후보 안에서의 덮어쓰기).
        self._designated: dict[int, str] = {}
        # T-269 — 플레이어 소셜 액션 로그(권유·FGI). 이력 패널의 데이터 소스.
        self._social_log: list[dict] = []

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
        # T-249 — 오늘 동선이 겹친 NPC와의 만남을 실제 반영(§9.2.1b). companion은
        # 오늘 스냅샷에 기록(§13.6 '교류' 축), 감정 효과는 밤 정산에서(R1 —
        # preview_crisis==advance 판정 불변식을 지키기 위해 오늘 판정엔 미반영).
        met: list[str] = []
        meetings = overlap_meetings(self.schedule, self.npc_scheds)
        for slot in sorted(meetings):
            # T-272a — 플레이어 지정이 있고 여전히 후보 안이면 그쪽 우선.
            desig = self._designated.get(slot)
            pick = desig if desig in meetings[slot] else clone_picks_npc(
                meetings[slot], self.clone_spec.trap_scores, _NPC_STIM_TRAP)
            if pick:
                met.append(pick)
        self._met_today = met
        plan = {"news": news, "intervention": intervention,
                "roll": roll, "agent_pressure": agent_pressure,
                "prev_realized_pnl": self._prev_realized_pnl,
                "crowd_mood": self.crowd_mood,
                "companion": met[0] if met else ""}
        res = step_day(self.clone_spec, self.stats, self.fl, self.category,
                       self.day, self.start_price, self.holding, plan,
                       other_categories=self.other_categories)
        self.day += 1
        snap = None
        if res is not None:
            snap, self.holding, self.last_price = res
            # T-269 발자취 — 그날의 뉴스 선택·만남·일과를 스냅샷에 남긴다(이력 패널).
            snap.news_id = (news or {}).get("id", "")
            snap.news_tone = (news or {}).get("tone", "")
            snap.met = list(met)
            snap.schedule = dict(self.schedule)
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
        # T-223/D11 게시판 여파 — 그날 게시판이 열렸으면 과열 델타를 밤 정산에서
        # 정확히 1회 반영(self.day는 위에서 이미 +1됨). 관찰 GET은 무변이라
        # preview_crisis==advance_day 불변식·결정론이 유지된다.
        if (self._board is not None and self._board.get("day") == self.day - 1
                and self._board.get("open") and not self._board.get("mood_applied")):
            self.crowd_mood = clamp(
                self.crowd_mood + clamp(self._board["crowd_mood_delta"],
                                        -_T.CROWD_DELTA_CLAMP, _T.CROWD_DELTA_CLAMP),
                0.0, 100.0)
            self._board["mood_applied"] = True
        # T-249 — 만남 감정 효과(밤 정산, R1): 자극형은 관련 저항 스탯을 소폭 깎고
        # 도움형은 멘탈회복을 소폭 올린다(§11.5.4 대화 보정과 같은 급, 하루 상한 없음
        # — 만남은 하루 최대 몇 건이고 스탯은 클램프·게임 자체 동학으로 평형).
        for npc_id in getattr(self, "_met_today", []):
            trap_id = _NPC_STIM_TRAP.get(npc_id)
            if trap_id:
                stat = stat_for_trap(trap_id)
                self.stats[stat] = clamp(
                    self.stats.get(stat, 50.0) - _T.MEETING_STIM_DELTA, 0.0, 100.0)
            else:
                self.stats[MENTAL] = clamp(
                    self.stats.get(MENTAL, 50.0) + _T.MEETING_CALM_DELTA, 0.0, 100.0)
        self._met_today = []
        self._designated = {}  # T-272a — 지정은 그날 하루만(일일 셔플 T-248과 동일 수명)
        # §9.3 폭주 방지 — 군중 분위기는 밤사이 중립으로 일부 회귀(게시판·FGI로
        # 올라간 과열이 영구 고착돼 M2를 상시 발동시키는 되먹임 차단, T-225).
        self.crowd_mood = clamp(
            50.0 + (self.crowd_mood - 50.0) * (1.0 - _T.CROWD_MOOD_REVERT), 0.0, 100.0)
        # T-248 — 다음 날 일과는 그날의 셔플(어제의 회피 스왑은 이월되지 않음).
        if self.day < self.days:
            self.schedule = self._schedule_for_day(self.day)
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
        # T-272a — 플레이어 지정(후보 안일 때만 유효)이 클론의 선택을 덮어쓴다.
        picks = {
            slot: (self._designated[slot]
                   if self._designated.get(slot) in candidates
                   else clone_picks_npc(candidates, self.clone_spec.trap_scores,
                                        _NPC_STIM_TRAP))
            for slot, candidates in meetings.items()
        }
        return {
            "slots": day_slots(),
            "schedule": dict(self.schedule),
            "meetings": meetings,
            "picks": picks,
            "designated": {s: n for s, n in self._designated.items()
                           if n in meetings.get(s, [])},
        }

    def preview_crisis(self, *, news: dict | None = None) -> dict:
        """오늘 위기가 실제 발생하는지 부작용 없이 미리 판정(사용자 피드백:

        위기 개입은 상시 노출이 아니라 위기가 진짜 터진 순간에만 이벤트로
        떠야 한다). trap 감지(STEP1)는 intervention·roll과 무관하게 시장
        조건만으로 결정되므로, 여기서 개입 없이 계산해도 실제 advance_day
        결과와 항상 일치한다(결정론).
        """
        if self.finished or self.day >= self.days:
            return {"trap": None, "trap_name": None, "bundle": []}
        plan = {"news": news, "intervention": None, "roll": 100.0,
                "agent_pressure": 0.0, "prev_realized_pnl": self._prev_realized_pnl,
                "crowd_mood": self.crowd_mood}
        res = step_day(self.clone_spec, self.stats, self.fl, self.category,
                       self.day, self.start_price, self.holding, plan,
                       other_categories=self.other_categories)
        if res is None:
            return {"trap": None, "trap_name": None, "bundle": []}
        snap, _holding, _price = res
        trap = get_trap(snap.trap) if snap.trap else None
        # T-216 D4 — 번들 미리보기는 어느 종목·함정이 걸렸는지만(category/trap/
        # trap_name) 노출한다. resisted/reason은 STEP1(감지)이 아니라 STEP4~5
        # (개입·판정)의 산물이라 roll=100/개입없음인 이 미리보기에선 의미가 없다
        # — 실제 결과는 advance_day에서 플레이어가 고른 전략으로 다시 판정된다.
        bundle_preview = [
            {"category": b["category"], "trap": b["trap"], "trap_name": get_trap(b["trap"]).name}
            for b in snap.bundle
        ]
        return {"trap": snap.trap, "trap_name": trap.name if trap else None, "bundle": bundle_preview}

    def avoid(self, slot_a: int, slot_b: int) -> dict:
        """일과 항목 하나의 순서만 변경(두 슬롯 스왑) → 마주칠 NPC가 달라진다."""
        self.schedule = _avoid_slots(self.schedule, slot_a, slot_b)
        return overlap_meetings(self.schedule, self.npc_scheds)

    def designate(self, slot: int, npc_id: str | None) -> dict:
        """T-272a — 이 슬롯의 대화 상대를 플레이어가 지정(§9.2.1b 덮어쓰기).

        npc_id=None이면 지정 해제(클론에게 맡김). 그 슬롯 후보가 아닌 NPC는
        거부 — 클론의 동선 밖 인물과 억지로 만나게 할 수는 없다(회피와 대칭:
        플레이어 개입은 언제나 '이미 가능한 것' 안에서만).
        """
        if npc_id is None:
            self._designated.pop(slot, None)
            return self.preview_day()
        meetings = overlap_meetings(self.schedule, self.npc_scheds)
        if npc_id not in meetings.get(slot, []):
            raise ValueError(f"npc {npc_id!r}는 슬롯 {slot}의 후보가 아님")
        self._designated[slot] = npc_id
        return self.preview_day()

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
        # T-269 — 발자취: 플레이어의 권유 시도를 일자와 함께 기록.
        self._social_log.append({"day": self.day, "kind": "persuade",
                                 "npc_id": npc_id, "direction": direction,
                                 "accepted": bool(out.get("accepted"))})
        return out

    def fgi_post(self, tone: str, roll: float = 100.0) -> dict:
        """단톡방에 톤 얹기 — 래포 무관, 군중+클론(멘탈회복) 약하게(§9.2.3)."""
        out = _social.fgi_post(tone, self.crowd_mood, self.stats.get(MENTAL, 50.0), roll=roll)
        self.crowd_mood = out["crowd_mood"]
        self.stats[MENTAL] = out["clone_stat_value"]
        # T-269 — 발자취: 단톡방 글도 기록.
        self._social_log.append({"day": self.day, "kind": "fgi", "tone": tone})
        return out

    def history(self) -> list[dict]:
        """T-269 — 이 회차의 일별 발자취(뉴스 선택·만남·소셜·일과). 순수 조회."""
        snaps = self.store.snapshots(self.run_id)
        return [{
            "day": day,
            "news_id": s.news_id, "news_tone": s.news_tone,
            "met": list(s.met), "companion": s.companion,
            "schedule": {str(k): v for k, v in (s.schedule or {}).items()},
            "swayed": s.swayed, "trap": s.trap,
            "social": [e for e in self._social_log if e.get("day") == day],
        } for day, s in sorted(snaps.items())]

    def board_today(self, drawn_news: list[dict], use_llm: bool = False) -> dict:
        """T-223 게시판(D1~D3) — 이벤트 날만 열리고, 하루 1회 확정 생성.

        같은 날 재호출은 캐시 반환. 트리거는 위기(preview_crisis, 부작용 없음) 또는
        그날 뽑힌 뉴스의 고강도 여부(D2). 시드는 (run_id, day) 고정 crc32.

        ⚠️ 관찰 전용 — 상태(crowd_mood)를 변이하지 않는다. 여파(crowd_mood_delta)는
        advance_day의 밤 정산에서 1회 반영(D11) — GET에서 변이하면 crisis_check와의
        레이스·동시호출 이중적용·네트워크 유실로 결정론이 깨진다(/review에서 발견).
        """
        if self._board is not None and self._board.get("day") == self.day:
            return self._board
        # D2 개정 — 트리거는 공개 이벤트만: 시장 급변동(전일 대비) 또는 고강도 뉴스.
        # 클론의 함정(preview_crisis)은 여기서 안 본다(§12.4 비공개 — 누설 금지).
        market_move = self.fl.change_rate(self.category, self.day)
        context = _social.board_trigger(market_move, drawn_news)
        # T-257 — 첫인상 보장: 플레이어가 실제 처음 플레이하는 날(day 0)은 트리거
        # 무관 반드시 한 번 열린다(발견성). /review 정정 — day 1로 걸면 보장이
        # 두 번째 날에 발동해 "첫 세션에서 반드시 본다"는 DoD가 깨진다.
        if context is None and self.day == 0:
            context = _social.board_first_day_context(drawn_news)
        if context is None:
            board: dict = {"day": self.day, "open": False, "context": None,
                           "posts": [], "crowd_mood_delta": 0.0,
                           "recent": self._recent_board()}
        else:
            # T-251~253(게시판 v2) — 그날 뉴스에 대한 에이전트 대화. 공개 트랙은
            # 게임 레벨 아카이브에 박제(회차 무관 재사용 — 같은 시험지 보호),
            # 클론 발언만 회차별로 주입(D9 규칙).
            news_id, _ = _board_v2._news_line(drawn_news)
            key = f"{self.day}:{news_id}"
            conv = self.board_archive.get(key)
            if conv is None:
                if use_llm:
                    conv = _board_v2.llm_conversation(
                        context, drawn_news, market_move,
                        memory_digests=_agent_state.memory_digests(
                            self.board_archive, self.day))
                if conv is None:
                    rng = random.Random(
                        zlib.crc32(f"board:{self.run_id}:{self.day}".encode()))
                    conv = _board_v2.offline_conversation(
                        context, self.stats, drawn_news, rng)
                self.board_archive[key] = conv
            crng = random.Random(zlib.crc32(f"{self.run_id}:{self.day}".encode()))
            with_clone = _board_v2.inject_clone(conv, context, self.stats, crng)
            # T-259 — 여론 라벨은 클론 발언까지 포함해 "화면에 보이는 그대로"의
            # 다수결로 재계산(아카이브 verdict는 주입 전 값이라 체감과 어긋날 수 있음).
            board = {"day": self.day, "open": True, "mood_applied": False,
                     "context": context,
                     "verdict": _board_v2.verdict_from_speech(with_clone["threads"]),
                     "posts": _board_v2.to_posts(with_clone),
                     "crowd_mood_delta": with_clone["crowd_delta"]}
        self._board = board
        return board

    def _recent_board(self) -> dict | None:
        """T-257 — 닫힌 날 핸드폰 게시판 탭용: 가장 최근 박제 대화(읽기 전용).

        공개 트랙(아카이브) 그대로 — 클론 발언은 미주입(회차 불변 보호, council F2).
        """
        if not self.board_archive:
            return None
        key = max(self.board_archive, key=lambda k: int(k.split(":", 1)[0]))
        return {"day": int(key.split(":", 1)[0]),
                "posts": _board_v2.to_posts(self.board_archive[key])}

    # --- 표현 계층이 읽는 스냅샷 ----------------------------------------- #
    def _holdings_breakdown(self) -> list[dict]:
        """T-214 — 화면 표시용 종목별 분해(주력 + 2차 포지션). 순수 조회, 상태 무변경."""
        out: list[dict] = []
        qty = self.holding["quantity"]
        if qty:
            pnl = (self.last_price - self.holding["avg_cost"]) * qty
            out.append({
                "category": self.category,
                "quantity": round(qty, 6),
                "avg_cost": round(self.holding["avg_cost"], 4),
                "value": round(qty * self.last_price, 4),
                "unrealized_pnl": round(pnl, 4),
            })
        for cat, pos in self.holding.get("positions", {}).items():
            pqty = pos["quantity"]
            if not pqty:
                continue
            fate = self.fl.day_ohlc(cat, self.day)
            price = fate[3] if fate is not None else pos["avg_cost"]
            out.append({
                "category": cat,
                "quantity": round(pqty, 6),
                "avg_cost": round(pos["avg_cost"], 4),
                "value": round(pqty * price, 4),
                "unrealized_pnl": round((price - pos["avg_cost"]) * pqty, 4),
            })
        return out

    def state(self) -> dict:
        holdings = self._holdings_breakdown()
        return {
            "run_id": self.run_id,
            "day": self.day,
            "days": self.days,
            "finished": self.finished,
            "stats": dict(self.stats),
            "portfolio": {**dict(self.holding), "holdings": holdings},
            "total_asset": round(
                self.last_snap.total_asset if self.last_snap is not None
                else self.holding["cash"] + sum(h["value"] for h in holdings), 4),
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
            "initial_positions": self._initial_positions,
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
            "board": self._board,
            "designated": {str(k): v for k, v in self._designated.items()},  # T-272a
            "social_log": list(self._social_log),   # T-269
            "archive": self.board_archive,   # T-252 — 대화 박제(재시작 안전)
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
            initial_positions=doc.get("initial_positions") or None,
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
        g._board = doc.get("board")   # T-223 이전 문서엔 없음 → None(하위호환)
        # T-272a 이전 문서엔 없음 → {}(하위호환)
        g._designated = {int(k): v for k, v in (doc.get("designated") or {}).items()}
        g._social_log = doc.get("social_log") or []   # T-269 하위호환
        # T-250 부호 전환 하위호환 — 무부호 시절(verdict 없음) 박제된 공포 게시판의
        # +델타를 새 의미(양수=탐욕)로 적용하면 역방향 블립 → 부호 반전.
        if (g._board and "verdict" not in g._board
                and g._board.get("context") in ("fear", "unrest")
                and g._board.get("crowd_mood_delta", 0) > 0):
            g._board["crowd_mood_delta"] = -g._board["crowd_mood_delta"]
        g.board_archive = doc.get("archive") or {}   # T-252 하위호환
        return g
