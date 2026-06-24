from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import pandas as pd

from langchain_agent import ReActDataAnalysisAgent


@dataclass
class IntentEvalCase:
    question: str
    expected_task: str


def build_eval_cases() -> List[IntentEvalCase]:
    return [
        IntentEvalCase("分析产品结构和销售贡献。", "product_mix"),
        IntentEvalCase("看一下各产品的销售贡献占比。", "product_mix"),
        IntentEvalCase("帮我做一个产品 ABC 分类分析。", "product_mix"),
        IntentEvalCase("不同品类的销售结构怎么样？", "product_mix"),

        IntentEvalCase("分析地区和渠道的交叉表现。", "channel_region"),
        IntentEvalCase("不同区域在线上和线下渠道的销售差异。", "channel_region"),
        IntentEvalCase("帮我看 region 和 channel 的销售矩阵。", "channel_region"),
        IntentEvalCase("各地区不同渠道表现如何？", "channel_region"),

        IntentEvalCase("分析不同产品的客户效率。", "customer_efficiency"),
        IntentEvalCase("看一下各产品的人均销售额。", "customer_efficiency"),
        IntentEvalCase("不同产品的客户贡献和客单价怎么样？", "customer_efficiency"),
        IntentEvalCase("帮我比较不同品类的客效。", "customer_efficiency"),

        IntentEvalCase("分析这个数据集有没有缺失值。", "missing"),
        IntentEvalCase("检查一下数据里有没有空值。", "missing"),
        IntentEvalCase("哪些字段存在 missing value？", "missing"),
        IntentEvalCase("帮我看一下 null 数据情况。", "missing"),

        IntentEvalCase("检测销售额是否存在异常值。", "outlier"),
        IntentEvalCase("sales 里面有没有离群点？", "outlier"),
        IntentEvalCase("帮我找出极端销售额。", "outlier"),
        IntentEvalCase("检查一下收入字段是否有 outlier。", "outlier"),

        IntentEvalCase("找出销售额最高的前3个产品。", "top_n"),
        IntentEvalCase("top 5 产品有哪些？", "top_n"),
        IntentEvalCase("销售额排名最高的品类。", "top_n"),
        IntentEvalCase("按销售额排序，找出前几名。", "top_n"),

        IntentEvalCase("按日期分析销售额环比增长率。", "period_comparison"),
        IntentEvalCase("销售额同比增长情况怎么样？", "period_comparison"),
        IntentEvalCase("和上期相比销售额变化如何？", "period_comparison"),
        IntentEvalCase("sales mom growth 分析。", "period_comparison"),

        IntentEvalCase("预测未来3天销售额趋势。", "forecast"),
        IntentEvalCase("帮我预估未来销售额走势。", "forecast"),
        IntentEvalCase("forecast sales trend for next periods.", "forecast"),
        IntentEvalCase("未来几天 sales 会怎么变化？", "forecast"),

        IntentEvalCase("按日期分析销售额趋势。", "trend"),
        IntentEvalCase("销售额随时间变化趋势如何？", "trend"),
        IntentEvalCase("帮我看每天 sales 的变化。", "trend"),
        IntentEvalCase("分析时间维度下的收入趋势。", "trend"),

        IntentEvalCase("按地区汇总销售额。", "groupby"),
        IntentEvalCase("不同渠道的销售额统计。", "groupby"),
        IntentEvalCase("按照产品分组计算平均销售额。", "groupby"),
        IntentEvalCase("帮我按区域聚合销售数据。", "groupby"),

        IntentEvalCase(
            "SELECT product, SUM(sales) AS sales_sum FROM sales_data GROUP BY product",
            "sql",
        ),
        IntentEvalCase(
            "WITH t AS (SELECT * FROM sales_data) SELECT COUNT(*) AS n FROM t",
            "sql",
        ),
    ]


def evaluate_intent(df: pd.DataFrame) -> pd.DataFrame:
    agent = ReActDataAnalysisAgent()
    rows: List[Dict[str, object]] = []

    for case in build_eval_cases():
        predicted = agent.infer_task_type(case.question, df)
        rows.append(
            {
                "question": case.question,
                "expected_task": case.expected_task,
                "predicted_task": predicted,
                "correct": predicted == case.expected_task,
            }
        )

    return pd.DataFrame(rows)


def main() -> None:
    df = pd.read_csv("data/sample_sales.csv")
    result = evaluate_intent(df)

    total = len(result)
    correct = int(result["correct"].sum())
    accuracy = correct / total if total else 0.0

    print("=== Intent Recognition Evaluation ===")
    print(f"Total cases: {total}")
    print(f"Correct: {correct}")
    print(f"Accuracy: {accuracy:.2%}")

    print("\n=== Per-task accuracy ===")
    per_task = (
        result.groupby("expected_task")["correct"]
        .agg(["count", "sum", "mean"])
        .rename(columns={"count": "total", "sum": "correct", "mean": "accuracy"})
        .reset_index()
    )
    per_task["accuracy"] = per_task["accuracy"].map(lambda x: f"{x:.2%}")
    print(per_task.to_string(index=False))

    print("\n=== Failed cases ===")
    failed = result[~result["correct"]]
    if failed.empty:
        print("No failed cases.")
    else:
        print(failed.to_string(index=False))

    result.to_csv("intent_eval_results.csv", index=False)
    print("\nSaved detailed results to intent_eval_results.csv")


if __name__ == "__main__":
    main()
