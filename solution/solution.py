"""Submission entry point for the completed Day 14 evaluation core.

The implementation remains in ``template.py`` so the supplied artifact adapter
continues to import the same module during the lab. Re-exporting the public
API here gives the test suite and the submission folder one authoritative,
non-duplicated implementation.
"""

from template import (
    BenchmarkRunner,
    EvalResult,
    FailureAnalyzer,
    LLMJudge,
    QAPair,
    RAGASEvaluator,
    rerank_by_overlap,
)

__all__ = [
    "BenchmarkRunner",
    "EvalResult",
    "FailureAnalyzer",
    "LLMJudge",
    "QAPair",
    "RAGASEvaluator",
    "rerank_by_overlap",
]
