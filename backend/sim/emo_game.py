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
from .interview import build_initial_emotion
from .personas import npc_scheds
from .player_emotion.deltas import apply_delta
from .player_emotion.log import EmotionLog, record_snapshot
from .player_emotion.state import PlayerEmotionState
from .player_emotion.verdict import compute_verdict

START_VALUE = 1_000_000.0

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
    returns: list[float]
    seed: int
    day: int = 0
    portfolio_value: float = START_VALUE
    position: float = 1.0   # 투자 비중(0=현금, 1=풀투자) — 선택의 매매행동이 조절
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

    # --- 생성 ------------------------------------------------------------- #
    @classmethod
    def new(
        cls, answers: dict, events: list[str], returns: list[float], seed: int
    ) -> "EmoGameRun":
        run = cls(
            emotion=build_initial_emotion(answers),
            events=list(events),
            returns=list(returns),
            seed=seed,
            clone_route=_default_route(len(events)),
        )
        run._enter_day()   # day 0 노출 델타 1회 + companion 결정
        return run

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

    def choose(self, choice_id: str) -> None:
        """하루 결산: 시장 실현(진입 포지션) → 감정 델타+스냅샷 → 매매행동으로 포지션
        갱신 → 다음 날 진입.

        재산은 행동의 결과다: 오늘 시장 이동은 '어제 정한 포지션'만큼 맞고, 오늘 선택의
        매매(손절=현금↑, 추격=투자↑)는 '다음 날' 이동에 반영된다. 손절 후 반등을
        놓치고, 버티면 반등을 타는 행동적 인과가 생긴다."""
        if self.is_over:
            raise RuntimeError("game is over")
        event_id = self.events[self.day]
        choice = _scenario.get_choice(event_id, choice_id)   # 검증 먼저(변이 전)

        ret = self.returns[self.day] if self.day < len(self.returns) else 0.0
        self.portfolio_value = round(self.portfolio_value * (1.0 + ret * self.position), 2)

        self.emotion = apply_delta(self.emotion, choice["deltas"])
        self.log = record_snapshot(self.log, self.day, self.emotion)

        self.position = max(0.0, min(1.0, self.position + float(choice.get("position", 0.0))))
        self.day += 1
        self._enter_day()

    # --- 종료 ------------------------------------------------------------- #
    def ending_inputs(self) -> dict:
        """엔딩 분기 입력(T-13): 감정 압축판정 + 재산 수준 + 특수이벤트 누적."""
        return {
            "verdict": compute_verdict(self.emotion),
            "wealth_level": "high" if self.portfolio_value >= START_VALUE else "low",
            "portfolio_value": self.portfolio_value,
            "special_count": self.special_event_count,
        }

    def ending(self) -> dict:
        """최종 엔딩(E1~E5 + 등급 + 에필로그). 문서 §4."""
        ei = self.ending_inputs()
        return _ending.decide_ending(
            ei["verdict"], ei["wealth_level"], ei["special_count"]
        )

    # --- 직렬화 (T-14 영속화가 소비) ------------------------------------- #
    def to_doc(self) -> dict:
        return {
            "emotion": {
                "fear": self.emotion.fear, "greed": self.emotion.greed,
                "anxiety": self.emotion.anxiety, "restlessness": self.emotion.restlessness,
            },
            "events": self.events,
            "returns": self.returns,
            "seed": self.seed,
            "day": self.day,
            "portfolio_value": self.portfolio_value,
            "position": self.position,
            "clone_route": self.clone_route,
            "designations": {str(k): v for k, v in self.designations.items()},
            "companion_id": self.companion_id,
            "special_event_count": self.special_event_count,
            "chain_progress": self.chain_progress,
            "rapport": self.rapport,
            "pending_chain": self.pending_chain,
            "log": [
                {"turn": s.turn, "emotion": {
                    "fear": s.state.fear, "greed": s.state.greed,
                    "anxiety": s.state.anxiety, "restlessness": s.state.restlessness,
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
        return cls(
            emotion=PlayerEmotionState(**doc["emotion"]),
            events=list(doc["events"]),
            returns=list(doc["returns"]),
            seed=doc["seed"],
            day=doc["day"],
            portfolio_value=doc["portfolio_value"],
            position=doc.get("position", 1.0),
            log=EmotionLog(snapshots=snaps),
            clone_route=list(doc.get("clone_route") or _default_route(n)),
            designations={int(k): v for k, v in (doc.get("designations") or {}).items()},
            companion_id=doc.get("companion_id"),
            special_event_count=doc.get("special_event_count", 0),
            chain_progress={k: int(v) for k, v in (doc.get("chain_progress") or {}).items()},
            rapport={k: float(v) for k, v in (doc.get("rapport") or {}).items()},
            pending_chain=doc.get("pending_chain"),
        )
