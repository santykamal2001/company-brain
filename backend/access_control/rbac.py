"""
RBAC enforcement: chunk-level and graph-node-level permission checks.
Pre-filter is applied at the vector store (Qdrant metadata filter).
Post-filter here is the defense-in-depth layer using Postgres as source of truth.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from access_control.models import Chunk, ClassificationEnum, DocumentACL, RoleEnum, User


# Classification hierarchy: higher index = more restrictive
_CLASSIFICATION_ORDER = [
    ClassificationEnum.public,
    ClassificationEnum.internal,
    ClassificationEnum.confidential,
    ClassificationEnum.restricted,
]

_ROLE_MAX_CLASSIFICATION: dict[RoleEnum, ClassificationEnum] = {
    RoleEnum.guest: ClassificationEnum.public,
    RoleEnum.employee: ClassificationEnum.internal,
    RoleEnum.manager: ClassificationEnum.confidential,
    RoleEnum.admin: ClassificationEnum.restricted,
}


@dataclass
class ACLContext:
    """Derived from the authenticated user; passed through the retrieval pipeline."""
    user_id: str
    role: RoleEnum
    department: str | None
    project_ids: list[str] = field(default_factory=list)

    @property
    def max_classification(self) -> ClassificationEnum:
        return _ROLE_MAX_CLASSIFICATION[self.role]

    def qdrant_filter(self) -> dict:
        """
        Build a Qdrant filter dict that Qdrant evaluates at ANN search time.
        Uses denormalized boolean fields on each vector payload:
          allowed_role_<role>: true | false
          allowed_dept_<dept>: true | false
        Admin bypasses all department/project checks.
        """
        must = [{"key": f"allowed_role_{self.role.value}", "match": {"value": True}}]
        if self.role != RoleEnum.admin and self.department:
            # department filter: either no dept restriction or user's dept is allowed
            must.append({
                "should": [
                    {"key": "no_dept_restriction", "match": {"value": True}},
                    {"key": f"allowed_dept_{self.department}", "match": {"value": True}},
                ]
            })
        return {"must": must}


def acl_context_from_user(user: User) -> ACLContext:
    dept_name = user.department.name if user.department else None
    return ACLContext(
        user_id=str(user.id),
        role=user.role,
        department=dept_name,
        project_ids=[str(p) for p in (user.project_ids or [])],
    )


def _classification_level(c: ClassificationEnum) -> int:
    return _CLASSIFICATION_ORDER.index(c)


async def post_filter_chunks(
    chunk_ids: list[str],
    acl: ACLContext,
    db: AsyncSession,
) -> tuple[list[str], list[str]]:
    """
    Re-verify chunk permissions against Postgres (source of truth).
    Returns (allowed_ids, denied_ids).
    This catches Qdrant payload staleness after ACL version bumps.
    """
    if not chunk_ids:
        return [], []

    rows = await db.execute(
        select(Chunk.id, Chunk.acl_version, Chunk.document_id)
        .where(Chunk.id.in_([UUID(cid) for cid in chunk_ids]))
    )
    chunk_rows = rows.all()

    doc_ids = list({str(r.document_id) for r in chunk_rows})
    acl_rows = await db.execute(
        select(DocumentACL).where(DocumentACL.document_id.in_([UUID(d) for d in doc_ids]))
    )
    doc_acls: dict[str, DocumentACL] = {
        str(a.document_id): a for a in acl_rows.scalars()
    }

    allowed, denied = [], []
    max_level = _classification_level(acl.max_classification)

    for row in chunk_rows:
        doc_acl = doc_acls.get(str(row.document_id))
        if doc_acl is None:
            denied.append(str(row.id))
            continue

        doc_level = _classification_level(doc_acl.classification)
        if doc_level > max_level:
            denied.append(str(row.id))
            continue

        # Role check
        if doc_acl.allowed_roles and acl.role.value not in doc_acl.allowed_roles:
            # explicit whitelist on user overrides
            if str(acl.user_id) not in (doc_acl.allowed_users or []):
                denied.append(str(row.id))
                continue

        # Department check (admin bypasses)
        if acl.role != RoleEnum.admin and doc_acl.allowed_departments:
            if acl.department not in doc_acl.allowed_departments:
                if str(acl.user_id) not in (doc_acl.allowed_users or []):
                    denied.append(str(row.id))
                    continue

        allowed.append(str(row.id))

    return allowed, denied


def acl_payload_for_chunk(
    classification: ClassificationEnum,
    allowed_roles: list[str],
    allowed_departments: list[str],
    allowed_users: list[str],
) -> dict[str, Any]:
    """
    Build the Qdrant payload dict with denormalized boolean ACL flags.
    Called at ingestion time for every chunk vector.
    """
    payload: dict[str, Any] = {
        "classification": classification.value,
        "acl_allowed_users": allowed_users,
    }

    for role in RoleEnum:
        # Role is allowed if: no role restriction OR role is in allowed list
        # Admin always gets access to everything at ingestion
        if role == RoleEnum.admin:
            payload[f"allowed_role_{role.value}"] = True
        elif not allowed_roles:
            payload[f"allowed_role_{role.value}"] = _classification_level(
                _ROLE_MAX_CLASSIFICATION[role]
            ) >= _classification_level(classification)
        else:
            payload[f"allowed_role_{role.value}"] = (
                role.value in allowed_roles
                and _classification_level(_ROLE_MAX_CLASSIFICATION[role])
                >= _classification_level(classification)
            )

    payload["no_dept_restriction"] = not bool(allowed_departments)
    # Add per-department flags (max 50 departments; beyond that use allowed_users list)
    for dept in allowed_departments[:50]:
        payload[f"allowed_dept_{dept}"] = True

    return payload


def query_hash(question: str) -> str:
    return hashlib.sha256(question.encode()).hexdigest()[:16]
