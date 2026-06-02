"""Pure rule-based classification into the label set from 09-Classification.

Labels: code, documentation, engineering, reasoning, agent, memory, general.
Deterministic and unit-testable; an ML model can replace `classify` later.
"""

from __future__ import annotations

import re

from arc.db.enums import DocLabel

_CODE_EXT = {
    ".py", ".js", ".ts", ".tsx", ".go", ".rs", ".java", ".c", ".h", ".cpp",
    ".rb", ".php", ".cs", ".kt", ".swift", ".scala", ".sh", ".sql",
}
_DOC_EXT = {".md", ".rst", ".txt", ".adoc"}
_CODE_HINTS = re.compile(r"\b(def |class |import |function |const |#include|public static)\b")
_REASONING_HINTS = re.compile(r"\b(therefore|let'?s think|step by step|we can prove|hence)\b", re.I)
# Note: no trailing \b — a \b after a literal ':' can never match (':' and the
# following space are both non-word chars), which would silently disable the
# colon-terminated markers.
_AGENT_HINTS = re.compile(r"\btool call\b|\bagent\b|observation:|action:|thought:", re.I)
_MEMORY_HINTS = re.compile(r"\bremember that\b|\brecall\b|\bmemory\b|note to self", re.I)
_ENG_HINTS = re.compile(r"\b(RFC|architecture|design doc|postmortem|incident|SLA|latency)\b")


def _ext(path: str | None) -> str:
    if not path or "." not in path:
        return ""
    return path[path.rfind(".") :].lower()


def classify(text: str, metadata: dict) -> DocLabel:
    path = metadata.get("path") or metadata.get("url")
    ext = _ext(path)
    sample = text[:4000]

    if ext in _CODE_EXT or _CODE_HINTS.search(sample):
        return DocLabel.CODE
    if ext in _DOC_EXT or (metadata.get("source_type") in {"web_docs", "wikipedia"}):
        return DocLabel.DOCUMENTATION
    if _AGENT_HINTS.search(sample):
        return DocLabel.AGENT
    if _MEMORY_HINTS.search(sample):
        return DocLabel.MEMORY
    if _REASONING_HINTS.search(sample):
        return DocLabel.REASONING
    if _ENG_HINTS.search(sample):
        return DocLabel.ENGINEERING
    return DocLabel.GENERAL
