from __future__ import annotations

import statistics
import time
from typing import List

import pandas as pd

from langchain_agent import ReActDataAnalysisAgent


def percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0

    sorted_values = sorted(values)
    k = (len(sorted_values) - 1) * p
    lower = int(k)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = k - lower

    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def build_latency_questions() -> List[str]:
    return [
        "分析产品结构和销售贡献。",
        "分析地区和渠道的交叉表现。",
        "分析不同产品的客户效率。",
        "检测销售额是否存在异常值。",
        "分析这个数据集有没有缺失值。",
        "找出销售额最高的前3个产品。",
        "按日期分析销售额趋势。",
        "按地区汇总销售额。",
    ]


def run_latency_test(repeats: int = 5) -> pd.DataFrame:
    df = pd.read_csv("data/sample_sales.csv")
    agent = ReActDataAnalysisAgent()

    rows = []

    for _ in range(repeats):
        for question in build_latency_questions():
            start = time.perf_counter()
            output = agent.run(question, df)
            elapsed = round(time.perf_counter() - start, 4)

            rows.append(
                {
                    "question": question,
                    "task_type": output.task_type,
                    "tool_name": output.tool_name,
                    "elapsed_seconds": elapsed,
                    "result_rows": output.result.shape[0],
                    "result_cols": output.result.shape[1],
                }
            )

    return pd.DataFrame(rows)


def main() -> None:
    result = run_latency_test(repeats=5)
    values = result["elapsed_seconds"].tolist()

    avg_latency = statistics.mean(values)
    median_latency = statistics.median(values)
    p95_latency = percentile(values, 0.95)
    max_latency = max(values)

    print("=== Latency Test ===")
    print(f"Total runs: {len(values)}")
    print(f"Average latency: {avg_latency:.4f}s")
    print(f"Median latency: {median_latency:.4f}s")
    print(f"P95 latency: {p95_latency:.4f}s")
    print(f"Max latency: {max_latency:.4f}s")

    print("\n=== Per-task average latency ===")
    per_task = (
        result.groupby("task_type")["elapsed_seconds"]
        .agg(["count", "mean", "max"])
        .reset_index()
    )
    print(per_task.to_string(index=False))

    result.to_csv("latency_test_results.csv", index=False)
    print("\nSaved detailed results to latency_test_results.csv")

    if p95_latency <= 4.0:
        print("\nPASS: P95 tool-routing latency is within 4 seconds.")
    else:
        print("\nWARNING: P95 latency exceeds 4 seconds.")


if __name__ == "__main__":
    main()
