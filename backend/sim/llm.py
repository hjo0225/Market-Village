"""LLM client wrapper for the simulation.

Design goals:
- Mockable: every FR module takes an ``LLMClient`` argument; tests inject a
  ``FakeLLM`` so the whole round is deterministic with the LLM mocked
  (PRD §2.3 / test_round_reproducible_with_mocked_llm).
- Robust: ``safe_json`` never raises — on any failure the caller's fallback is
  returned and the loop continues (PRD §2.4 fallback assertion).
- Secure: the API key comes from the OPENROUTER_API_KEY env var, never
  hardcoded. (The legacy hardcoded key in the reverie fork must be rotated.)

Chat uses the OpenAI SDK with the key the user put in the project's .env. That
key (stored under OPENROUTER_API_KEY, but it is actually a plain OpenAI key) is
loaded with override=True so the project's .env WINS over any ambient OS
OPENAI_API_KEY. We call the OpenAI API directly (default base) with a native
model id. Embeddings are intentionally out of scope here.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Callable

# Load the project's .env with override so the key the user put there beats any
# ambient OS environment variable. Tests set MARKET_DISABLE_LLM=1 (conftest) to
# skip this and stay hermetic/offline.
if not os.getenv("MARKET_DISABLE_LLM"):
    try:
        from dotenv import load_dotenv
        _sim_dir = Path(__file__).resolve().parents[2]
        # Try project root first, then backend/
        load_dotenv(_sim_dir / ".env", override=True)
        load_dotenv(_sim_dir / "backend" / ".env", override=True)
    except Exception:
        pass


def _native_model(raw: str) -> str:
    """OpenAI direct API wants a bare model id (strip any 'openai/' prefix)."""
    return raw.split("/", 1)[1] if raw.startswith("openai/") else raw


# The key may be an OpenRouter key (sk-or-...) or a plain OpenAI key (sk-...).
# Auto-route by prefix so whichever the user provides just works:
#   sk-or*  -> OpenRouter base + namespaced model id (e.g. "openai/gpt-4o-mini")
#   else    -> OpenAI direct base + native model id (e.g. "gpt-4o-mini")
_KEY = os.getenv("OPENROUTER_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")
_IS_OPENROUTER = _KEY.startswith("sk-or")

if _IS_OPENROUTER:
    DEFAULT_BASE_URL = os.getenv("OPENROUTER_API_BASE", "https://openrouter.ai/api/v1")
    DEFAULT_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini") or "openai/gpt-4o-mini"
else:
    DEFAULT_BASE_URL = os.getenv("OPENAI_BASE_URL") or None
    DEFAULT_MODEL = _native_model(
        os.getenv("OPENAI_MODEL") or os.getenv("OPENROUTER_MODEL") or "gpt-4o-mini"
    )


class LLMError(RuntimeError):
    pass


class LLMClient:
    """Thin chat client: OpenAI SDK -> OpenRouter base_url, OpenRouter key from
    .env. Lazy-imports openai so tests need no network and no key."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 30.0,
        base_url: str | None = None,
    ):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")
        self.model = model or DEFAULT_MODEL
        self.base_url = base_url or DEFAULT_BASE_URL
        self.timeout = timeout
        self._client = None

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def chat(self, user: str, system: str | None = None, temperature: float = 0.7) -> str:
        if not self.available:
            raise LLMError("OPENROUTER_API_KEY not set")
        try:
            if self._client is None:
                from openai import OpenAI  # lazy import
                self._client = OpenAI(
                    api_key=self.api_key, base_url=self.base_url, timeout=self.timeout
                )
            messages: list[dict[str, str]] = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": user})
            resp = self._client.chat.completions.create(
                model=self.model, messages=messages, temperature=temperature
            )
            return resp.choices[0].message.content
        except Exception as exc:  # noqa: BLE001 - any failure -> LLMError -> fallback
            raise LLMError(str(exc)) from exc


class FakeLLM(LLMClient):
    """Deterministic test/offline double.

    Pass either a ``response`` string, a list of responses (consumed in order),
    or a ``handler`` callable(user, system) -> str for context-aware replies.
    """

    def __init__(
        self,
        response: str | list[str] | None = None,
        handler: Callable[[str, str | None], str] | None = None,
    ):
        super().__init__(api_key="fake", model="fake")
        self._response = response
        self._handler = handler
        self._queue = list(response) if isinstance(response, list) else None
        self.calls: list[tuple[str, str | None]] = []

    @property
    def available(self) -> bool:
        return True

    def chat(self, user: str, system: str | None = None, temperature: float = 0.7) -> str:
        self.calls.append((user, system))
        if self._handler is not None:
            return self._handler(user, system)
        if self._queue is not None:
            return self._queue.pop(0) if self._queue else "{}"
        if isinstance(self._response, str):
            return self._response
        return "{}"


def extract_json(text: str) -> dict[str, Any]:
    """Best-effort: pull the first JSON object out of an LLM response."""
    text = text.strip()
    # strip ```json fences
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    raise ValueError(f"no JSON object in response: {text[:120]!r}")


def safe_json(
    client: LLMClient,
    user: str,
    fallback: dict[str, Any],
    system: str | None = None,
    temperature: float = 0.7,
) -> dict[str, Any]:
    """Call the LLM and parse JSON, returning ``fallback`` on any failure.

    Guarantees the simulation loop never crashes on an LLM hiccup (PRD §2.4).
    """
    try:
        raw = client.chat(user, system=system, temperature=temperature)
        return extract_json(raw)
    except Exception:  # noqa: BLE001
        return dict(fallback)


# Module-level default client (constructed lazily so import never needs a key).
_default: LLMClient | None = None


def default_client() -> LLMClient:
    global _default
    if _default is None:
        _default = LLMClient()
    return _default


# --------------------------------------------------------------------------- #
# Scripted offline client — gives a lively, deterministic demo with no API key.
# It mirrors the LLM JSON contracts so the FR modules behave identically; the
# content is template-flavoured by reading persona/impact keywords in the prompt.
# --------------------------------------------------------------------------- #
def _is_negative(text: str) -> bool:
    from .sentiment import is_negative
    return is_negative(text)


def _agent_type_in_prompt(text: str) -> str:
    """The FR-module persona block renders 'type: <agent_type>'; the first such
    token identifies the current agent unambiguously (feed text has no 'type:')."""
    m = re.search(r"type:\s*([a-z_]+)", text)
    return m.group(1) if m else ""


# Several in-character lines per persona/sentiment so posts vary across rounds.
_POST_POOL: dict[str, dict[str, list[str]]] = {
    "panic_seller": {
        "neg": ["이거 진짜 위험한 거 아니에요? 일단 정리해야 하나...",
                "손절 각인가... 더 떨어지기 전에 던진다",
                "어젯밤부터 불안해서 잠을 못 잤어요",
                "지금이라도 비중 줄여야 할까요 ㅠㅠ"],
        "pos": ["오른다는데 지금 들어가도 되나요?",
                "휴 한숨 돌렸다... 그래도 불안은 여전",
                "반등이 진짜일까요? 못 믿겠어요"],
    },
    "fomo_trader": {
        "neg": ["눌림목인가? 줍줍 타이밍?", "이 정도 빠지면 단타 각인데",
                "공포에 사라던데 지금인가"],
        "pos": ["지금 안 사면 후회한다. 가즈아", "불기둥 간다 풀매수",
                "남들 다 타는데 나만 빠질 순 없지"],
    },
    "conspiracy": {
        "neg": ["이거 그냥 사고 아닙니다. 큰손들이 미리 알고 움직였어요",
                "윗선에서 정보 샌 거 확실합니다", "차트가 말해주잖아요. 작전이에요"],
        "pos": ["이 상승 누가 만들었을까요? 다 계획입니다",
                "개미 털고 올리는 전형적 패턴"],
    },
    "value_investor": {
        "neg": ["근거가 약합니다. 펀더멘탈은 그대로예요.",
                "루머에 과민 반응하는 구간이네요.",
                "공포가 과합니다. 가치는 변하지 않았습니다."],
        "pos": ["과열입니다. 차분히 보죠.", "밸류에이션이 부담스러운 레벨입니다.",
                "기대가 가격에 선반영된 듯합니다."],
    },
    "whale": {
        "neg": ["대중이 공포일 때가 매집 기회죠.", "조용히 담을 구간입니다.",
                "패닉은 길지 않습니다. 물량 받습니다."],
        "pos": ["유동성 흐름을 봅니다.", "과열 구간, 일부 차익 실현 고려.",
                "거시 사이클상 아직 여유 있습니다."],
    },
    "contrarian": {
        "neg": ["다들 파니까 저는 삽니다.", "공포지수 보면 지금이 바닥 근처죠.",
                "역추세 진입 시점입니다."],
        "pos": ["다들 탐욕이면 저는 덜어냅니다.", "환호할 때가 팔 때죠.",
                "군중과 반대로 갑니다."],
    },
    "quant": {
        "neg": ["변동성 확대. 패닉셀 비율이 비정상적으로 높습니다.",
                "지표상 과매도. 단기 반등 확률 상승.",
                "거래량 급증, 추세 전환 신호 감지."],
        "pos": ["신호는 중립. 추세 확인 중.", "모멘텀 약화. 비중 조절 신호.",
                "RSI 과매수권 진입."],
    },
    "news_bot": {
        "neg": ["요약: 악재성 이슈로 변동성 확대. 추이 관찰 필요.",
                "속보 정리: 시장 하방 압력 우세.", "팩트체크: 확인되지 않은 정보 다수."],
        "pos": ["요약: 호재성 이슈로 투자심리 개선.",
                "속보 정리: 매수세 유입 관찰됨.", "핵심: 단기 반등 기대감 확산."],
    },
}


def _persona_post(text: str) -> str:
    t = _agent_type_in_prompt(text)
    sent = "neg" if _is_negative(text) else "pos"
    pool = _POST_POOL.get(t, {}).get(sent) or _POST_POOL.get(t, {}).get("neg")
    if not pool:
        return "시장 분위기가 심상치 않네요." if sent == "neg" else "분위기 나쁘지 않은데요."
    # Vary across rounds: the prompt embeds the (growing) feed, so its hash shifts.
    return pool[hash(text) % len(pool)]


def scripted_client() -> "FakeLLM":
    def handler(user: str, system: str | None) -> str:
        if "fear_delta" in user:
            rumor = "rumor" in user.lower() or "루머" in user
            trust_d = -7 if rumor else 5
            if _is_negative(user):
                return json.dumps({"fear_delta": 9, "greed_delta": -4,
                                   "confidence_delta": -5, "excitement_delta": 7,
                                   "trust_delta": trust_d})
            return json.dumps({"fear_delta": -4, "greed_delta": 8,
                               "confidence_delta": 5, "excitement_delta": 6,
                               "trust_delta": trust_d})
        if "kind" in user:
            # Reactive personas COMMENT on others' posts (populates comment
            # threads); the rest POST their own. If no thread exists yet, the SNS
            # layer downgrades a COMMENT to a POST automatically.
            t = _agent_type_in_prompt(user)
            kind = "COMMENT" if t in ("value_investor", "quant", "contrarian", "news_bot") else "POST"
            return json.dumps(
                {"kind": kind, "text": _persona_post(user), "symbol_tags": ["BTC"]}
            )
        if "score" in user:
            low = user.lower()
            rumor = "rumor" in low or "루머" in user
            skeptical = "skeptical" in low or "analytical" in low
            return json.dumps({"score": 3 if (rumor and skeptical) else 6})
        return "{}"

    return FakeLLM(handler=handler)
