import pandas as pd

from langchain_agent import ReActDataAnalysisAgent


df = pd.read_csv("data/sample_sales.csv")
agent = ReActDataAnalysisAgent(enable_memory=True)

agent.run("分析产品结构和销售贡献。", df)
agent.run("再分析地区和渠道的交叉表现。", df)

history = agent.get_memory_context()

print("=== Memory backend ===")
print(agent.memory_backend)

print("\n=== Conversation memory ===")
print(history)

assert "分析产品结构和销售贡献" in history
assert "地区和渠道" in history
assert "product_mix" in history
assert "channel_region" in history

print("\nMemory test passed.")
