from __future__ import annotations

from typing import Any, List

import pandas as pd

from langchain_agent import ReActDataAnalysisAgent

try:
    from langchain.agents import AgentExecutor, create_react_agent
    from langchain_core.prompts import PromptTemplate
    from langchain_core.tools import Tool

    LANGCHAIN_AGENTEXECUTOR_AVAILABLE = True
except Exception:
    AgentExecutor = None
    PromptTemplate = None
    Tool = None
    create_react_agent = None
    LANGCHAIN_AGENTEXECUTOR_AVAILABLE = False


def build_langchain_agent_executor(llm: Any, df: pd.DataFrame) -> Any:
    """
    Build a real LangChain AgentExecutor when LangChain and an LLM are available.

    The default Streamlit app still uses deterministic ReAct-style routing for stability.
    This factory exists to support a true AgentExecutor backend without breaking fallback mode.
    """
    if not LANGCHAIN_AGENTEXECUTOR_AVAILABLE:
        raise RuntimeError("LangChain AgentExecutor dependencies are not available.")

    router = ReActDataAnalysisAgent(enable_memory=False)

    def run_data_tool(question: str) -> str:
        output = router.run(question, df)
        return output.result.to_csv(index=False)

    tools: List[Any] = [
        Tool(
            name="deterministic_data_analysis_tool",
            func=run_data_tool,
            description=(
                "Use this tool for structured data analysis questions. "
                "It routes to safe Pandas, SQLite, or controlled Python tools and returns CSV results."
            ),
        )
    ]

    prompt = PromptTemplate.from_template(
        """You are a careful data analysis agent.

You must use tools for data calculation. Do not invent numbers.
After observing tool output, summarize the answer in business language.

Available tools:
{tools}

Use this format:

Question: the input question
Thought: decide what analysis is needed
Action: one of [{tool_names}]
Action Input: the user question
Observation: tool output
Thought: interpret the tool output
Final Answer: concise business explanation based only on the observation

Question: {input}
Thought:{agent_scratchpad}"""
    )

    agent = create_react_agent(llm=llm, tools=tools, prompt=prompt)
    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
    )
