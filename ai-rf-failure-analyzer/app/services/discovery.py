"""Robot project auto-discovery.

Scans one or more configured root directories for Robot Framework
``output.xml`` files and exposes each as a :class:`DiscoveredProject`. This
keeps the analyzer project-agnostic: point ``project_roots`` at any repository
(the sibling ``tests/`` suites by default, or an absolute path to another
project) and its results become analyzable without uploading files by hand.

The :class:`ProjectScanner` interface follows the same Dependency-Inversion
pattern as :class:`~app.parsers.base.ResultParser` and
:class:`~app.services.storage.ResultStore`: the service depends on the
abstraction, and the filesystem implementation can be swapped (e.g. for an S3
or artifact-server scanner) without touching callers.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from datetime import datetime
from fnmatch import fnmatch
from pathlib import Path
from typing import Iterable, List, Set

from app.core.exceptions import ValidationError
from app.models.schemas import DiscoveredProject


class ProjectScanner(ABC):
    """Abstract discovery interface for Robot Framework result files."""

    @abstractmethod
    def discover(self) -> List[DiscoveredProject]:
        """Return every discoverable project, sorted for stable output."""

    @abstractmethod
    def resolve_allowed(self, path: str) -> Path:
        """Resolve ``path`` to a safe, discoverable file or raise.

        Guards against path traversal: the resolved path must live under one
        of the configured roots and match the result glob. Raises
        :class:`~app.core.exceptions.ValidationError` otherwise.
        """


class FileSystemProjectScanner(ProjectScanner):
    """Discover ``output.xml`` files by walking the local filesystem."""

    def __init__(
        self,
        roots: Iterable[Path],
        *,
        output_glob: str,
        exclude_dirs: Iterable[str],
    ) -> None:
        # Keep only existing directories; resolve for reliable containment checks.
        self._roots: List[Path] = [
            r.resolve() for r in roots if Path(r).is_dir()
        ]
        self._output_glob = output_glob
        self._exclude_dirs: Set[str] = {d for d in exclude_dirs}

    # -- discovery --------------------------------------------------------
    def discover(self) -> List[DiscoveredProject]:
        projects: List[DiscoveredProject] = []
        seen: Set[Path] = set()
        for root in self._roots:
            for match in self._walk(root):
                if match in seen:  # same file reachable from overlapping roots
                    continue
                seen.add(match)
                projects.append(self._describe(match, root))
        projects.sort(key=lambda p: (p.root, p.relative_path))
        return projects

    def _walk(self, root: Path) -> Iterable[Path]:
        for dirpath, dirnames, filenames in os.walk(root):
            # Prune excluded directories in place so os.walk never descends.
            dirnames[:] = [d for d in dirnames if d not in self._exclude_dirs]
            for filename in filenames:
                if fnmatch(filename, self._output_glob):
                    yield Path(dirpath, filename)

    def _describe(self, match: Path, root: Path) -> DiscoveredProject:
        rel = match.relative_to(root)
        # Friendly name: the directory holding the result, relative to the root.
        # Falls back to the root's own name when the file sits directly in it.
        parent_rel = rel.parent.as_posix()
        project = parent_rel if parent_rel not in ("", ".") else root.name
        try:
            stat = match.stat()
            size = stat.st_size
            modified = datetime.fromtimestamp(stat.st_mtime)
        except OSError:  # pragma: no cover - file vanished between walk and stat
            size = 0
            modified = None
        return DiscoveredProject(
            project=project,
            path=str(match),
            relative_path=rel.as_posix(),
            root=str(root),
            size_bytes=size,
            modified_at=modified,
        )

    # -- safe resolution --------------------------------------------------
    def resolve_allowed(self, path: str) -> Path:
        if not path or not str(path).strip():
            raise ValidationError("A project 'path' is required.")
        candidate = Path(path)
        if not candidate.is_absolute():
            # Resolve relative requests against each root until one contains it.
            candidate = self._first_existing_under_roots(candidate)
        resolved = candidate.resolve()

        if not self._within_roots(resolved):
            raise ValidationError(
                "Path is outside the configured project roots. Set PROJECT_ROOTS "
                "to scan additional locations."
            )
        if not fnmatch(resolved.name, self._output_glob):
            raise ValidationError(
                f"'{resolved.name}' is not a Robot result file "
                f"(expected glob '{self._output_glob}')."
            )
        if not resolved.is_file():
            raise ValidationError(f"No such result file: {resolved}")
        return resolved

    def _first_existing_under_roots(self, relative: Path) -> Path:
        for root in self._roots:
            candidate = (root / relative)
            if candidate.exists():
                return candidate
        # Nothing matched; return as-is so the containment check rejects it.
        return relative

    def _within_roots(self, resolved: Path) -> bool:
        for root in self._roots:
            try:
                resolved.relative_to(root)
                return True
            except ValueError:
                continue
        return False
