"""Tool routing and execution orchestration for ALIFE."""

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from brain.providers.ollama_provider import OllamaProvider
from tools.base import ToolResult
from tools.builtin.shutdown import perform_shutdown
from tools.config import resolve_application, resolve_website
from tools.confirmation import ConfirmationManager, PendingConfirmation
from tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

SHUTDOWN_RULE_PATTERNS = (
    r"\bshut\s+down\b",
    r"\bshutdown\b",
    r"\bturn\s+off\s+my\s+(laptop|computer)\b",
)

SHUTDOWN_NEGATION_PATTERNS = (
    r"\bdon'?t\b",
    r"\bdo\s+not\b",
    r"\bnever\b",
    r"\bcancel\b",
)

CLAUSE_SPLIT_PATTERN = re.compile(
    r"\b(?:and then|then|after that|also|,|;|&|and)\b",
    re.IGNORECASE,
)

OPEN_INTENT_PATTERN = re.compile(
    r"\b(open|launch|go to|start|visit)\b",
    re.IGNORECASE,
)

SITE_NAMES = ("youtube", "leetcode", "google", "github")
APP_ALIASES: tuple[tuple[str, str], ...] = (
    ("visual studio code", "vscode"),
    ("vs code", "vscode"),
    ("vscode", "vscode"),
    ("google chrome", "chrome"),
    ("chrome", "chrome"),
    ("whatsapp", "whatsapp"),
)


@dataclass(frozen=True)
class ToolDecision:
    """Decision produced by the tool router."""

    action: str
    name: str | None = None
    arguments: dict[str, Any] | None = None
    source: str = "unknown"


class ToolOrchestrator:
    """Decides when to use tools and executes approved actions safely."""

    def __init__(
        self,
        provider: OllamaProvider,
        registry: ToolRegistry,
        confirmation_manager: ConfirmationManager,
    ) -> None:
        """Initialize the tool orchestrator."""
        self._provider = provider
        self._registry = registry
        self._confirmation_manager = confirmation_manager

    def try_handle(self, user_message: str) -> ToolResult | None:
        """Route a user message to one or more safe registered tools.

        Returns:
            Combined tool result if at least one tool was selected, otherwise ``None``.
        """
        decisions = self._collect_decisions(user_message)
        if not decisions:
            return None

        results: list[ToolResult] = []
        seen: set[tuple[str, str]] = set()

        for decision in decisions:
            if decision.action != "tool" or not decision.name:
                continue
            if decision.name == "request_shutdown" and decision.source != "rule":
                logger.warning(
                    "Blocked shutdown tool selection from non-rule source=%s",
                    decision.source,
                )
                continue

            identity = (
                decision.name,
                json.dumps(decision.arguments or {}, sort_keys=True),
            )
            if identity in seen:
                logger.info("Skipping duplicate tool decision: %s", identity)
                continue
            seen.add(identity)

            result = self._registry.execute(decision.name, decision.arguments or {})
            if result.requires_confirmation:
                self._confirmation_manager.set_pending(
                    PendingConfirmation(
                        tool_name=decision.name,
                        arguments=decision.arguments or {},
                        prompt=result.message,
                        execute_callback=self._build_confirmation_callback(
                            decision.name
                        ),
                    )
                )
            results.append(result)

        if not results:
            return None
        return self._combine_results(results)

    def _combine_results(self, results: list[ToolResult]) -> ToolResult:
        """Merge sequential tool results into a single response."""
        messages = [result.message for result in results if result.message]
        combined_data: dict[str, Any] = {"actions": [result.data for result in results]}
        return ToolResult(
            success=all(result.success for result in results),
            message=" ".join(messages),
            data=combined_data,
            requires_confirmation=any(result.requires_confirmation for result in results),
        )

    def _build_confirmation_callback(self, tool_name: str):
        def _callback() -> str:
            if tool_name == "request_shutdown":
                return perform_shutdown()
            return "The requested action is not available."

        return _callback

    def _collect_decisions(self, user_message: str) -> list[ToolDecision]:
        """Collect unique tool decisions for a user message."""
        decisions: list[ToolDecision] = []
        inherit_open = OPEN_INTENT_PATTERN.search(user_message) is not None
        clauses = self._split_clauses(user_message)
        for clause in clauses:
            decision = self._rule_based_decision(clause, inherit_open=inherit_open)
            if decision is not None:
                decisions.append(decision)

        if decisions:
            return decisions

        llm_decision = self._llm_decision(user_message)
        if llm_decision is None:
            return []
        if llm_decision.action != "tool":
            return []
        return [llm_decision]

    def _split_clauses(self, user_message: str) -> list[str]:
        """Split a request into independent action clauses."""
        parts = [
            part.strip()
            for part in CLAUSE_SPLIT_PATTERN.split(user_message)
            if part and part.strip()
        ]
        return parts or [user_message]

    def _rule_based_decision(
        self,
        user_message: str,
        inherit_open: bool = False,
    ) -> ToolDecision | None:
        """Apply simple deterministic routing for a single clause."""
        text = user_message.strip().lower()
        cleaned = re.sub(r"[^a-z0-9\s]", " ", text)
        cleaned = re.sub(
            r"\b(alife|please|can you|could you|would you|for me)\b",
            " ",
            cleaned,
        )
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        if any(
            phrase in text
            for phrase in ("what time is it", "current time", "tell me the time", "what's the time", "whats the time")
        ):
            return ToolDecision(action="tool", name="get_time", arguments={}, source="rule")

        if any(
            phrase in text
            for phrase in ("system info", "system information", "about my computer")
        ):
            return ToolDecision(action="tool", name="system_info", arguments={}, source="rule")

        if self._is_explicit_shutdown_request(text):
            return ToolDecision(
                action="tool",
                name="request_shutdown",
                arguments={},
                source="rule",
            )

        if inherit_open or OPEN_INTENT_PATTERN.search(text):
            site_decision = self._match_website(cleaned)
            if site_decision is not None:
                return site_decision
            app_decision = self._match_application(cleaned)
            if app_decision is not None:
                return app_decision

        return None

    def _match_website(self, cleaned: str) -> ToolDecision | None:
        """Return a website tool decision if a known site is mentioned."""
        compact = cleaned.replace(" ", "")
        for site in SITE_NAMES:
            if site in compact:
                if resolve_website(site) is None:
                    continue
                return ToolDecision(
                    action="tool",
                    name="open_website",
                    arguments={"site": site},
                    source="rule",
                )
        return None

    def _match_application(self, cleaned: str) -> ToolDecision | None:
        """Return an application tool decision if a known app is mentioned."""
        compact = cleaned.replace(" ", "")
        for alias, app_name in APP_ALIASES:
            if alias.replace(" ", "") in compact:
                if resolve_application(app_name) is None:
                    continue
                return ToolDecision(
                    action="tool",
                    name="open_application",
                    arguments={"app": app_name},
                    source="rule",
                )
        return None

    def _is_explicit_shutdown_request(self, text: str) -> bool:
        """Return True only for explicit shutdown intent, not negated requests."""
        if any(re.search(pattern, text) for pattern in SHUTDOWN_NEGATION_PATTERNS):
            return False
        return any(re.search(pattern, text) for pattern in SHUTDOWN_RULE_PATTERNS)

    def _llm_decision(self, user_message: str) -> ToolDecision | None:
        """Ask the LLM to choose a safe registered tool when rules do not match."""
        routing_prompt = f"""
You are ALIFE's tool router.

Available tools:
{self._registry.describe_tools()}

If the user request requires one or more of these tools, respond with ONLY JSON:
{{"action":"tool","name":"<tool_name>","arguments":{{}}}}

If no tool is needed, respond with ONLY JSON:
{{"action":"chat"}}

Never select request_shutdown. Never invent tool names. Never invent websites or applications.

User request:
{user_message}
""".strip()

        try:
            raw = self._provider.generate(routing_prompt)
        except Exception as exc:
            logger.warning("Tool routing via LLM failed: %s", exc)
            return None

        payload = self._extract_json(raw)
        if payload is None:
            logger.warning("Tool routing produced invalid JSON")
            return None

        action = str(payload.get("action", "")).lower()
        if action != "tool":
            return ToolDecision(action="chat", source="llm")

        name = str(payload.get("name", "")).strip().lower()
        if name == "request_shutdown":
            logger.warning("Blocked LLM attempt to select request_shutdown")
            return ToolDecision(action="chat", source="llm")

        if self._registry.get(name) is None:
            logger.warning("Blocked unknown LLM tool name=%s", name)
            return ToolDecision(action="chat", source="llm")

        arguments = payload.get("arguments") or {}
        if not isinstance(arguments, dict):
            arguments = {}

        if name == "open_website":
            site = str(arguments.get("site", ""))
            if resolve_website(site) is None:
                return None

        if name == "open_application":
            app = str(arguments.get("app", ""))
            if resolve_application(app) is None:
                return None

        if name:
            return ToolDecision(
                action="tool",
                name=name,
                arguments=arguments,
                source="llm",
            )
        return ToolDecision(action="chat", source="llm")

    def _extract_json(self, text: str) -> dict[str, Any] | None:
        """Extract a JSON object from model output."""
        if not isinstance(text, str):
            return None
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return None
        try:
            payload = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
        return payload if isinstance(payload, dict) else None
