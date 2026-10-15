"""Architecture analysis for the exam (RQ-EXM-014, RQ-EXM-023, RQ-EXM-030).

The analyzer separates three kinds of statement, and never blurs them:

``observed``
    Derived only from deterministic project evidence — the files and packages
    ``AndroidProjectAnalyzer`` actually reported.
``documented``
    Taken from student-authored documentation the exam definition accepts. It
    explains intent; it is not proof.
``inferred``
    Produced by the LLM. An inferred claim is kept only when it cites at least
    one observed or documented evidence reference; anything else is reported as an
    unsupported claim instead of being presented as fact.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..evaluation import EvidenceContext
from ..models import Evidence, UnsupportedClaim
from .models import (
    ArchitectureClaim,
    ArchitectureReport,
    ExamDefinition,
)

#: Source-file suffixes that can hold a component.
_SOURCE_SUFFIXES = (".kt", ".java")

#: Layer keyword -> the component name students usually use.
_LAYER_HINTS = {
    "presentation": ("ui", "screen", "activity", "fragment", "composable", "view"),
    "domain": ("domain", "usecase", "usecase", "entity", "model"),
    "data": ("data", "repository", "dao", "database", "api", "network", "remote"),
    "di": ("di", "injection", "module", "hilt", "koin", "container"),
}

#: Architecture components the spec asks the report to identify when present.
COMPONENT_HINTS = (
    ("modules", ("module",)),
    ("viewmodels", ("viewmodel", "presenter")),
    ("repositories", ("repository",)),
    ("dependency_injection", ("hilt", "koin", "injection", "di")),
    ("navigation", ("navigation", "navgraph", "navigator", "router")),
    ("persistence", ("room", "sqlite", "datastore", "preference", "persistence")),
    ("network", ("retrofit", "okhttp", "api", "network", "remote")),
    ("testing", ("test", "spec")),
)

#: ``class FooRepository`` / ``interface FooDao`` / ``object BarModule``
_DECL_RE = re.compile(
    r"\b(?:class|interface|object|abstract class)\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)"
)

MAX_DOC_BYTES = 200_000


class ArchitectureAnalyzer:
    """Builds an evidence-grounded ``ArchitectureReport``."""

    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root)

    def analyze(
        self,
        evidence: EvidenceContext,
        definition: ExamDefinition,
        inferred_claims: list[ArchitectureClaim] | None = None,
    ) -> ArchitectureReport:
        observed = self._observed_claims(evidence)
        documented = self._documented_claims(definition)
        known_refs = {
            ref
            for claim in (*observed, *documented)
            for ref in claim.evidence_refs
        }
        inferred, unsupported = self._split_inferred(inferred_claims or [], known_refs)
        doc_files = [
            str(p.relative_to(self.project_root))
            for p in definition.documentation_paths(self.project_root)
        ]
        return ArchitectureReport(
            narrative=self._narrative(observed, documented, inferred),
            claims=[*observed, *documented, *inferred],
            modules=self._names_matching(evidence, "module"),
            packages=self._packages(evidence),
            documentation_files=doc_files,
            unsupported_claims=unsupported,
        )

    # -- observed ---------------------------------------------------------

    def _observed_claims(self, evidence: EvidenceContext) -> list[ArchitectureClaim]:
        claims: list[ArchitectureClaim] = []
        structure = [e for e in evidence.evidence if e.type == "structure"]
        if not structure:
            return claims
        refs = [e.id for e in structure if e.id]
        for layer, keywords in _LAYER_HINTS.items():
            matched = [
                e.file or e.message
                for e in structure
                if any(k in (e.file or e.message).lower() for k in keywords)
            ]
            if matched:
                claims.append(
                    ArchitectureClaim(
                        claim=f"the project has a {layer} area: "
                        f"{len(matched)} inspected file(s) match {layer} naming",
                        kind="observed",
                        evidence_refs=[e.id for e in structure if e.id][:5] or refs[:5],
                        source="project structure evidence",
                    )
                )
        for component, keywords in COMPONENT_HINTS:
            matched = [
                e
                for e in structure
                if any(k in (e.file or "").lower() for k in keywords)
            ]
            if not matched:
                continue
            names = sorted(
                {
                    name
                    for group in (
                        _declarations_in(self.project_root, e.file) for e in matched
                    )
                    for name in group
                }
            )
            label = ", ".join(names[:6]) or f"{len(matched)} file(s)"
            claims.append(
                ArchitectureClaim(
                    claim=f"{component.replace('_', ' ')} present: {label}",
                    kind="observed",
                    evidence_refs=[e.id for e in matched if e.id][:5],
                    source="project structure evidence",
                )
            )
        return claims

    def _names_matching(self, evidence: EvidenceContext, needle: str) -> list[str]:
        found = {
            (e.file or "").split("/")[0]
            for e in evidence.evidence
            if e.type == "structure" and needle in (e.file or "").lower()
        }
        return sorted(found)

    def _packages(self, evidence: EvidenceContext) -> list[str]:
        packages: set[str] = set()
        for item in evidence.evidence:
            if item.type != "structure" or not item.file:
                continue
            parts = item.file.split("/")
            # Only one language root is usually present, and a source set may
            # contain both; the deepest one is the package root. The last path
            # segment is the file name, never part of the package.
            indices = [
                parts.index(name)
                for name in ("kotlin", "java")
                if name in parts
            ]
            if not indices:
                continue
            package = ".".join(parts[max(indices) + 1 : -1])
            if package:
                packages.add(package)
        return sorted(packages)

    # -- documented -------------------------------------------------------

    def _documented_claims(
        self, definition: ExamDefinition
    ) -> list[ArchitectureClaim]:
        claims: list[ArchitectureClaim] = []
        for path in definition.documentation_paths(self.project_root):
            relative = str(path.relative_to(self.project_root))
            try:
                if path.stat().st_size > MAX_DOC_BYTES:
                    continue
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            headings = [
                line.lstrip("#").strip()
                for line in text.splitlines()
                if line.lstrip().startswith("#")
            ]
            summary = ", ".join(headings[:8]) or "(no headings)"
            claims.append(
                ArchitectureClaim(
                    claim=f"student documentation {relative} describes: {summary}",
                    kind="documented",
                    evidence_refs=[f"doc://{relative}"],
                    source=relative,
                )
            )
        return claims

    # -- inferred ---------------------------------------------------------

    @staticmethod
    def _split_inferred(
        claims: list[ArchitectureClaim], known_refs: set[str]
    ) -> tuple[list[ArchitectureClaim], list[UnsupportedClaim]]:
        """Keep only inferred claims grounded in observed/documented evidence."""
        kept: list[ArchitectureClaim] = []
        unsupported: list[UnsupportedClaim] = []
        for claim in claims:
            if claim.kind != "inferred":
                unsupported.append(
                    UnsupportedClaim(
                        claim=claim.claim,
                        kind="inferred",
                        reason="architecture claims must be declared as inferred",
                    )
                )
                continue
            resolved = [r for r in claim.evidence_refs if r in known_refs]
            if not resolved:
                unsupported.append(
                    UnsupportedClaim(
                        claim=claim.claim,
                        kind="inferred",
                        reason="cites no observed or documented evidence reference",
                    )
                )
                continue
            kept.append(claim.model_copy(update={"evidence_refs": resolved}))
        return kept, unsupported

    # -- narrative --------------------------------------------------------

    @staticmethod
    def _narrative(
        observed: list[ArchitectureClaim],
        documented: list[ArchitectureClaim],
        inferred: list[ArchitectureClaim],
    ) -> str:
        if not observed and not documented and not inferred:
            return (
                "No architecture evidence was available, so the project's "
                "architecture is not evaluated."
            )
        parts = [
            f"Observed in the project: {len(observed)} statement(s); "
            f"documented by the student: {len(documented)}; "
            f"inferred interpretation: {len(inferred)}.",
        ]
        if observed:
            parts.append(
                "The observed statements come from inspected project files only."
            )
        if documented:
            parts.append(
                "Documented statements are the student's own explanation and do "
                "not by themselves prove the behaviour works."
            )
        if inferred:
            parts.append(
                "Inferred statements were kept only where they cite observed or "
                "documented evidence."
            )
        return " ".join(parts)


def _declarations_in(project_root: Path, relative: str | None) -> list[str]:
    """Type names declared in one source file; empty when unreadable."""
    if not relative:
        return []
    path = project_root / relative
    if path.suffix not in _SOURCE_SUFFIXES or not path.is_file():
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    return [m.group("name") for m in _DECL_RE.finditer(text)]


def evidence_refs(evidence: list[Evidence]) -> list[str]:
    return [e.id for e in evidence if e.id]


__all__ = [
    "ArchitectureAnalyzer",
    "COMPONENT_HINTS",
    "evidence_refs",
]
