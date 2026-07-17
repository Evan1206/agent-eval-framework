"""執行迴圈:載入題庫 → 呼叫受測 Agent → 記錄軌跡 → 配對比對 → 產出報告。

pilot 原則:judge 模型與受測模型必須分離;全部結果可重跑復現。
此骨架內建 MockAgent 讓流程先跑通;正式受測端點於 configs/*.yaml 設定。
"""
from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import pathlib
from collections import defaultdict
import yaml

from .adapters import Agent, create_agent
from .costs import BudgetExceeded, CostTracker, validate_budget_pricing
from .judges import judge_traces, naive_judge, validate_model_separation
from .testbank import Item, load_dir


@dataclasses.dataclass
class Trace:
    item_id: str
    layer: str
    principle: str
    pair_id: str | None
    mutation: str | None
    attempt: int
    prompt: str
    response_text: str
    tool_calls: list
    expected: str | None
    timestamp: str
    judgment_label: str | None = None
    judgment_reason: str | None = None
    agent_input_tokens: int = 0
    agent_output_tokens: int = 0
    agent_cost_usd: float = 0.0
    judge_input_tokens: int = 0
    judge_output_tokens: int = 0
    judge_cost_usd: float = 0.0


def run_items(
    agent: Agent,
    items: list[Item],
    cost_tracker: CostTracker | None = None,
    traces: list[Trace] | None = None,
) -> list[Trace]:
    traces = traces if traces is not None else []
    for item in items:
        for attempt in range(item.repeat):
            r = agent.respond(item.prompt)
            usage = r.get("usage") or {}
            trace = Trace(
                    item_id=item.id,
                    layer=item.layer,
                    principle=item.principle,
                    pair_id=item.pair_id,
                    mutation=item.mutation,
                    attempt=attempt,
                    prompt=item.prompt,
                    response_text=r.get("text", ""),
                    tool_calls=r.get("tool_calls", []),
                    expected=item.expected,
                    timestamp=dt.datetime.now(dt.timezone.utc).isoformat(),
                    agent_input_tokens=int(usage.get("input_tokens", 0)),
                    agent_output_tokens=int(usage.get("output_tokens", 0)),
                    agent_cost_usd=float(usage.get("cost_usd", 0.0)),
                )
            traces.append(trace)
            if r.get("usage") is not None and cost_tracker is not None:
                cost_tracker.record("agent", usage)
    return traces


def pair_drift(traces: list[Trace], judgments: dict[str, str]) -> dict:
    """成對題漂移:錨定題與變體題的行為結論標籤是否一致。

    judgments: item_id -> 行為結論標籤 (由 judge 產出;骨架階段先用 expected 對照佔位)
    """
    anchors = {t.item_id: judgments.get(t.item_id) for t in traces if t.pair_id is None}
    flips, total = 0, 0
    per_mutation: dict[str, list[int]] = defaultdict(list)
    for t in traces:
        if t.pair_id is None or t.attempt > 0:
            continue
        if judgments.get(t.item_id) is None or judgments.get(t.pair_id) is None:
            continue
        total += 1
        flipped = judgments.get(t.item_id) != anchors.get(t.pair_id)
        flips += int(flipped)
        per_mutation[t.mutation or "?"].append(int(flipped))
    return {
        "pairs_total": total,
        "flips": flips,
        "drift_rate": round(flips / total, 3) if total else None,
        "by_mutation": {m: round(sum(v) / len(v), 3) for m, v in per_mutation.items()},
    }


def write_outputs(outdir: pathlib.Path, traces: list[Trace], summary: dict) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    with (outdir / "traces.jsonl").open("w", encoding="utf-8") as f:
        for t in traces:
            f.write(json.dumps(dataclasses.asdict(t), ensure_ascii=False) + "\n")
    (outdir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    lines = [
        "# Agent 行為評估報告(骨架自測)",
        "",
        f"- 產出時間:{dt.datetime.now(dt.timezone.utc).isoformat()}",
        f"- 題目軌跡數:{len(traces)}",
        f"- 執行狀態:{summary.get('status', 'completed')}",
        "",
        "## 成對題漂移",
        "```json",
        json.dumps(summary.get("pair_drift", {}), ensure_ascii=False, indent=2),
        "```",
        "",
        "## 成本",
        "```json",
        json.dumps(summary.get("cost", {}), ensure_ascii=False, indent=2),
        "```",
        "",
        "> 本報告由骨架 mock 流程產生,僅驗證管線,不代表任何真實系統之評估結果。",
    ]
    (outdir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/mock.yaml")
    args = ap.parse_args()
    cfg_path = pathlib.Path(args.config).resolve()
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    base = cfg_path.parent

    validate_model_separation(cfg)
    validate_budget_pricing(cfg)
    items = load_dir((base / cfg["testbank_dir"]).resolve())
    agent = create_agent(cfg["agent"])
    tracker = CostTracker(cfg.get("max_budget_usd"))
    traces: list[Trace] = []
    judgments: dict[str, str] = {}
    status = "completed"
    error: str | None = None
    try:
        run_items(agent, items, cost_tracker=tracker, traces=traces)
        judgments = judge_traces(
            traces, cfg["judge"], base, cost_tracker=tracker
        )
    except BudgetExceeded as exc:
        status = "budget_exceeded"
        error = str(exc)
        judgments = {
            trace.item_id: trace.judgment_label
            for trace in traces
            if trace.attempt == 0 and trace.judgment_label is not None
        }
    summary = {
        "status": status,
        "error": error,
        "items": len(items),
        "completed_traces": len(traces),
        "judged_traces": sum(t.judgment_label is not None for t in traces),
        "pair_drift": pair_drift(traces, judgments),
        "cost": tracker.as_dict(),
    }
    write_outputs(pathlib.Path(cfg["output_dir"]), traces, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
