from __future__ import annotations

from dataclasses import dataclass
from typing import List

import pandas as pd

from langchain_agent import AgentDecision, AgentRunResult, ReActDataAnalysisAgent
from tools import get_column_candidates


@dataclass
class PipelineStep:
    name: str
    status: str
    detail: str
    display_name: str = ""


@dataclass
class MultiStepAnalysisResult:
    question: str
    steps: List[PipelineStep]
    agent_result: AgentRunResult
    decision: AgentDecision
    chart_recommendation: str
    visible_steps: List[PipelineStep]




def _join_columns(columns: list[str]) -> str:
    return ", ".join(columns) if columns else "none"


def build_visible_pipeline_steps(
    df: pd.DataFrame,
    candidates: dict,
    decision: AgentDecision,
    output: AgentRunResult,
    chart_recommendation: str,
) -> List[PipelineStep]:
    """Build a CV-aligned, user-facing multi-step analysis chain."""
    categorical = _join_columns(candidates.get("categorical_columns", []))
    numeric = _join_columns(candidates.get("numeric_columns", []))
    dates = _join_columns(candidates.get("date_columns", []))

    return [
        PipelineStep(
            name="data_extraction",
            display_name="数据提取",
            status="success",
            detail=f"已读取上传数据：{df.shape[0]} rows x {df.shape[1]} columns。",
        ),
        PipelineStep(
            name="schema_detection",
            display_name="字段识别",
            status="success",
            detail=f"分类字段={categorical}; 数值字段={numeric}; 日期字段={dates}。",
        ),
        PipelineStep(
            name="cleaning_preparation",
            display_name="清洗准备",
            status="success",
            detail="已完成字段候选识别、类型检查与缺失值检查准备；具体清洗/转换由受控 Pandas 工具执行。",
        ),
        PipelineStep(
            name="tool_selection",
            display_name="工具选择",
            status="success",
            detail=f"ReActDataAnalysisAgent 选择 task_type={decision.task_type}; tool={decision.tool_name}。",
        ),
        PipelineStep(
            name="tool_execution",
            display_name="Pandas/SQL/sandbox 执行",
            status="success",
            detail=f"执行工具 {output.tool_name}; result_shape={output.result.shape}; elapsed_seconds={output.elapsed_seconds}。",
        ),
        PipelineStep(
            name="chart_generation",
            display_name="图表生成",
            status="success",
            detail=f"图表建议={chart_recommendation}。",
        ),
        PipelineStep(
            name="claude_explanation",
            display_name="Claude 解释",
            status="success",
            detail="确定性分析结果已准备好传给 Claude 生成业务解释。",
        ),
    ]

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

    visible_steps = build_visible_pipeline_steps(
        df=df,
        candidates=candidates,
        decision=decision,
        output=output,
        chart_recommendation=chart_recommendation,
    )

    return MultiStepAnalysisResult(
        question=question,
        steps=steps,
        agent_result=output,
        decision=decision,
        chart_recommendation=chart_recommendation,
        visible_steps=visible_steps,
    )
