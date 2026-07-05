"""§13 회차(NG+) 스토어 + 회차 비교 — 게임의 수명 + 거울의 핵심 산출물.

같은 시험지(고정 운명선 §6.3)를 여러 번 살며 "1회차의 나 vs 2회차의 나"를 겹쳐
본다(기둥2). §13.8 3계층 영속:
  · 회차 요약  — 카드·등급·6함정 발동/저항·클론스펙 스냅샷 → **영구**(컬렉션 §14.3)
  · 위기 로그  — 위기별 행동·개입·자금행선지·결과     → **최근 N회차**(기본 5)
  · 개입 로그  — 클론 과거 충동 행동                  → **현재+직전**(과거찌르기 A)

회차마다 래포·확증편향은 리셋(클론은 "처음 만남")되지만 요약은 누적 → 나는 성장.
인메모리 — Mongo 영속화는 하드게이트(D-D)로 별도.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

_KEEP_IMPULSE = 2   # 현재+직전 (§13.8)


@dataclass
class RunSummary:
    run_id: str
    return_pct: float = 0.0
    emotion_overall: dict = field(default_factory=dict)
    grade: str = ""
    trap_counts: dict = field(default_factory=dict)   # trap_id → {triggered, resisted}
    clone_spec_snapshot: dict = field(default_factory=dict)


@dataclass
class DailySnapshot:
    """§6.5.6 — 매일 밤 회차별 기록(회차 비교의 데이터 소스)."""

    day: int
    holdings: dict = field(default_factory=dict)
    cash: float = 0.0
    total_asset: float = 0.0
    realized_pnl: float = 0.0
    trades: list = field(default_factory=list)
    emotion_stats: dict = field(default_factory=dict)
    swayed: bool = False             # 휘둘렸는가(함정 발동+충동 매매)
    fund_flow: str = ""              # §8.3 자금 행선지
    companion: str = ""              # 그날 주로 누구와 교류했나
    trap: str | None = None          # 그날 발동·선정된 함정(없으면 None, 번들이면 첫 항목과 동일)
    # T-216 D4 — 분산 보유 시 같은 날 여러 종목이 트리거되면 여기 전부 담긴다.
    # [{category, trap, trap_name, resisted, reason, fund_flow, realized_pnl}, ...]
    # 트리거가 0/1개일 때도 채워짐(0개=[], 1개=[그 항목]) — bundle이 항상 정답.
    bundle: list = field(default_factory=list)
    # T-269 발자취 — 그날의 뉴스 선택·전체 만남·일과(회피 반영). 기본값이 있어
    # 구 문서 하위호환 안전(from_dict의 **unpack에 키가 없어도 됨).
    news_id: str = ""
    news_tone: str = ""                     # fear | optimism | uncertain | ""(미선택)
    met: list = field(default_factory=list)  # 그날 만난 NPC 전원(첫 항목=companion)
    schedule: dict = field(default_factory=dict)  # 슬롯→장소(진행 시점, 회피 반영)


class RunStore:
    """회차 데이터의 인메모리 3계층 저장소."""

    def __init__(self, keep_crisis: int = 5) -> None:
        self.keep_crisis = keep_crisis
        self._summaries: dict[str, RunSummary] = {}              # 영구
        self._crisis: dict[str, dict[int, dict]] = {}            # 최근 N
        self._impulse: dict[str, list] = {}                     # 현재+직전
        self._snapshots: dict[str, dict[int, DailySnapshot]] = {}
        self._order: list[str] = []

    # --- 회차 시작/리셋 --------------------------------------------------- #
    def start_run(self, run_id: str, initial_rapport: float = 50.0) -> dict:
        """새 회차 시작. 래포·확증편향 리셋, 최근성 윈도 정리. 요약은 유지."""
        if run_id not in self._order:
            self._order.append(run_id)
        self._snapshots.setdefault(run_id, {})
        self._crisis.setdefault(run_id, {})
        self._impulse.setdefault(run_id, [])
        self._trim()
        return {"run_id": run_id, "rapport": initial_rapport, "confirmation_locked": False}

    def _trim(self) -> None:
        crisis_keep = set(self._order[-self.keep_crisis:])
        for rid in list(self._crisis):
            if rid not in crisis_keep:
                self._crisis.pop(rid, None)
        impulse_keep = set(self._order[-_KEEP_IMPULSE:])
        for rid in list(self._impulse):
            if rid not in impulse_keep:
                self._impulse.pop(rid, None)

    # --- 기록 ------------------------------------------------------------- #
    def record_summary(self, summary: RunSummary) -> None:
        self._summaries[summary.run_id] = summary

    def record_snapshot(self, run_id: str, snap: DailySnapshot) -> None:
        self._snapshots.setdefault(run_id, {})[snap.day] = snap

    def snapshots(self, run_id: str) -> dict[int, DailySnapshot]:
        """T-269 — 회차의 전체 일별 스냅샷(day→snap). 순수 조회."""
        return self._snapshots.get(run_id, {})

    def record_crisis(self, run_id: str, day: int, log: dict) -> None:
        if run_id in self._crisis:
            self._crisis[run_id][day] = log

    def record_impulse(self, run_id: str, entry: dict) -> None:
        if run_id in self._impulse:
            self._impulse[run_id].append(entry)

    # --- 조회 ------------------------------------------------------------- #
    def get_summary(self, run_id: str) -> RunSummary | None:
        return self._summaries.get(run_id)

    def summaries(self) -> list[RunSummary]:
        """영구 컬렉션(성장 연대기 §14.3) — 등록 순서."""
        return [self._summaries[r] for r in self._order if r in self._summaries]

    def get_snapshot(self, run_id: str, day: int) -> DailySnapshot | None:
        return self._snapshots.get(run_id, {}).get(day)

    def get_crisis(self, run_id: str, day: int) -> dict | None:
        return self._crisis.get(run_id, {}).get(day)

    def get_impulses(self, run_id: str) -> list:
        return self._impulse.get(run_id, [])

    # --- 직렬화(§13.8 T-DB — MongoDB 영속화용, 순수 dict 왕복) -------------- #
    def to_dict(self) -> dict:
        """crisis/impulse(현재 아무 곳에서도 안 씀)는 제외 — 국소 스코프."""
        return {
            "order": list(self._order),
            "summaries": {rid: asdict(s) for rid, s in self._summaries.items()},
            # BSON/JSON 키는 문자열만 허용 — day(int)를 문자열로.
            "snapshots": {
                rid: {str(day): asdict(snap) for day, snap in days.items()}
                for rid, days in self._snapshots.items()
            },
        }

    @classmethod
    def from_dict(cls, doc: dict, keep_crisis: int = 5) -> "RunStore":
        store = cls(keep_crisis=keep_crisis)
        store._order = list(doc.get("order", []))
        store._summaries = {
            rid: RunSummary(**s) for rid, s in doc.get("summaries", {}).items()
        }
        store._snapshots = {
            rid: {int(day): DailySnapshot(**snap) for day, snap in days.items()}
            for rid, days in doc.get("snapshots", {}).items()
        }
        for rid in store._order:
            store._crisis.setdefault(rid, {})
            store._impulse.setdefault(rid, [])
        return store


def runs_comparable(store: RunStore, run_a: str, run_b: str) -> bool:
    """§13.6 비교 가능 여부 — 서로 다른 두 회차 모두 스냅샷이 있어야 한다.

    (/review 지적: 검증 없이 빈 목록을 돌려주면 프론트가 존재하지 않는 회차에
    대해 "두 회차가 같은 선택을 했습니다"라는 틀린 결론을 자신 있게 그린다.)
    """
    return (run_a != run_b
            and bool(store._snapshots.get(run_a))
            and bool(store._snapshots.get(run_b)))


def diverging_days(store: RunStore, run_a: str, run_b: str) -> list[int]:
    """§13.6/T-227 — 두 회차의 행동이 실제로 갈린 날 목록(오름차순).

    비교 기준은 행동 3요소(swayed·fund_flow·companion) — "결과 아는 날은
    빨리감기"(§13.3): 같은 선택을 한 날은 비교 화면에 나열하지 않는다.
    양쪽 모두에 스냅샷이 있는 날만 대상(미완주 회차의 잔여일 제외).
    """
    a_days = store._snapshots.get(run_a, {})
    b_days = store._snapshots.get(run_b, {})
    out = []
    for day in sorted(set(a_days) & set(b_days)):
        a, b = a_days[day], b_days[day]
        if (a.swayed, a.fund_flow, a.companion) != (b.swayed, b.fund_flow, b.companion):
            out.append(day)
    return out


def compare_runs(store: RunStore, run_a: str, run_b: str, day: int) -> dict:
    """§13.6 회차 비교 — 같은 Day를 두 회차로 겹쳐 본다(거울의 핵심 산출물)."""

    def view(rid: str) -> dict | None:
        snap = store.get_snapshot(rid, day)
        if snap is None:
            return None
        return {
            "swayed": snap.swayed,
            "companion": snap.companion,
            "fund_flow": snap.fund_flow,
            "realized_pnl": snap.realized_pnl,
            "total_asset": snap.total_asset,
        }

    return {"day": day, "a": view(run_a), "b": view(run_b)}
