"""
MCP-compliant JSON-RPC 2.0 server. POST /mcp
Bearer token identifies the calling user — all tool calls go through RBAC + audit.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import CurrentUser
from database import get_db
from mcp_server.tools import (
    CheckAccessParams,
    DecisionsParams,
    EntityRelationsParams,
    SearchParams,
    check_employee_access,
    get_decisions,
    get_entity_relations,
    search_knowledge,
)

router = APIRouter(prefix="/mcp", tags=["mcp"])

_TOOLS: dict = {
    "search_knowledge":      (search_knowledge,      SearchParams),
    "get_entity_relations":  (get_entity_relations,  EntityRelationsParams),
    "get_decisions":         (get_decisions,          DecisionsParams),
    "check_employee_access": (check_employee_access, CheckAccessParams),
}


@router.get("/manifest")
async def manifest() -> dict:
    """Return MCP tool manifest so agents can discover available tools."""
    return {
        "protocol": "jsonrpc/2.0",
        "tools": [
            {
                "name": "search_knowledge",
                "description": "Hybrid RAG search over the company knowledge base with full RBAC enforcement.",
                "parameters": {"type": "object", "properties": {
                    "query": {"type": "string"},
                    "context": {"type": "string", "default": ""},
                    "n_results": {"type": "integer", "default": 5, "minimum": 1, "maximum": 20},
                }},
            },
            {
                "name": "get_entity_relations",
                "description": "Return graph triples for a named entity (depth-1 subgraph traversal, ACL-filtered).",
                "parameters": {"type": "object", "properties": {
                    "entity_name": {"type": "string"},
                    "depth": {"type": "integer", "default": 1, "minimum": 1, "maximum": 2},
                }},
            },
            {
                "name": "get_decisions",
                "description": "Query the Decision Trail — structured decision records with rationale and decision-makers.",
                "parameters": {"type": "object", "properties": {
                    "topic": {"type": "string", "default": ""},
                    "project": {"type": "string", "default": ""},
                }},
            },
            {
                "name": "check_employee_access",
                "description": "Admin-only: check whether a given employee has access to a topic or document.",
                "parameters": {"type": "object", "properties": {
                    "user_email": {"type": "string"},
                    "topic_or_doc": {"type": "string"},
                }},
            },
        ],
    }


@router.post("")
async def mcp_endpoint(
    body: dict,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """JSON-RPC 2.0 dispatch. Same RBAC + audit as human queries; caller_type=mcp_agent."""
    rpc_id = body.get("id")
    method = body.get("method", "")
    params = body.get("params") or {}

    if method not in _TOOLS:
        return {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "error": {"code": -32601, "message": f"Method '{method}' not found. Available: {list(_TOOLS)}"},
        }

    tool_fn, ParamsModel = _TOOLS[method]
    try:
        parsed = ParamsModel(**params)
        result = await tool_fn(parsed, user=user, db=db)
        return {"jsonrpc": "2.0", "id": rpc_id, "result": result}
    except PermissionError as exc:
        return {"jsonrpc": "2.0", "id": rpc_id, "error": {"code": -32000, "message": str(exc)}}
    except Exception as exc:
        return {"jsonrpc": "2.0", "id": rpc_id, "error": {"code": -32603, "message": str(exc)}}
