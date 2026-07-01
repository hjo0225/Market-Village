"""Shared domain models for the Market Village simulation.

This module is the single source of truth for the data contract between the
simulation engine, the FastAPI surface, and the Next.js frontend. The field
names mirror the frontend mock_data types (frontend/mock_data/*.ts) so the UI
can swap mock data for API responses with minimal churn.

Pydantic v2 BaseModel is used throughout for free FastAPI (de)serialization.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Enums
# --------------------------------------------------------------------------- #
class AgentType(str, Enum):
    PANIC_SELLER = "panic_seller"
    FOMO_TRADER = "fomo_trader"
    VALUE_INVESTOR = "value_investor"
    QUANT = "quant"
    WHALE = "whale"
    NEWS_BOT = "news_bot"
    CONTRARIAN = "contrarian"
    CONSPIRACY = "conspiracy"
    GAMBLER = "gambler"   # §9.5.3 한탕 도박꾼 (G1·G2 부추김)


class Action(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    BUY_LARGE = "BUY_LARGE"


class Location(str, Enum):
    HOME = "home"
    COMMUNITY = "community"  # board / SNS
    EXCHANGE = "exchange"


class EventImpact(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


# --------------------------------------------------------------------------- #
# Static / reference data
# --------------------------------------------------------------------------- #
class Asset(BaseModel):
    """A tradeable asset. Mirrors frontend Asset (mock_data/market.ts)."""

    symbol: str
    name: str
    price: float
    change24h: float = 0.0
    volume: float = 0.0
    priceHistory: list[float] = Field(default_factory=list)
    sector: str = ""


class PortfolioHolding(BaseModel):
    """Mirrors frontend Agent.portfolio entry."""

    asset: str
    amount: float
    avgPrice: float


class Position(BaseModel):
    x: int = 0
    y: int = 0


# --------------------------------------------------------------------------- #
# Persona pool (static character definition) vs Agent (runtime state)
# --------------------------------------------------------------------------- #
class Persona(BaseModel):
    """A character template in the 20-persona pool.

    Personality is expressed purely as scratch text fields (innate/learned/
    currently/lifestyle/daily_req) per PRD §3.1 — these are injected into LLM
    prompts so tone (panic/cautious/hype) is generated for free.
    """

    persona_id: str
    alias: str  # SNS nickname e.g. "손절 금붕어"
    type: AgentType
    sprite: str
    color: str

    # scratch personality text (English; output asked in Korean)
    innate: str
    learned: str
    currently: str
    lifestyle: str
    daily_req: str

    # candidate pools — one is sampled (seeded) at game setup. No LLM.
    cash_pool: list[float]
    portfolio_symbol_pool: list[str]

    default_fear: float = 50.0
    default_greed: float = 50.0
    # Seed defaults for the detail axes (D3/7): persona-fixed starting points,
    # then nudged by the per-event LLM measurement. fear/greed stay the primary
    # axes; these three are persona-seeded, not user-set.
    default_confidence: float = 50.0
    default_excitement: float = 50.0
    default_trust: float = 50.0

    # optional behavioural sensitivities (0..1)
    herd_sensitivity: float = 0.5
    rumor_sensitivity: float = 0.5
    fear_threshold: float | None = None


class Agent(BaseModel):
    """Runtime agent state. Mirrors frontend Agent (mock_data/agents.ts)."""

    id: str
    alias: str
    type: str
    sprite: str
    cash: float
    portfolio: list[PortfolioHolding] = Field(default_factory=list)
    fear: float = 50.0
    greed: float = 50.0
    # Extra emotion axes (D3): each 0..100, 50 = neutral midpoint.
    confidence: float = 50.0   # 자신감 ↔ 위축 (driven by likes − dislikes)
    excitement: float = 50.0   # 흥분 ↔ 침착 (driven by hype/volatility)
    trust: float = 50.0        # 신뢰 ↔ 의심 (driven by news credibility/rumors)
    # SNS-only agents live only on the board (no map/movement/trade).
    sns_only: bool = False
    # C-012: 플레이어의 거울 클론(미연시 관계 대상). 세션당 최대 1명.
    is_player_clone: bool = False
    lastAction: str = "HOLD"
    location: Location = Location.HOME
    position: Position = Field(default_factory=Position)
    bubble: str = ""
    color: str = "#888888"

    # scratch personality (kept server-side, not strictly needed by FE)
    innate: str = ""
    learned: str = ""
    currently: str = ""
    lifestyle: str = ""
    daily_req: str = ""
    herd_sensitivity: float = 0.5
    rumor_sensitivity: float = 0.5
    fear_threshold: float | None = None

    def holding(self, symbol: str) -> PortfolioHolding | None:
        for h in self.portfolio:
            if h.asset == symbol:
                return h
        return None


# --------------------------------------------------------------------------- #
# Events, posts (board), emotion
# --------------------------------------------------------------------------- #
class Event(BaseModel):
    """User-input event. Mirrors frontend GameEvent (mock_data/events.ts)."""

    id: str
    round: int
    text: str
    source: str = "user"
    impact: EventImpact = EventImpact.NEUTRAL
    timestamp: str = ""
    is_rumor: bool = False
    cred_source: str | None = None  # provenance for credibility judging


class EmotionDelta(BaseModel):
    """FR-2: LLM-returned emotion delta across the 5 axes (D3).

    fear/greed feed the price/state formula; the extra three axes (confidence,
    excitement, trust) are surfaced in the 감정 탭 and nudged by the same stimuli.
    """

    fear_delta: float = 0.0
    greed_delta: float = 0.0
    confidence_delta: float = 0.0
    excitement_delta: float = 0.0
    trust_delta: float = 0.0


# --------------------------------------------------------------------------- #
# Trading & price
# --------------------------------------------------------------------------- #
class TradeDecision(BaseModel):
    agent_id: str
    action: Action = Action.HOLD
    symbol: str | None = None
    qty: float = 0.0
    reason: str = ""


class TradeResult(BaseModel):
    agent_id: str
    action: Action
    symbol: str | None = None
    qty: float = 0.0
    price: float = 0.0
    cash_after: float = 0.0
    realized_pnl: float = 0.0   # §6.5.4 매도로 확정된 손익 = (P − avg_cost) × q


class TradeLog(BaseModel):
    """N2.1: 클론/에이전트 매매 로그 (초반 vs 후반 행동 비교용)."""

    uid: str = ""
    round: int = 0
    act: int = 1
    agent_id: str
    action: str
    symbol: str | None = None
    qty: float = 0.0
    price: float = 0.0
    market_situation: str = ""      # crash/surge/sideways/rumor/recovery
    fear: float = 50.0
    greed: float = 50.0


class InterventionLog(BaseModel):
    """N2.1: 플레이어 개입 로그 (학습 측정의 핵심 데이터)."""

    uid: str = ""
    round: int = 0
    act: int = 1
    market_situation: str = ""
    cell_key: str = ""
    choice_label: str | None = None
    choice_tag: str | None = None   # 침착_유도/공포_동조/...
    free_text: str | None = None    # 결정적 순간 한마디
    resolved: bool = False          # 먹힘/씹힘
    clone_fear_before: float = 0.0
    clone_fear_after: float = 0.0
    timestamp: str = ""


# --------------------------------------------------------------------------- #
# Aggregate market indices (FE MarketData shape)
# --------------------------------------------------------------------------- #
class SentimentContribution(BaseModel):
    agent: str
    value: float


class MarketData(BaseModel):
    """Mirrors frontend MarketData (mock_data/market.ts)."""

    assets: list[Asset] = Field(default_factory=list)
    fearGreedIndex: float = 50.0
    rumorSpeed: float = 0.0
    panicSellRatio: float = 0.0
    fomoBuyRatio: float = 0.0
    whaleBuyIntensity: float = 0.0
    whaleSellIntensity: float = 0.0
    sentimentContribution: list[SentimentContribution] = Field(default_factory=list)
