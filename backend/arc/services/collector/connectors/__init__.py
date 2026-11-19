"""Source connectors. Composition over inheritance: each connector implements
the `Connector` protocol; the registry maps SourceType -> connector instance.
"""

from __future__ import annotations

from arc.db.enums import SourceType
from arc.services.collector.connectors.base import Connector, RawDocument
from arc.services.collector.connectors.github import GitHubConnector
from arc.services.collector.connectors.inline import InlineConnector
from arc.services.collector.connectors.web import WebDocsConnector, WikipediaConnector

# SourceHut/RFC reuse the web connector (HTTP fetch + SSRF guard) with
# source-specific config; included per the PRD (07-spec had omitted them).
_REGISTRY: dict[SourceType, Connector] = {
    SourceType.GITHUB: GitHubConnector(),
    # GITLAB: no connector yet (the GitHub one can't parse GitLab URLs/APIs);
    # collect fails fast with "no connector" instead of silently fetching nothing.
    SourceType.SOURCEHUT: WebDocsConnector(),
    SourceType.WEB_DOCS: WebDocsConnector(),
    SourceType.RFC: WebDocsConnector(),
    SourceType.WIKIPEDIA: WikipediaConnector(),
    SourceType.WEB_DATASET: InlineConnector(),
}


def get_connector(source_type: SourceType) -> Connector:
    try:
        return _REGISTRY[source_type]
    except KeyError as exc:
        raise LookupError(f"no connector for source type {source_type}") from exc


__all__ = ["Connector", "RawDocument", "get_connector"]
