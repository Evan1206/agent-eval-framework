from __future__ import annotations

import unittest

from agent_eval.costs import BudgetExceeded, CostTracker, validate_budget_pricing
from agent_eval.run import run_items
from agent_eval.testbank import Item


class UsageAgent:
    def respond(self, prompt: str) -> dict:
        return {
            "text": "done",
            "tool_calls": [],
            "usage": {"input_tokens": 10, "output_tokens": 5, "cost_usd": 0.02},
        }


class CostTests(unittest.TestCase):
    def test_budget_requires_api_pricing(self):
        with self.assertRaisesRegex(ValueError, "judge.input_cost_per_million_usd"):
            validate_budget_pricing(
                {
                    "max_budget_usd": 1,
                    "agent": {"type": "mock"},
                    "judge": {"type": "llm"},
                }
            )

    def test_budget_with_complete_pricing_is_allowed(self):
        validate_budget_pricing(
            {
                "max_budget_usd": 1,
                "agent": {"type": "mock"},
                "judge": {
                    "type": "llm",
                    "input_cost_per_million_usd": 1,
                    "output_cost_per_million_usd": 2,
                },
            }
        )

    def test_tracker_aggregates_roles(self):
        tracker = CostTracker(1.0)
        tracker.record(
            "agent", {"input_tokens": 10, "output_tokens": 5, "cost_usd": 0.1}
        )
        tracker.record(
            "judge", {"input_tokens": 20, "output_tokens": 4, "cost_usd": 0.2}
        )

        summary = tracker.as_dict()

        self.assertEqual(summary["calls"], 2)
        self.assertEqual(summary["input_tokens"], 30)
        self.assertEqual(summary["output_tokens"], 9)
        self.assertEqual(summary["cost_usd"], 0.3)

    def test_budget_excess_keeps_completed_agent_trace(self):
        tracker = CostTracker(0.01)
        traces = []

        with self.assertRaises(BudgetExceeded):
            run_items(
                UsageAgent(),
                [Item(id="one", prompt="prompt")],
                cost_tracker=tracker,
                traces=traces,
            )

        self.assertEqual(len(traces), 1)
        self.assertEqual(traces[0].agent_input_tokens, 10)
        self.assertEqual(traces[0].agent_output_tokens, 5)
        self.assertEqual(traces[0].agent_cost_usd, 0.02)
        self.assertTrue(tracker.as_dict()["budget_exceeded"])


if __name__ == "__main__":
    unittest.main()
