"""T-SVC8(부분) · LLM 과금 방어 3종 — 서버측 마스터 게이트·일일 한도·프롬프트 캐시.

L3 리뷰 지적(2026-07-02): use_llm 쿼리 파라미터는 무인증 GET으로 실과금을 트리거할
수 있다 — 클라이언트 신뢰 금지, 서버 env가 최종 결정권. 한도·캐시는 요금 폭주 방어.
전부 FakeLLM/스텁 — 실호출 0.
"""

from __future__ import annotations

import pytest

from sim import llm as llmmod


class _CountingClient(llmmod.LLMClient):
    """_raw_chat만 스텁 — chat()의 게이트·캐시·한도 래핑은 실제 코드 그대로 탄다."""

    def __init__(self):
        super().__init__(api_key="sk-test", model="test-model")
        self.raw_calls = 0

    def _raw_chat(self, user, system=None, temperature=0.7):
        self.raw_calls += 1
        return f"resp:{user}"


@pytest.fixture(autouse=True)
def _fresh_state(monkeypatch):
    llmmod.reset_llm_guard()                        # 카운터·캐시 초기화(테스트 격리)
    monkeypatch.delenv("MV_ALLOW_LLM", raising=False)
    monkeypatch.delenv("MV_LLM_DAILY_MAX", raising=False)
    yield
    llmmod.reset_llm_guard()


def test_master_gate_blocks_before_any_network(monkeypatch):
    monkeypatch.setenv("MV_ALLOW_LLM", "0")
    c = _CountingClient()
    with pytest.raises(llmmod.LLMError):
        c.chat("hello")
    assert c.raw_calls == 0                          # 네트워크 근처도 안 감


def test_gate_default_allows_when_key_exists():
    c = _CountingClient()
    assert c.chat("hello") == "resp:hello"           # 로컬 현행 동작 보존


def test_daily_budget_exhaustion_raises(monkeypatch):
    monkeypatch.setenv("MV_LLM_DAILY_MAX", "2")
    c = _CountingClient()
    c.chat("a")
    c.chat("b")
    with pytest.raises(llmmod.LLMError):
        c.chat("c")                                  # 3번째 신규 호출은 차단
    assert c.raw_calls == 2


def test_prompt_cache_hits_do_not_consume_budget(monkeypatch):
    monkeypatch.setenv("MV_LLM_DAILY_MAX", "1")
    c = _CountingClient()
    first = c.chat("same", system="s")
    second = c.chat("same", system="s")              # 캐시 — 한도 소진 없음
    assert first == second and c.raw_calls == 1
    with pytest.raises(llmmod.LLMError):
        c.chat("different", system="s")


def test_fakellm_unaffected_by_gate(monkeypatch):
    monkeypatch.setenv("MV_ALLOW_LLM", "0")
    fake = llmmod.FakeLLM(response="ok")
    assert fake.chat("x") == "ok"                    # 테스트 더블은 게이트 무관
