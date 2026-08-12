"""Run Exercise 3.4 on identical saved RAG inputs with RAGAS and DeepEval.

The script is deliberately separate from the lab's required evaluation core.  It
reads the committed inference trace, never regenerates answers, and records every
metric error instead of substituting a score.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
import re
import sys
import time
import types
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

from dotenv import load_dotenv


METRICS = ("faithfulness", "answer_relevancy", "context_recall", "context_precision")


def _read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def load_cases(golden_path: Path, actual_path: Path) -> list[dict[str, Any]]:
    golden = _read_object(golden_path)
    actual = _read_object(actual_path)
    if golden.get("corpus_id") != actual.get("corpus_id"):
        raise ValueError("Golden dataset and actual answers use different corpus_id")
    actual_by_id = {row["id"]: row for row in actual["answers"]}
    cases: list[dict[str, Any]] = []
    for row in golden["qa_pairs"]:
        observed = actual_by_id.get(row["id"])
        if observed is None:
            raise ValueError(f"Missing actual answer for {row['id']}")
        if observed.get("question") != row["question"]:
            raise ValueError(f"Question mismatch for {row['id']}")
        if observed.get("error") is not None:
            raise ValueError(f"Inference error for {row['id']}: {observed['error']}")
        contexts = [item["text"].strip() for item in observed["retrieved_contexts"]]
        if not contexts:
            raise ValueError(f"No retrieved contexts for {row['id']}")
        cases.append(
            {
                "id": row["id"],
                "difficulty": row["difficulty"],
                "question": row["question"],
                "expected_answer": row["expected_answer"],
                "actual_answer": observed["actual_answer"],
                "retrieved_contexts": contexts,
            }
        )
    if len(actual_by_id) != len(cases):
        raise ValueError("Actual-answer artifact contains IDs outside the golden dataset")
    return cases


def _install_ragas_vertex_compatibility_shim() -> bool:
    """Bridge a removed optional LangChain import used by RAGAS 0.4.3.

    Vertex AI is not used in this experiment. RAGAS imports ChatVertexAI eagerly,
    while langchain-community 0.4.2 removed that legacy module path.
    """

    module_name = "langchain_community.chat_models.vertexai"
    try:
        __import__(module_name)
        return False
    except ModuleNotFoundError:
        module = types.ModuleType(module_name)

        class ChatVertexAI:  # pragma: no cover - import-only compatibility symbol
            pass

        module.ChatVertexAI = ChatVertexAI
        sys.modules[module_name] = module
        return True


class HashingEmbedding:
    """Deterministic local token/trigram embedding for RAGAS AnswerRelevancy.

    This avoids introducing a second remote embedding provider. It is explicitly
    reported as a methodological limitation in the output artifact.
    """

    dimensions = 1024

    @staticmethod
    def _features(text: str) -> list[str]:
        tokens = re.findall(r"[a-z0-9]+", text.lower())
        features = list(tokens)
        features.extend(" ".join(tokens[i : i + 2]) for i in range(len(tokens) - 1))
        return features

    def embed_text(self, text: str, **_: Any) -> list[float]:
        vector = [0.0] * self.dimensions
        for feature in self._features(text):
            digest = hashlib.sha256(feature.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] & 1 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

    async def aembed_text(self, text: str, **kwargs: Any) -> list[float]:
        return self.embed_text(text, **kwargs)

    async def aembed_texts(self, texts: list[str], **kwargs: Any) -> list[list[float]]:
        return [self.embed_text(text, **kwargs) for text in texts]


def _metric_record(started: float, score: Any = None, reason: Any = None, error: Exception | None = None) -> dict[str, Any]:
    value: float | None = None
    if error is None:
        try:
            candidate = float(score)
            value = candidate if math.isfinite(candidate) else None
            if value is None:
                error = ValueError(f"non-finite score: {candidate}")
        except (TypeError, ValueError) as exc:
            error = exc
    return {
        "score": value,
        "reason": str(reason) if reason else None,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "error": None if error is None else f"{type(error).__name__}: {error}",
    }


async def run_ragas(cases: list[dict[str, Any]], model: str, api_key: str, base_url: str, max_concurrency: int, metric_filter: dict[str, set[str]] | None = None) -> tuple[list[dict[str, Any]], bool]:
    shim_used = _install_ragas_vertex_compatibility_shim()
    from openai import AsyncOpenAI
    from ragas.embeddings.base import BaseRagasEmbedding
    from ragas.llms.base import llm_factory
    from ragas.metrics.collections import (
        AnswerRelevancy,
        ContextPrecisionWithReference,
        ContextRecall,
        Faithfulness,
    )

    class RagasHashingEmbedding(HashingEmbedding, BaseRagasEmbedding):
        """Expose the documented local implementation through RAGAS's modern API."""

        def __init__(self) -> None:
            BaseRagasEmbedding.__init__(self)

    client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=90.0, max_retries=1)
    judge = llm_factory(model, client=client, temperature=0)
    metrics = {
        "faithfulness": Faithfulness(llm=judge),
        "answer_relevancy": AnswerRelevancy(llm=judge, embeddings=RagasHashingEmbedding(), strictness=1),
        "context_recall": ContextRecall(llm=judge),
        "context_precision": ContextPrecisionWithReference(llm=judge),
    }
    semaphore = asyncio.Semaphore(max_concurrency)

    async def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
        async with semaphore:
            result = {"id": case["id"], "difficulty": case["difficulty"], "metrics": {}}
            calls = {
                "faithfulness": dict(user_input=case["question"], response=case["actual_answer"], retrieved_contexts=case["retrieved_contexts"]),
                "answer_relevancy": dict(user_input=case["question"], response=case["actual_answer"]),
                "context_recall": dict(user_input=case["question"], reference=case["expected_answer"], retrieved_contexts=case["retrieved_contexts"]),
                "context_precision": dict(user_input=case["question"], reference=case["expected_answer"], retrieved_contexts=case["retrieved_contexts"]),
            }
            for name, metric in metrics.items():
                if metric_filter is not None and name not in metric_filter.get(case["id"], set()):
                    continue
                started = time.perf_counter()
                try:
                    score = await metric.ascore(**calls[name])
                    result["metrics"][name] = _metric_record(started, score.value, score.reason)
                except Exception as exc:  # preserve framework/provider failures as evidence
                    result["metrics"][name] = _metric_record(started, error=exc)
            print(f"RAGAS complete: {case['id']}", flush=True)
            return result

    try:
        completed = await asyncio.gather(*(evaluate_case(case) for case in cases))
    finally:
        await client.close()
    by_id = {row["id"]: row for row in completed}
    return [by_id[case["id"]] for case in cases], shim_used


def run_deepeval(cases: list[dict[str, Any]], model: str, api_key: str, base_url: str, max_concurrency: int, metric_filter: dict[str, set[str]] | None = None) -> list[dict[str, Any]]:
    os.environ.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT", "1")
    from deepeval.metrics import (
        AnswerRelevancyMetric,
        ContextualPrecisionMetric,
        ContextualRecallMetric,
        FaithfulnessMetric,
    )
    from deepeval.models import OpenAIModel
    from deepeval.test_case import LLMTestCase

    judge = OpenAIModel(
        model=model,
        api_key=api_key,
        base_url=base_url,
        temperature=0,
        cost_per_input_token=0,
        cost_per_output_token=0,
    )
    classes = {
        "faithfulness": FaithfulnessMetric,
        "answer_relevancy": AnswerRelevancyMetric,
        "context_recall": ContextualRecallMetric,
        "context_precision": ContextualPrecisionMetric,
    }
    def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
        test_case = LLMTestCase(
            input=case["question"],
            actual_output=case["actual_answer"],
            expected_output=case["expected_answer"],
            retrieval_context=case["retrieved_contexts"],
        )
        result = {"id": case["id"], "difficulty": case["difficulty"], "metrics": {}}
        for name, metric_class in classes.items():
            if metric_filter is not None and name not in metric_filter.get(case["id"], set()):
                continue
            started = time.perf_counter()
            try:
                metric = metric_class(model=judge, include_reason=True, async_mode=False)
                score = metric.measure(test_case, _show_indicator=False)
                result["metrics"][name] = _metric_record(started, score, metric.reason)
            except Exception as exc:  # preserve framework/provider failures as evidence
                result["metrics"][name] = _metric_record(started, error=exc)
        print(f"DeepEval complete: {case['id']}", flush=True)
        return result

    completed: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=max_concurrency) as executor:
        futures = {executor.submit(evaluate_case, case): case["id"] for case in cases}
        for future in as_completed(futures):
            completed[futures[future]] = future.result()
    return [completed[case["id"]] for case in cases]


def summarize(framework_rows: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for framework, rows in framework_rows.items():
        metric_summary: dict[str, Any] = {}
        for name in METRICS:
            records = [row["metrics"][name] for row in rows]
            scores = [record["score"] for record in records if record["score"] is not None]
            metric_summary[name] = {
                "mean": round(mean(scores), 6) if scores else None,
                "successful": len(scores),
                "errors": len(records) - len(scores),
                "mean_elapsed_seconds": round(mean(record["elapsed_seconds"] for record in records), 3),
                "failure_ids_below_0_5": [row["id"] for row in rows if row["metrics"][name]["score"] is not None and row["metrics"][name]["score"] < 0.5],
            }
        summary[framework] = metric_summary

    agreement: dict[str, Any] = {}
    if set(framework_rows) == {"ragas", "deepeval"}:
        ragas_by_id = {row["id"]: row for row in framework_rows["ragas"]}
        deep_by_id = {row["id"]: row for row in framework_rows["deepeval"]}
        for name in METRICS:
            pairs = []
            same_failure = 0
            for case_id in ragas_by_id:
                left = ragas_by_id[case_id]["metrics"][name]["score"]
                right = deep_by_id[case_id]["metrics"][name]["score"]
                if left is not None and right is not None:
                    pairs.append((left, right))
                    same_failure += int((left < 0.5) == (right < 0.5))
            agreement[name] = {
                "comparable_cases": len(pairs),
                "mean_absolute_difference": round(mean(abs(a - b) for a, b in pairs), 6) if pairs else None,
                "same_side_of_0_5": same_failure,
                "agreement_rate": round(same_failure / len(pairs), 6) if pairs else None,
            }
    summary["cross_framework_agreement"] = agreement
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--golden", type=Path, default=Path("golden_dataset.json"))
    parser.add_argument("--actual", type=Path, default=Path("artifacts/actual_answers.json"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/framework_comparison.json"))
    parser.add_argument("--ids", nargs="*", help="Optional case IDs for a pilot run")
    parser.add_argument("--framework", choices=("both", "ragas", "deepeval"), default="both")
    parser.add_argument("--max-concurrency", type=int, default=3)
    parser.add_argument("--resume-from", type=Path, help="Retry only null/error metrics from an existing full artifact")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    model = os.getenv("OPENAI_MODEL")
    if not api_key or not base_url or not model:
        raise SystemExit("OPENAI_API_KEY, OPENAI_BASE_URL, and OPENAI_MODEL are required")
    all_cases = load_cases(args.golden, args.actual)
    cases = all_cases
    if args.max_concurrency < 1 or args.max_concurrency > 8:
        raise SystemExit("--max-concurrency must be between 1 and 8")
    if args.ids:
        selected = set(args.ids)
        cases = [case for case in cases if case["id"] in selected]
        missing = selected - {case["id"] for case in cases}
        if missing:
            raise SystemExit("Unknown IDs: " + ", ".join(sorted(missing)))

    resume_artifact: dict[str, Any] | None = None
    retry_metrics: dict[str, dict[str, set[str]]] = {"ragas": {}, "deepeval": {}}
    if args.resume_from:
        if args.ids:
            raise SystemExit("--resume-from cannot be combined with --ids")
        resume_artifact = _read_object(args.resume_from)
        old_results = resume_artifact.get("results", {})
        requested = ("ragas", "deepeval") if args.framework == "both" else (args.framework,)
        retry_ids: set[str] = set()
        for framework in requested:
            for row in old_results.get(framework, []):
                failed = {name for name in METRICS if row["metrics"][name]["score"] is None}
                if failed:
                    retry_ids.add(row["id"])
                    retry_metrics[framework][row["id"]] = failed
        cases = [case for case in all_cases if case["id"] in retry_ids]
        if not cases:
            raise SystemExit("No failed metrics to resume")
        print("Retrying failed metrics for: " + ", ".join(case["id"] for case in cases), flush=True)

    started = time.perf_counter()
    framework_rows: dict[str, list[dict[str, Any]]] = {}
    shim_used = False
    if args.framework in {"both", "ragas"}:
        framework_rows["ragas"], shim_used = asyncio.run(run_ragas(cases, model, api_key, base_url, args.max_concurrency, retry_metrics["ragas"] if resume_artifact else None))
    if args.framework in {"both", "deepeval"}:
        framework_rows["deepeval"] = run_deepeval(cases, model, api_key, base_url, args.max_concurrency, retry_metrics["deepeval"] if resume_artifact else None)

    if resume_artifact is not None:
        merged_results = resume_artifact["results"]
        for framework, fresh_rows in framework_rows.items():
            old_by_id = {row["id"]: row for row in merged_results[framework]}
            for fresh in fresh_rows:
                old = old_by_id[fresh["id"]]
                for name in METRICS:
                    if old["metrics"][name]["score"] is None and name in fresh["metrics"]:
                        old["metrics"][name] = fresh["metrics"][name]
        framework_rows = merged_results
    import importlib.metadata

    artifact = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "experiment": {
            "case_count": len(all_cases) if resume_artifact is not None else len(cases),
            "case_ids": [case["id"] for case in (all_cases if resume_artifact is not None else cases)],
            "same_saved_inputs": True,
            "judge_model": model,
            "base_url": base_url,
            "temperature": 0,
            "threshold_for_failure_comparison": 0.5,
            "max_concurrency": args.max_concurrency,
            "resumed_from": str(args.resume_from) if args.resume_from else None,
            "retry_case_count": len(cases) if resume_artifact is not None else 0,
            "elapsed_seconds": round(time.perf_counter() - started, 3),
        },
        "versions": {
            "python": sys.version.split()[0],
            "ragas": importlib.metadata.version("ragas"),
            "deepeval": importlib.metadata.version("deepeval"),
            "openai": importlib.metadata.version("openai"),
        },
        "method_notes": {
            "retrieval_context": "The exact retrieved_contexts saved in artifacts/actual_answers.json (2-5 contexts per case; no padding).",
            "reference": "expected_answer from golden_dataset.json for both context metrics.",
            "ragas_answer_relevancy_embedding": "Deterministic local 1024-dimensional signed hashing of tokens and bigrams; no remote embedding model was available through the configured 9Router endpoint.",
            "ragas_vertex_import_shim_used": shim_used,
            "ragas_vertex_import_shim_scope": "Import-only symbol; Vertex AI is not instantiated or used.",
            "errors": "A null score always has a non-null error; no score is imputed.",
        },
        "results": framework_rows,
        "summary": summarize(framework_rows),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(artifact["summary"], ensure_ascii=False, indent=2))
    print(f"Saved evidence: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
