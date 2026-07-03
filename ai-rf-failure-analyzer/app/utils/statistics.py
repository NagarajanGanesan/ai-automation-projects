"""Pandas-backed metric computation.

The parser produces a faithful structural view of a run; this module derives
higher-level analytics (slowest tests, most failure-prone keywords, per-tag
failure rates) that are useful both for the dashboard and as grounding
context for the AI agent.

Pandas is used deliberately here: these aggregations are exactly the kind of
group-by / sort operations it expresses concisely and efficiently.
"""

from __future__ import annotations

from typing import Dict, List

import pandas as pd

from app.models.schemas import ParsedResult


def tests_dataframe(result: ParsedResult) -> pd.DataFrame:
    """Build a tidy DataFrame with one row per test case."""
    rows = [
        {
            "name": t.name,
            "suite": t.suite,
            "status": t.status.value,
            "duration_seconds": t.duration_seconds,
            "tags": t.tags,
            "failing_keyword": t.failing_keyword,
        }
        for t in result.all_tests
    ]
    columns = ["name", "suite", "status", "duration_seconds", "tags", "failing_keyword"]
    return pd.DataFrame(rows, columns=columns)


def slowest_tests(result: ParsedResult, top_n: int = 5) -> List[Dict[str, object]]:
    """Return the ``top_n`` slowest tests by duration."""
    df = tests_dataframe(result)
    if df.empty:
        return []
    top = df.sort_values("duration_seconds", ascending=False).head(top_n)
    return [
        {
            "name": row["name"],
            "suite": row["suite"],
            "duration_seconds": float(row["duration_seconds"]),
            "status": row["status"],
        }
        for _, row in top.iterrows()
    ]


def keyword_failure_counts(result: ParsedResult) -> List[Dict[str, object]]:
    """Count failures grouped by keyword, most frequent first."""
    if not result.keyword_failures:
        return []
    df = pd.DataFrame(
        [
            {"keyword": kw.name, "library": kw.library or "unknown"}
            for kw in result.keyword_failures
        ]
    )
    grouped = (
        df.groupby(["keyword", "library"])
        .size()
        .reset_index(name="failures")
        .sort_values("failures", ascending=False)
    )
    return [
        {
            "keyword": row["keyword"],
            "library": row["library"],
            "failures": int(row["failures"]),
        }
        for _, row in grouped.iterrows()
    ]


def failure_rate_by_tag(result: ParsedResult) -> List[Dict[str, object]]:
    """Compute the failure rate per tag (executed tests only)."""
    df = tests_dataframe(result)
    if df.empty:
        return []
    exploded = df.explode("tags").dropna(subset=["tags"])
    exploded = exploded[exploded["status"].isin(["PASS", "FAIL"])]
    if exploded.empty:
        return []

    def _rate(group: pd.DataFrame) -> pd.Series:
        executed = len(group)
        failed = int((group["status"] == "FAIL").sum())
        return pd.Series(
            {
                "executed": executed,
                "failed": failed,
                "failure_rate": round(failed / executed, 4) if executed else 0.0,
            }
        )

    summary = (
        exploded.groupby("tags").apply(_rate, include_groups=False).reset_index()
        if _supports_include_groups()
        else exploded.groupby("tags").apply(_rate).reset_index()
    )
    summary = summary.sort_values("failure_rate", ascending=False)
    return [
        {
            "tag": row["tags"],
            "executed": int(row["executed"]),
            "failed": int(row["failed"]),
            "failure_rate": float(row["failure_rate"]),
        }
        for _, row in summary.iterrows()
    ]


def build_metrics(result: ParsedResult) -> Dict[str, object]:
    """Assemble the full analytics bundle used by the API and AI agent."""
    return {
        "pass_rate": result.pass_rate,
        "total_tests": result.total_tests,
        "passed": result.passed,
        "failed": result.failed,
        "skipped": result.skipped,
        "total_duration_seconds": result.total_duration_seconds,
        "slowest_tests": slowest_tests(result),
        "keyword_failure_counts": keyword_failure_counts(result),
        "failure_rate_by_tag": failure_rate_by_tag(result),
    }


def _supports_include_groups() -> bool:
    """Whether the installed pandas accepts ``include_groups`` on ``apply``."""
    try:
        major, minor = (int(p) for p in pd.__version__.split(".")[:2])
    except (ValueError, AttributeError):  # pragma: no cover - defensive
        return False
    return (major, minor) >= (2, 2)
