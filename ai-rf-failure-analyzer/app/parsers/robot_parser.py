"""Robot Framework ``output.xml`` parser.

This implementation uses the standard-library :mod:`xml.etree.ElementTree`
so it is dependency-light and resilient across Robot Framework schema
versions. It understands both the legacy timestamp format
(``starttime``/``endtime`` like ``20231010 10:00:00.000``) and the newer
ISO + ``elapsed`` format introduced in Robot Framework 7.

Only ``output.xml`` carries machine-readable results; ``report.html`` and
``log.html`` are human-facing renderings. The API still accepts them for
convenience but they are not parsed for statistics.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from xml.etree import ElementTree as ET

from app.core.exceptions import ParseError
from app.models.schemas import (
    KeywordFailure,
    ParsedResult,
    SuiteStatistics,
    TestCaseResult,
    TestStatus,
)
from app.parsers.base import ResultParser

_LEGACY_TS_FORMAT = "%Y%m%d %H:%M:%S.%f"


class RobotOutputParser(ResultParser):
    """Parse a Robot Framework ``output.xml`` document."""

    def parse(self, content: bytes) -> ParsedResult:
        try:
            root = ET.fromstring(content)
        except ET.ParseError as exc:  # malformed XML
            raise ParseError(f"Invalid XML: {exc}") from exc

        if root.tag != "robot":
            raise ParseError(
                "Not a Robot Framework output.xml (missing <robot> root). "
                "report.html and log.html cannot be parsed for statistics."
            )

        result = ParsedResult(
            generated_at=self._parse_timestamp(root.get("generated")),
            generator=root.get("generator"),
        )

        for suite in root.findall("suite"):
            self._visit_suite(suite, parent_path="", result=result)

        # Derive top-level totals from the collected tests.
        result.total_tests = len(result.all_tests)
        result.passed = sum(
            1 for t in result.all_tests if t.status == TestStatus.PASS
        )
        result.failed = sum(
            1 for t in result.all_tests if t.status == TestStatus.FAIL
        )
        result.skipped = sum(
            1 for t in result.all_tests if t.status == TestStatus.SKIP
        )
        result.total_duration_seconds = round(
            sum(t.duration_seconds for t in result.all_tests), 3
        )
        return result

    # -- suite / test traversal ------------------------------------------
    def _visit_suite(
        self, suite: ET.Element, parent_path: str, result: ParsedResult
    ) -> None:
        name = suite.get("name", "Unnamed Suite")
        path = f"{parent_path}.{name}" if parent_path else name

        direct_tests = suite.findall("test")
        if direct_tests:
            stat = SuiteStatistics(name=path)
            for test_el in direct_tests:
                test = self._parse_test(test_el, suite_path=path, result=result)
                result.all_tests.append(test)
                stat.total += 1
                stat.duration_seconds = round(
                    stat.duration_seconds + test.duration_seconds, 3
                )
                if test.status == TestStatus.PASS:
                    stat.passed += 1
                elif test.status == TestStatus.FAIL:
                    stat.failed += 1
                    result.failed_tests.append(test)
                elif test.status == TestStatus.SKIP:
                    stat.skipped += 1
            result.suite_statistics.append(stat)

        for child in suite.findall("suite"):
            self._visit_suite(child, parent_path=path, result=result)

    def _parse_test(
        self, test_el: ET.Element, suite_path: str, result: ParsedResult
    ) -> TestCaseResult:
        status_el = test_el.find("status")
        status = self._parse_status(status_el)
        message = (status_el.text or "").strip() if status_el is not None else ""

        tags = [
            (t.text or "").strip()
            for t in test_el.findall("tags/tag") + test_el.findall("tag")
            if (t.text or "").strip()
        ]

        failing_keyword: Optional[str] = None
        if status == TestStatus.FAIL:
            failing_keyword = self._extract_failing_keyword(
                test_el,
                test_name=test_el.get("name", "Unnamed Test"),
                suite_path=suite_path,
                result=result,
            )

        return TestCaseResult(
            name=test_el.get("name", "Unnamed Test"),
            suite=suite_path,
            status=status,
            message=message or None,
            duration_seconds=self._compute_duration(status_el),
            tags=tags,
            failing_keyword=failing_keyword,
        )

    # -- keyword failure extraction --------------------------------------
    def _extract_failing_keyword(
        self,
        test_el: ET.Element,
        test_name: str,
        suite_path: str,
        result: ParsedResult,
    ) -> Optional[str]:
        """Return the name of the most specific failing keyword.

        Robot nests keywords; the innermost failing keyword carries the real
        error. We therefore select a *leaf* failing keyword — one with no
        descendant keyword that also failed.
        """
        failing = [
            kw
            for kw in test_el.iter("kw")
            if self._parse_status(kw.find("status")) == TestStatus.FAIL
        ]
        leaf = None
        for kw in failing:
            descendants = [d for d in kw.iter("kw") if d is not kw]
            has_failing_child = any(
                self._parse_status(d.find("status")) == TestStatus.FAIL
                for d in descendants
            )
            if not has_failing_child:
                leaf = kw
                break
        if leaf is None:
            return None

        name = leaf.get("name", "Unknown Keyword")
        result.keyword_failures.append(
            KeywordFailure(
                name=name,
                library=leaf.get("library") or leaf.get("owner"),
                error_message=self._keyword_error_message(leaf),
                test_name=test_name,
                suite_name=suite_path,
            )
        )
        return name

    @staticmethod
    def _keyword_error_message(kw: ET.Element) -> Optional[str]:
        for msg in kw.findall("msg"):
            if (msg.get("level") or "").upper() in {"FAIL", "ERROR"}:
                text = (msg.text or "").strip()
                if text:
                    return text
        return None

    # -- low-level helpers -----------------------------------------------
    @staticmethod
    def _parse_status(status_el: Optional[ET.Element]) -> TestStatus:
        if status_el is None:
            return TestStatus.NOT_RUN
        raw = (status_el.get("status") or "").upper()
        try:
            return TestStatus(raw)
        except ValueError:
            return TestStatus.NOT_RUN

    @classmethod
    def _compute_duration(cls, status_el: Optional[ET.Element]) -> float:
        if status_el is None:
            return 0.0

        # Robot Framework 7+: explicit elapsed seconds.
        elapsed = status_el.get("elapsed")
        if elapsed is not None:
            try:
                return round(float(elapsed), 3)
            except ValueError:
                pass

        start = status_el.get("starttime") or status_el.get("start")
        end = status_el.get("endtime") or status_el.get("end")
        start_dt = cls._parse_timestamp(start)
        end_dt = cls._parse_timestamp(end)
        if start_dt and end_dt:
            return round((end_dt - start_dt).total_seconds(), 3)
        return 0.0

    @staticmethod
    def _parse_timestamp(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        text = value.strip()
        # Legacy Robot format: "20231010 10:00:00.123".
        try:
            return datetime.strptime(text, _LEGACY_TS_FORMAT)
        except ValueError:
            pass
        # ISO 8601 (Robot Framework 7+).
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            return None
