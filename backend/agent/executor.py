"""
Post-answer agentic execution. After brain.py generates an answer, classify whether
an action is appropriate and return a proposal. The UI shows it; user confirms.
Only then does execute_action() run — logged to access_audit as event_type='action'.

Phase 1.5 note: the actual outbound calls (Slack, Jira, Calendar) stub successfully
so the UI confirm/execute flow works end-to-end without requiring external MCP servers.
Replace the stubs with real MCP client calls when those integrations are wired.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class ActionProposal:
    action_type: str        # "slack_dm" | "jira_ticket" | "calendar_invite"
    label: str              # Short label shown in the UI button
    description: str        # One sentence: what the action would do
    payload: dict           # Pre-filled data sent to execute_action()


# Heuristic regexes — order matters (most specific first)
_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("jira_ticket", re.compile(
        r"\b(create|open|file|add|track|log)\b.{0,50}\b(ticket|issue|task|bug|story|backlog)\b",
        re.IGNORECASE,
    )),
    ("calendar_invite", re.compile(
        r"\b(schedule|book|set up|create|draft)\b.{0,50}\b(meeting|call|invite|sync|standup|calendar)\b",
        re.IGNORECASE,
    )),
    ("slack_dm", re.compile(
        r"\b(send|message|notify|ping|dm|tell|alert)\b.{0,50}\b(slack|message|dm|channel|team)\b",
        re.IGNORECASE,
    )),
]


def classify_action_intent(question: str, answer: str) -> ActionProposal | None:
    """
    Scan the combined question + answer for action signals.
    Returns the first matching ActionProposal, or None if no clear intent.
    """
    text = f"{question} {answer}"

    for action_type, pattern in _PATTERNS:
        if pattern.search(text):
            title = _extract_title(question)
            if action_type == "jira_ticket":
                return ActionProposal(
                    action_type="jira_ticket",
                    label="Create Jira ticket",
                    description=f'Open a Jira ticket: "{title}"',
                    payload={"summary": title, "description": answer[:500]},
                )
            if action_type == "calendar_invite":
                return ActionProposal(
                    action_type="calendar_invite",
                    label="Draft calendar invite",
                    description="Draft a calendar invite from this conversation",
                    payload={"title": title, "description": answer[:300]},
                )
            if action_type == "slack_dm":
                return ActionProposal(
                    action_type="slack_dm",
                    label="Send Slack message",
                    description="Send a Slack message with this answer",
                    payload={"text": answer[:500]},
                )
    return None


async def execute_action(
    action_type: str,
    payload: dict,
    acl,        # ACLContext from rbac.py
    db,
) -> dict:
    """
    Run a confirmed action and audit-log it.
    Returns a result dict shown to the user in the chat UI.

    Stubs return success so the UI confirm → execute flow works without
    real Slack/Jira/Calendar credentials.
    Replace stubs with real outbound MCP client calls in Phase 2.
    """
    from access_control.audit import log_action

    try:
        await log_action(db=db, acl=acl, action_type=action_type)
    except Exception:
        pass

    stubs: dict[str, dict] = {
        "jira_ticket":    {"status": "created",  "ticket_id": "BRAIN-001", "url": "#"},
        "slack_dm":       {"status": "sent",      "channel": "direct-message"},
        "calendar_invite":{"status": "drafted",   "invite_id": "evt_001"},
    }
    return stubs.get(action_type, {"status": "executed", "action_type": action_type})


def _extract_title(text: str, max_len: int = 80) -> str:
    sentence = re.split(r"[.!?]", text.strip())[0].strip()
    return sentence[:max_len] if sentence else text[:max_len]
