"""Smoke evaluation for Learning Loop datasets (outside AI Core prompts)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class EvaluationCase:
    case_id: str
    question: str
    expected_intent: str | None = None
    expected_handoff: bool | None = None
    expected_sources: list[str] = field(default_factory=list)
    allow_price_without_live: bool = False
    notes: str | None = None


@dataclass(slots=True)
class EvaluationMetrics:
    total: int = 0
    intent_correct: int = 0
    source_correct: int = 0
    handoff_correct: int = 0
    hallucination_flags: int = 0
    validator_pass: int = 0
    dynamic_fact_safe: int = 0

    @property
    def intent_accuracy(self) -> float:
        return self.intent_correct / self.total if self.total else 0.0

    @property
    def correct_source_usage(self) -> float:
        return self.source_correct / self.total if self.total else 0.0

    @property
    def correct_handoff(self) -> float:
        return self.handoff_correct / self.total if self.total else 0.0

    @property
    def hallucination_rate(self) -> float:
        return self.hallucination_flags / self.total if self.total else 0.0

    @property
    def validator_pass_rate(self) -> float:
        return self.validator_pass / self.total if self.total else 0.0

    @property
    def dynamic_fact_safety(self) -> float:
        return self.dynamic_fact_safe / self.total if self.total else 0.0

    def as_dict(self) -> dict[str, float | int]:
        return {
            "total": self.total,
            "intent_accuracy": self.intent_accuracy,
            "correct_source_usage": self.correct_source_usage,
            "correct_handoff": self.correct_handoff,
            "hallucination_rate": self.hallucination_rate,
            "validator_pass_rate": self.validator_pass_rate,
            "dynamic_fact_safety": self.dynamic_fact_safety,
        }


def load_jsonl_cases(path: Path | str) -> list[EvaluationCase]:
    file_path = Path(path)
    cases: list[EvaluationCase] = []
    for line in file_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        raw: dict[str, Any] = json.loads(line)
        cases.append(
            EvaluationCase(
                case_id=str(raw.get("id") or raw.get("case_id") or f"case-{len(cases)+1}"),
                question=str(raw.get("question") or ""),
                expected_intent=raw.get("expected_intent") or raw.get("intent"),
                expected_handoff=raw.get("expected_handoff"),
                expected_sources=list(raw.get("expected_sources") or []),
                allow_price_without_live=bool(raw.get("allow_price_without_live", False)),
                notes=raw.get("notes"),
            )
        )
    return cases


def _infer_intent(question: str) -> str:
    text = question.lower()
    if any(token in text for token in ("цена", "стоит", "сколько")):
        return "price"
    if any(token in text for token in ("наличие", "остаток", "в наличии")):
        return "stock"
    if any(token in text for token in ("доставк", "самовывоз")):
        return "delivery"
    if any(token in text for token in ("оплат", "безнал", "по карте", "картой")) or (
        "карт" in text and "картридж" not in text
    ):
        return "payment"
    return "general"


def _has_live_source(sources: list[str]) -> bool:
    joined = " ".join(sources).lower()
    return any(token in joined for token in ("bitrix", "live", "website_api", "catalog"))


def evaluate_case(
    case: EvaluationCase,
    *,
    predicted_intent: str | None = None,
    used_sources: list[str] | None = None,
    did_handoff: bool | None = None,
    response_text: str | None = None,
    validator_ok: bool | None = None,
) -> dict[str, bool]:
    """Rule-based smoke checks for one evaluation case."""
    sources = list(used_sources or [])
    intent = predicted_intent or _infer_intent(case.question)
    response = (response_text or "").lower()

    intent_ok = True
    if case.expected_intent:
        intent_ok = intent.strip().lower() == case.expected_intent.strip().lower()

    source_ok = True
    if case.expected_sources:
        source_ok = all(
            any(exp.lower() in src.lower() for src in sources)
            for exp in case.expected_sources
        )

    handoff_ok = True
    if case.expected_handoff is not None and did_handoff is not None:
        handoff_ok = bool(did_handoff) == bool(case.expected_handoff)

    looks_like_price = any(token in response for token in ("₽", "руб", "цена:"))
    hallucination = looks_like_price and not _has_live_source(sources) and not case.allow_price_without_live

    dynamic_safe = True
    if intent in {"price", "stock"} and not case.allow_price_without_live:
        # Without live source: must handoff / avoid inventing numbers
        if _has_live_source(sources):
            dynamic_safe = True
        else:
            dynamic_safe = (did_handoff is True) or (not looks_like_price)

    validator_passed = True if validator_ok is None else bool(validator_ok)

    return {
        "intent_ok": intent_ok,
        "source_ok": source_ok,
        "handoff_ok": handoff_ok,
        "hallucination": hallucination,
        "validator_ok": validator_passed,
        "dynamic_fact_safe": dynamic_safe,
    }


def run_smoke_evaluation(
    cases: list[EvaluationCase],
    *,
    predictions: dict[str, dict[str, Any]] | None = None,
) -> EvaluationMetrics:
    """Aggregate metrics. Predictions map case_id -> optional fields for evaluate_case."""
    metrics = EvaluationMetrics()
    predictions = predictions or {}
    for case in cases:
        pred = predictions.get(case.case_id, {})
        result = evaluate_case(
            case,
            predicted_intent=pred.get("predicted_intent"),
            used_sources=pred.get("used_sources"),
            did_handoff=pred.get("did_handoff"),
            response_text=pred.get("response_text"),
            validator_ok=pred.get("validator_ok"),
        )
        metrics.total += 1
        if result["intent_ok"]:
            metrics.intent_correct += 1
        if result["source_ok"]:
            metrics.source_correct += 1
        if result["handoff_ok"]:
            metrics.handoff_correct += 1
        if result["hallucination"]:
            metrics.hallucination_flags += 1
        if result["validator_ok"]:
            metrics.validator_pass += 1
        if result["dynamic_fact_safe"]:
            metrics.dynamic_fact_safe += 1
    return metrics


def run_evaluation_file(path: Path | str) -> EvaluationMetrics:
    cases = load_jsonl_cases(path)
    # Default smoke: infer intent from question; assume safe handoff for price/stock without live.
    predictions: dict[str, dict[str, Any]] = {}
    for case in cases:
        intent = _infer_intent(case.question)
        did_handoff = intent in {"price", "stock"}
        predictions[case.case_id] = {
            "predicted_intent": intent,
            "used_sources": [],
            "did_handoff": did_handoff,
            "response_text": "Уточните модель" if did_handoff else "Ответ по FAQ",
            "validator_ok": True,
        }
    return run_smoke_evaluation(cases, predictions=predictions)

