from langchain_executor_agent import LANGCHAIN_AGENTEXECUTOR_AVAILABLE, build_langchain_agent_executor

print("=== LangChain AgentExecutor optional backend ===")
print("AgentExecutor available:", LANGCHAIN_AGENTEXECUTOR_AVAILABLE)
assert callable(build_langchain_agent_executor)
print("LangChain AgentExecutor factory smoke test passed.")
