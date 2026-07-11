"""
Abstract connector interface. All source connectors implement BaseConnector.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import AsyncGenerator


@dataclass
class ConnectorDocument:
    """A document yielded by a connector — ready for the ingestion pipeline."""
    source_id: str              # Unique key within this connector (path, page-id, message-ts…)
    title: str
    content: str                # Extracted plain text (empty if raw_bytes provided)
    content_type: str           # MIME type: "text/plain", "application/pdf", etc.
    source_type: str            # "filesystem" | "confluence" | "notion" | "slack" | "email"
    created_at: datetime | None = None
    updated_at: datetime | None = None
    author: str | None = None
    url: str | None = None
    raw_bytes: bytes | None = None          # Binary file content; extractor.py handles conversion
    classification_hint: str | None = None  # "internal" | "confidential" — connector-level hint
    metadata: dict = field(default_factory=dict)


class BaseConnector(ABC):
    """
    Abstract connector. Subclasses override list_documents and fetch_document.
    The default sync() generator composes them into a stream of ConnectorDocuments.
    """

    @abstractmethod
    async def list_documents(self, since: datetime | None = None) -> list[str]:
        """
        Return source_ids of documents to ingest.
        If since is provided, return only documents modified after that timestamp.
        """
        ...

    @abstractmethod
    async def fetch_document(self, source_id: str) -> ConnectorDocument | None:
        """
        Fetch and return a single document by source_id.
        Return None if the document no longer exists.
        """
        ...

    async def sync(
        self, since: datetime | None = None
    ) -> AsyncGenerator[ConnectorDocument, None]:
        """
        Yield ConnectorDocuments for all changed sources.
        Default implementation: list → fetch one-by-one.
        Subclasses may override for batch fetching.
        """
        for source_id in await self.list_documents(since=since):
            doc = await self.fetch_document(source_id)
            if doc is not None:
                yield doc
