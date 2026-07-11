"""
Local filesystem connector. Watches a directory for supported document types.
Supported: PDF, DOCX, XLSX, XLS, PPTX, PPT, TXT, MD, RTF, CSV.

Usage:
    connector = FilesystemConnector("/path/to/docs")
    async for doc in connector.sync(since=last_sync_time):
        # dispatch doc to ingestion worker
        ...
"""
from __future__ import annotations

import mimetypes
from datetime import datetime
from pathlib import Path

from connectors.base import BaseConnector, ConnectorDocument

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({
    ".pdf", ".docx", ".xlsx", ".xls", ".pptx", ".ppt",
    ".txt", ".md", ".markdown", ".rtf", ".csv",
})

# These formats need binary extraction via extractor.py
_BINARY_EXTENSIONS: frozenset[str] = frozenset({
    ".pdf", ".docx", ".xlsx", ".xls", ".pptx", ".ppt", ".rtf",
})


class FilesystemConnector(BaseConnector):
    def __init__(self, watch_dir: str | Path):
        self.watch_dir = Path(watch_dir).resolve()

    async def list_documents(self, since: datetime | None = None) -> list[str]:
        docs = []
        for path in self.watch_dir.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue
            if since is not None:
                mtime = datetime.fromtimestamp(path.stat().st_mtime)
                if mtime <= since:
                    continue
            docs.append(str(path))
        return docs

    async def fetch_document(self, source_id: str) -> ConnectorDocument | None:
        path = Path(source_id)
        if not path.exists() or not path.is_file():
            return None

        suffix = path.suffix.lower()
        mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        stat = path.stat()
        created = datetime.fromtimestamp(stat.st_ctime)
        updated = datetime.fromtimestamp(stat.st_mtime)

        if suffix in _BINARY_EXTENSIONS:
            # Pass raw bytes; extractor.py handles text extraction
            raw_bytes = path.read_bytes()
            return ConnectorDocument(
                source_id=source_id,
                title=path.stem,
                content="",
                content_type=mime,
                source_type="filesystem",
                raw_bytes=raw_bytes,
                created_at=created,
                updated_at=updated,
                url=f"file://{path}",
            )

        # Plain text formats — read directly
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return None

        return ConnectorDocument(
            source_id=source_id,
            title=path.stem,
            content=content,
            content_type="text/plain" if suffix not in {".csv"} else "text/csv",
            source_type="filesystem",
            created_at=created,
            updated_at=updated,
            url=f"file://{path}",
        )
