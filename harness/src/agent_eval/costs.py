"""Token usage and budget accounting for evaluation API calls."""
from __future__ import annotations

import dataclasses
from typing import Any


class BudgetExceeded(RuntimeError):
    """Raised immediately after a completed call crosses the configured budget."""


@dataclasses.dataclass
class UsageTotals:
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0

    def add(self, usage: dict[str, Any]) -> None:
        self.calls += 1
        self.input_tokens += int(usage.get("input_tokens", 0))
        self.output_tokens += int(usage.get("output_tokens", 0))
        self.cost_usd += float(usage.get("cost_usd", 0.0))

    def as_dict(self) -> dict[str, int | float]:
        return {
            "calls": self.calls,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost_usd": round(self.cost_usd, 8),
        }


class CostTracker:
    def __init__(self, max_budget_usd: float | None = None):
        if max_budget_usd is not None and float(max_budget_usd) < 0:
            raise ValueError("max_budget_usd must be non-negative")
        self.max_budget_usd = (
            float(max_budget_usd) if max_budget_usd is not None else None
        )
        self.by_role = {"agent": UsageTotals(), "judge": UsageTotals()}
        self.budget_exceeded = False

    @property
    def total_cost_usd(self) -> float:
        return sum(item.cost_usd for item in self.by_role.values())

    def record(self, role: str, usage: dict[str, Any]) -> None:
        if role not in self.by_role:
            raise ValueError(f"Unknown cost role: {role}")
        self.by_role[role].add(usage)
        if (
            self.max_budget_usd is not None
            and self.total_cost_usd > self.max_budget_usd
        ):
            self.budget_exceeded = True
            raise BudgetExceeded(
                f"max_budget_usd exceeded: {self.total_cost_usd:.8f} > "
                f"{self.max_budget_usd:.8f}"
            )

    def as_dict(self) -> dict[str, Any]:
        totals = UsageTotals()
        for usage in self.by_role.values():
            totals.calls += usage.calls
            totals.input_tokens += usage.input_tokens
            totals.output_tokens += usage.output_tokens
            totals.cost_usd += usage.cost_usd
        return {
            **totals.as_dict(),
            "max_budget_usd": self.max_budget_usd,
            "budget_exceeded": self.budget_exceeded,
            "by_role": {
                role: usage.as_dict() for role, usage in self.by_role.items()
            },
        }


def validate_budget_pricing(config: dict[str, Any]) -> None:
    """Ensure a configured budget has prices for every real API caller."""
    if config.get("max_budget_usd") is None:
        return
    callers: list[tuple[str, dict[str, Any]]] = []
    agent = config.get("agent") or {}
    if agent.get("type") in {"http", "anthropic_api"}:
        callers.append(("agent", agent))
    judge = config.get("judge") or {}
    if judge.get("type") == "llm":
        callers.append(("judge", judge))
    for role, caller in callers:
        for field in (
            "input_cost_per_million_usd",
            "output_cost_per_million_usd",
        ):
            if caller.get(field) is None:
                raise ValueError(
                    f"{role}.{field} is required when max_budget_usd is set"
                )
            if float(caller[field]) < 0:
                raise ValueError(f"{role}.{field} must be non-negative")
