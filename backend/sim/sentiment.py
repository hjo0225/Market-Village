"""Shared sentiment classifier — KR-FinBert-SC model + keyword fallback.

Single source of truth for event sentiment. Used by engine.py and llm.py.
"""

from __future__ import annotations

import os
import threading

from .models import EventImpact

_pipeline = None
_lock = threading.Lock()


def _get_pipeline():
    global _pipeline
    if _pipeline is not None:
        return _pipeline if _pipeline else None
    with _lock:
        if _pipeline is not None:
            return _pipeline if _pipeline else None
        try:
            # Skip network checks after first download — saves ~1.5s per call
            os.environ.setdefault("HF_HUB_OFFLINE", "1")
            from transformers import pipeline
            try:
                _pipeline = pipeline(
                    "text-classification", model="snunlp/KR-FinBert-SC",
                    local_files_only=True,
                )
            except OSError:
                # First run: download the model
                os.environ.pop("HF_HUB_OFFLINE", None)
                _pipeline = pipeline(
                    "text-classification", model="snunlp/KR-FinBert-SC",
                )
        except Exception:
            _pipeline = False
    return _pipeline if _pipeline else None


_LABEL_MAP = {
    "negative": EventImpact.NEGATIVE,
    "positive": EventImpact.POSITIVE,
    "neutral": EventImpact.NEUTRAL,
}

_NEG_KW = {"해킹", "폭락", "규제", "관세", "전쟁", "급락", "공포", "파산",
           "악재", "악제", "장애", "중단", "다운", "소송", "유출",
           "하락", "떨어", "약세", "손실", "적자", "실패"}
_POS_KW = {"승인", "상승", "호재", "급등", "유입", "인하", "etf"}


def _keyword_fallback(text: str) -> EventImpact | None:
    low = text.lower()
    if any(k in low for k in _NEG_KW):
        return EventImpact.NEGATIVE
    if any(k in low for k in _POS_KW):
        return EventImpact.POSITIVE
    return None


def classify_impact(text: str) -> EventImpact:
    """KR-FinBert-SC first, keyword fallback for short/ambiguous inputs."""
    pipe = _get_pipeline()
    if pipe is not None:
        try:
            result = pipe(text[:512])[0]
            if result["score"] >= 0.75 and result["label"] != "neutral":
                return _LABEL_MAP[result["label"]]
        except Exception:
            pass
    return _keyword_fallback(text) or EventImpact.NEUTRAL


def is_negative(text: str) -> bool:
    """Convenience for scripted client sentiment direction."""
    return classify_impact(text) == EventImpact.NEGATIVE
