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

from . import board_exposure
from .interview import build_initial_emotion
from .player_emotion.deltas import apply_delta
from .player_emotion.log import EmotionLog, record_snapshot
from .player_emotion.state import PlayerEmotionState
from .player_emotion.verdict import compute_verdict

START_VALUE = 1_000_000.0


def _day_rng(seed: int, day: int) -> random.Random:
    """(seed, day)로 결정론 rng — 같은 날은 항상 같은 게시판(재생 가능)."""
    return random.Random(seed * 1000 + day)


@dataclass
class EmoGameRun:
    emotion: PlayerEmotionState
    events: list[str]
    returns: list[float]
    seed: int
    day: int = 0
    portfolio_value: float = START_VALUE
    log: EmotionLog = field(default_factory=EmotionLog)

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
        )
        run._enter_day()   # day 0 노출 델타 1회
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
        """그 날에 진입할 때 노출 델타를 1회 적용한다(강제노출·스킵 불가)."""
        if self.is_over:
            return
        board = self.board()
        delta = board_exposure.exposure_delta(self.events[self.day], board["threads"])
        self.emotion = apply_delta(self.emotion, delta)

    def choose(self, choice_id: str) -> None:
        """선택지 델타 적용 → 스냅샷 기록 → 시장 반영 → 다음 날 진입."""
        if self.is_over:
            raise RuntimeError("game is over")
        event_id = self.events[self.day]
        self.emotion = board_exposure.apply_choice(self.emotion, event_id, choice_id)
        self.log = record_snapshot(self.log, self.day, self.emotion)
        ret = self.returns[self.day] if self.day < len(self.returns) else 0.0
        self.portfolio_value = round(self.portfolio_value * (1.0 + ret), 2)
        self.day += 1
        self._enter_day()

    # --- 종료 ------------------------------------------------------------- #
    def ending_inputs(self) -> dict:
        """엔딩 분기 입력(T-13): 감정 압축판정 + 재산 수준."""
        return {
            "verdict": compute_verdict(self.emotion),
            "wealth_level": "high" if self.portfolio_value >= START_VALUE else "low",
            "portfolio_value": self.portfolio_value,
        }

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
        return cls(
            emotion=PlayerEmotionState(**doc["emotion"]),
            events=list(doc["events"]),
            returns=list(doc["returns"]),
            seed=doc["seed"],
            day=doc["day"],
            portfolio_value=doc["portfolio_value"],
            log=EmotionLog(snapshots=snaps),
        )
