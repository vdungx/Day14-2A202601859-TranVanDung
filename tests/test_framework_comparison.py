import json
from pathlib import Path

from compare_frameworks import METRICS, load_cases, summarize


ROOT = Path(__file__).resolve().parents[1]


def test_framework_inputs_join_all_saved_cases():
    cases = load_cases(ROOT / "golden_dataset.json", ROOT / "artifacts" / "actual_answers.json")
    assert len(cases) == 20
    assert len({case["id"] for case in cases}) == 20
    assert all(1 <= len(case["retrieved_contexts"]) <= 5 for case in cases)
    assert {case["id"]: len(case["retrieved_contexts"]) for case in cases}["E02"] == 2


def test_framework_artifact_has_auditable_scores_and_errors():
    artifact = json.loads((ROOT / "artifacts" / "framework_comparison.json").read_text(encoding="utf-8"))
    assert artifact["experiment"]["case_count"] == 20
    assert set(artifact["results"]) == {"ragas", "deepeval"}
    for rows in artifact["results"].values():
        assert len(rows) == 20
        for row in rows:
            assert set(row["metrics"]) == set(METRICS)
            for record in row["metrics"].values():
                assert (record["score"] is None) == (record["error"] is not None)
                if record["score"] is not None:
                    assert 0 <= record["score"] <= 1


def test_committed_framework_summary_is_recomputable():
    artifact = json.loads((ROOT / "artifacts" / "framework_comparison.json").read_text(encoding="utf-8"))
    assert summarize(artifact["results"]) == artifact["summary"]
    successful = sum(
        metric["successful"]
        for framework in ("ragas", "deepeval")
        for metric in artifact["summary"][framework].values()
    )
    assert successful == 151


def test_quality_gate_distinguishes_lab_completion_from_production_readiness():
    gate = json.loads((ROOT / "artifacts" / "framework_quality_gate.json").read_text(encoding="utf-8"))
    assert gate["status"] == "complete_with_provider_limitations"
    assert gate["lab_requirement"] == "pass"
    assert gate["production_completeness"] == "blocked_by_provider_or_parser"
    assert gate["coverage"] == {"successful": 151, "expected": 160, "rate": 0.94375, "errors": 9}
    assert gate["quality_gate_policy"] == {"lab_ready": True, "production_ready": False}
