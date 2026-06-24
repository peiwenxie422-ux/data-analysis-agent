import pandas as pd

from langchain_agent import ReActDataAnalysisAgent


df = pd.read_csv("data/sample_sales.csv")
agent = ReActDataAnalysisAgent()

cases = [
    ("分析产品结构和销售贡献。", "product_mix"),
    ("分析地区和渠道的交叉表现。", "channel_region"),
    ("分析不同产品的客户效率。", "customer_efficiency"),
    ("检测销售额是否存在异常值。", "outlier"),
    ("分析这个数据集有没有缺失值。", "missing"),
    ("找出销售额最高的前3个产品。", "top_n"),
    ("按日期分析销售额环比增长率。", "period_comparison"),
    ("预测未来3天销售额趋势。", "forecast"),
]

print("=== LangChain/ReAct lightweight agent smoke test ===")
print(agent.list_tools())

for question, expected_task in cases:
    output = agent.run(question, df)

    print("\nQuestion:", question)
    print("Expected:", expected_task)
    print("Actual:", output.task_type)
    print("Tool:", output.tool_name)
    print("Elapsed:", output.elapsed_seconds)
    print(output.result.head())

    assert output.task_type == expected_task
    assert output.result is not None
    assert len(output.result) >= 1

print("\nAll langchain_agent tests passed.")
