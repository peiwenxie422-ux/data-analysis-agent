import pandas as pd

from analysis_pipeline import run_multistep_analysis


df = pd.read_csv("data/sample_sales.csv")
output = run_multistep_analysis("预测未来3天销售额趋势。", df)

print("=== Multi-step analysis pipeline ===")
for step in output.steps:
    print(step.name, step.status, step.detail)

print("\n=== Visible business pipeline ===")
for step in output.visible_steps:
    print(step.display_name, step.status, step.detail)

assert output.agent_result.task_type == "forecast"
assert output.decision.task_type == "forecast"
assert output.agent_result.tool_name == output.decision.tool_name
assert len(output.steps) >= 5
expected_visible_steps = [
    "数据提取",
    "字段识别",
    "清洗准备",
    "工具选择",
    "Pandas/SQL/sandbox 执行",
    "图表生成",
    "Claude 解释",
]
assert [step.display_name for step in output.visible_steps] == expected_visible_steps
assert output.chart_recommendation == "table_and_chart"

print("\nMulti-step analysis pipeline test passed.")
