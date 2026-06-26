import pandas as pd

from analysis_pipeline import run_multistep_analysis


df = pd.read_csv("data/sample_sales.csv")
output = run_multistep_analysis("预测未来3天销售额趋势。", df)

print("=== Multi-step analysis pipeline ===")
for step in output.steps:
    print(step.name, step.status, step.detail)

assert output.agent_result.task_type == "forecast"
assert output.decision.task_type == "forecast"
assert output.agent_result.tool_name == output.decision.tool_name
assert len(output.steps) >= 5
assert output.chart_recommendation == "table_and_chart"

print("\nMulti-step analysis pipeline test passed.")
