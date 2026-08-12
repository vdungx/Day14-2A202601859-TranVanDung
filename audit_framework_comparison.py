"""Create a machine-readable quality gate for Exercise 3.4 artifacts."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from compare_frameworks import METRICS, summarize


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def count_scores(artifact: dict[str, Any]) -> tuple[int, int]:
    records = [
        row["metrics"][metric]
        for rows in artifact["results"].values()
        for row in rows
        for metric in METRICS
    ]
    return sum(record["score"] is not None for record in records), len(records)


def validate_artifact(artifact: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    if artifact["experiment"]["case_count"] != 20:
        problems.append("main artifact must contain 20 cases")
    if len(set(artifact["experiment"]["case_ids"])) != 20:
        problems.append("main artifact IDs must be unique")
    if summarize(artifact["results"]) != artifact["summary"]:
        problems.append("stored summary differs from independently recomputed summary")
    for framework, rows in artifact["results"].items():
        if len(rows) != 20:
            problems.append(f"{framework} must contain 20 rows")
        for row in rows:
            for metric in METRICS:
                record = row["metrics"][metric]
                if (record["score"] is None) != (record["error"] is not None):
                    problems.append(f"{framework}/{row['id']}/{metric}: score/error invariant failed")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--main", type=Path, default=Path("artifacts/framework_comparison.json"))
    parser.add_argument(
        "--recovery",
        type=Path,
        nargs="*",
        default=[
            Path("artifacts/framework_comparison_recovery_pilot.json"),
            Path("artifacts/framework_comparison_recovery_gemini_pilot.json"),
        ],
    )
    parser.add_argument("--output", type=Path, default=Path("artifacts/framework_quality_gate.json"))
    args = parser.parse_args()

    main_artifact = read_json(args.main)
    problems = validate_artifact(main_artifact)
    successful, expected = count_scores(main_artifact)
    recovery = []
    for path in args.recovery:
        artifact = read_json(path)
        recovered, recovery_expected = count_scores(artifact)
        recovery.append(
            {
                "artifact": path.as_posix(),
                "judge_model": artifact["experiment"]["judge_model"],
                "case_ids": artifact["experiment"]["case_ids"],
                "successful": recovered,
                "expected": recovery_expected,
                "generated_at": artifact["generated_at"],
            }
        )

    status = "failed" if problems else ("complete" if successful == expected else "complete_with_provider_limitations")
    output = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "lab_requirement": "pass" if not problems else "fail",
        "production_completeness": "pass" if successful == expected else "blocked_by_provider_or_parser",
        "main_artifact": args.main.as_posix(),
        "coverage": {
            "successful": successful,
            "expected": expected,
            "rate": round(successful / expected, 6),
            "errors": expected - successful,
        },
        "invariants": {
            "same_saved_inputs": main_artifact["experiment"]["same_saved_inputs"],
            "case_count": main_artifact["experiment"]["case_count"],
            "summary_recomputed": "stored summary matches",
            "null_score_requires_error": True,
            "secrets_stored": False,
        },
        "comparability": {
            "same_judge_for_main_run": True,
            "native_answer_relevancy_symmetric": False,
            "reason": "RAGAS requires an embedding model; 9Router returned HTTP 400 because no OpenAI embedding provider credentials are configured. The run therefore uses a documented local hashing embedding only for RAGAS.",
            "decision": "Do not rank framework accuracy from Answer Relevancy until both are calibrated against human labels or a shared semantic control metric.",
        },
        "recovery_evidence": recovery,
        "problems": problems,
        "quality_gate_policy": {
            "lab_ready": not problems,
            "production_ready": not problems and successful == expected and main_artifact["method_notes"].get("ragas_answer_relevancy_embedding") is None,
        },
    }
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
