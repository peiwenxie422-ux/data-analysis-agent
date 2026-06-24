from __future__ import annotations

from dataclasses import dataclass
from typing import List

import pandas as pd

from langchain_agent import AgentRunResult, ReActDataAnalysisAgent
from tools import get_column_candidates


@dataclass
class PipelineStep:
    name: str
    status: str
    detail: str


@dataclass
class MultiStepAnalysisResult:
    question: str
    steps: List[PipelineStep]
    agent_result: AgentRunResult
    chart_recommendation: str


def run_multistep_analysis(
    question: str,
    df: pd.DataFrame,
    agent: ReActDataAnalysisAgent | None = None,
) -> MultiStepAnalysisResult:
    """
    Explicit multi-step analysis pipeline:
    1. Profile dataframe schema
    2. Plan tool route
    3. Execute deterministic Pandas/SQL/Python tool
    4. Prepare chart recommendation
    5. Return structured trace for LLM explanation/UI
    """
    if agent is None:
        agent = ReActDataAnalysisAgent()

    steps: List[PipelineStep] = []

    candidates = get_column_candidates(df)
    steps.append(
        PipelineStep(
            name="data_profile",
            status="success",
            detail=(
                f"shape={df.shape}; categorical={candidates.get('categorical_columns', [])}; "
                f"numeric={candidates.get('numeric_columns', [])}; dates={candidates.get('date_columns', [])}"
            ),
        )
    )

    decision = agent.plan(question, df)
    steps.append(
        PipelineStep(
            name="tool_planning",
            status="success",
            detail=f"task_type={decision.task_type}; tool_name={decision.tool_name}",
        )
    )

    output = agent.run(question, df)
    steps.append(
        PipelineStep(
            name="tool_execution",
            status="success",
            detail=f"result_shape={output.result.shape}; elapsed_seconds={output.elapsed_seconds}",
        )
    )

    chart_recommendation = "table_only"
    if output.task_type in {"groupby", "top_n", "trend", "product_mix", "channel_region", "customer_efficiency", "period_comparison", "forecast"}:
        chart_recommendation = "table_and_chart"

    steps.append(
        PipelineStep(
            name="chart_planning",
            status="success",
            detail=f"recommendation={chart_recommendation}",
        )
    )

    steps.append(
        PipelineStep(
            name="llm_explanation_ready",
            status="success",
            detail="deterministic result is ready for Claude explanation",
        )
    )

    return MultiStepAnalysisResult(
        question=question,
        steps=steps,
        agent_result=output,
        chart_recommendation=chart_recommendation,
    )
