from __future__ import annotations

import re
import time
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

import pandas as pd

from conversation_memory import SimpleConversationBufferMemory

from tools import (
    get_column_candidates,
    groupby_aggregate,
    top_n,
    trend_analysis,
    missing_value_summary,
    outlier_detection,
    product_mix_analysis,
    channel_region_matrix,
    customer_efficiency_analysis,
    period_comparison_analysis,
    trend_forecast_analysis,
)

try:
    from sql_tools import run_readonly_sql
except Exception:
    run_readonly_sql = None

try:
    from langchain_core.tools import StructuredTool
    LANGCHAIN_AVAILABLE = True
except Exception:
    StructuredTool = None
    LANGCHAIN_AVAILABLE = False


try:
    from langchain.memory import ConversationBufferMemory
    LANGCHAIN_MEMORY_AVAILABLE = True
except Exception:
    ConversationBufferMemory = None
    LANGCHAIN_MEMORY_AVAILABLE = False

@dataclass
class AgentDecision:
    task_type: str
    tool_name: str
    group_col: Optional[str] = None
    value_col: Optional[str] = None
    date_col: Optional[str] = None
    channel_col: Optional[str] = None
    customer_col: Optional[str] = None
    top_n: Optional[int] = None


@dataclass
class AgentRunResult:
    question: str
    task_type: str
    tool_name: str
    result: pd.DataFrame
    elapsed_seconds: float
    reasoning_trace: List[str]
    langchain_available: bool

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["result"] = self.result.to_dict(orient="records")
        return d


class ReActDataAnalysisAgent:
    """
    Lightweight LangChain/ReAct-style data analysis agent.

    设计目的：
    1. 保留 ReAct 的 Thought -> Action -> Observation 工作范式；
    2. 将自然语言问题路由到 Pandas / SQL / Matplotlib 相关工具；
    3. 支撑简历中 LangChain Agent / ReAct / tool calling 的项目说法；
    4. 即使本地没有安装 LangChain，也可以用 fallback 模式完成测试。
    """

    def __init__(self, enable_memory: bool = True) -> None:
        self.tool_registry = self._build_tool_registry()
        self.enable_memory = enable_memory

        if enable_memory and LANGCHAIN_MEMORY_AVAILABLE:
            self.memory = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=False,
            )
            self.memory_backend = "langchain.ConversationBufferMemory"
        elif enable_memory:
            self.memory = SimpleConversationBufferMemory(max_turns=20)
            self.memory_backend = "SimpleConversationBufferMemory"
        else:
            self.memory = None
            self.memory_backend = "disabled"

    def _build_tool_registry(self) -> List[Dict[str, str]]:
        return [
            {
                "name": "product_mix_analysis",
                "description": "Analyze product sales contribution, cumulative share and ABC classification.",
            },
            {
                "name": "channel_region_matrix",
                "description": "Analyze cross performance between region and channel.",
            },
            {
                "name": "customer_efficiency_analysis",
                "description": "Analyze sales efficiency by product, including sales per customer and order value.",
            },
            {
                "name": "groupby_aggregate",
                "description": "Aggregate numeric KPI by categorical dimension.",
            },
            {
                "name": "top_n",
                "description": "Return top N categories by selected numeric KPI.",
            },
            {
                "name": "period_comparison_analysis",
                "description": "Analyze period-over-period or year-over-year KPI growth.",
            },
            {
                "name": "trend_forecast_analysis",
                "description": "Forecast future KPI trend using simple deterministic extrapolation.",
            },
            {
                "name": "trend_analysis",
                "description": "Analyze KPI trend by date column.",
            },
            {
                "name": "missing_value_summary",
                "description": "Check missing value count and missing rate by field.",
            },
            {
                "name": "outlier_detection",
                "description": "Detect numeric outliers using IQR rule.",
            },
            {
                "name": "readonly_sql_query",
                "description": "Execute SELECT/WITH-only SQL query against uploaded dataframe.",
            },
        ]

    def get_memory_context(self) -> str:
        if self.memory is None:
            return ""

        memory_vars = self.memory.load_memory_variables({})
        return memory_vars.get("chat_history", "")

    def clear_memory(self) -> None:
        if self.memory is not None:
            self.memory.clear()

    def list_tools(self) -> pd.DataFrame:
        return pd.DataFrame(self.tool_registry)

    def _contains_any(self, text: str, keywords: List[str]) -> bool:
        return any(k in text for k in keywords)

    def infer_task_type(self, question: str, df: pd.DataFrame) -> str:
        q = question.lower()

        if self._contains_any(q, ["缺失", "missing", "null", "na", "空值"]):
            return "missing"

        if self._contains_any(q, ["异常", "离群", "极端值", "极端", "outlier"]):
            return "outlier"

        if self._contains_any(q, ["预测", "预估", "未来", "forecast", "future"]):
            return "forecast"

        if self._contains_any(q, ["同比", "环比", "增长率", "较上期", "比上期", "和上期", "mom", "yoy"]):
            return "period_comparison"

        if self._contains_any(q, ["趋势", "trend", "按日期", "时间变化", "变化趋势", "每天", "每日", "变化"]):
            return "trend"

        if self._contains_any(q, ["客户效率", "客效", "人均", "客户贡献", "客户产出"]):
            return "customer_efficiency"

        if (
            self._contains_any(q, ["地区", "区域", "region"])
            and self._contains_any(q, ["渠道", "channel"])
        ) or self._contains_any(q, ["交叉", "矩阵"]):
            return "channel_region"

        if self._contains_any(q, ["top", "前", "最高", "排名", "最大"]):
            return "top_n"

        if self._contains_any(q, ["产品结构", "产品组合", "abc", "贡献", "品类", "销售贡献"]):
            return "product_mix"

        if q.strip().startswith("select") or q.strip().startswith("with"):
            return "sql"

        return "groupby"

    def _infer_value_col(self, question: str, df: pd.DataFrame) -> Optional[str]:
        q = question.lower()
        numeric_cols = df.select_dtypes(include="number").columns.tolist()

        aliases = {
            "sales": ["sales", "销售额", "销售", "收入", "营收", "gmv"],
            "quantity": ["quantity", "销量", "数量", "销售量"],
            "customer_count": ["customer_count", "客户数", "客户", "客流", "顾客数"],
        }

        for col, words in aliases.items():
            if col in df.columns and any(w in q for w in words):
                return col

        if "sales" in df.columns:
            return "sales"

        return numeric_cols[0] if numeric_cols else None

    def _infer_group_col(self, question: str, df: pd.DataFrame) -> Optional[str]:
        q = question.lower()

        aliases = {
            "product": ["product", "产品", "品类", "商品", "sku"],
            "region": ["region", "地区", "区域", "城市"],
            "channel": ["channel", "渠道", "来源"],
        }

        for col, words in aliases.items():
            if col in df.columns and any(w in q for w in words):
                return col

        candidates = get_column_candidates(df).get("categorical_columns", [])
        return candidates[0] if candidates else None

    def _infer_date_col(self, df: pd.DataFrame) -> Optional[str]:
        candidates = get_column_candidates(df).get("date_columns", [])
        if candidates:
            return candidates[0]

        for col in df.columns:
            low = col.lower()
            if "date" in low or "time" in low or "日期" in col or "时间" in col:
                return col

        return None

    def _infer_channel_col(self, df: pd.DataFrame) -> Optional[str]:
        if "channel" in df.columns:
            return "channel"

        for col in df.columns:
            if "channel" in col.lower() or "渠道" in col:
                return col

        return None

    def _infer_customer_col(self, df: pd.DataFrame) -> Optional[str]:
        if "customer_count" in df.columns:
            return "customer_count"

        for col in df.columns:
            low = col.lower()
            if "customer" in low or "客户" in col or "顾客" in col:
                return col

        return None

    def _infer_top_n(self, question: str, default: int = 3) -> int:
        patterns = [
            r"top\s*(\d+)",
            r"前\s*(\d+)",
            r"最高的?\s*(\d+)",
            r"最大的?\s*(\d+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, question.lower())
            if match:
                return int(match.group(1))

        return default

    def plan(self, question: str, df: pd.DataFrame) -> AgentDecision:
        task_type = self.infer_task_type(question, df)
        value_col = self._infer_value_col(question, df)
        group_col = self._infer_group_col(question, df)
        date_col = self._infer_date_col(df)
        channel_col = self._infer_channel_col(df)
        customer_col = self._infer_customer_col(df)
        n = self._infer_top_n(question)

        tool_map = {
            "product_mix": "product_mix_analysis",
            "channel_region": "channel_region_matrix",
            "customer_efficiency": "customer_efficiency_analysis",
            "missing": "missing_value_summary",
            "outlier": "outlier_detection",
            "period_comparison": "period_comparison_analysis",
            "forecast": "trend_forecast_analysis",
            "trend": "trend_analysis",
            "top_n": "top_n",
            "sql": "readonly_sql_query",
            "groupby": "groupby_aggregate",
        }

        return AgentDecision(
            task_type=task_type,
            tool_name=tool_map.get(task_type, "groupby_aggregate"),
            group_col=group_col,
            value_col=value_col,
            date_col=date_col,
            channel_col=channel_col,
            customer_col=customer_col,
            top_n=n,
        )

    def run(self, question: str, df: pd.DataFrame) -> AgentRunResult:
        start = time.perf_counter()
        decision = self.plan(question, df)

        trace = [
            f"Thought: user asks for {decision.task_type} analysis.",
            f"Action: select tool `{decision.tool_name}`.",
        ]

        if decision.task_type == "product_mix":
            product_col = "product" if "product" in df.columns else decision.group_col
            if product_col is None or decision.value_col is None:
                raise ValueError("Product mix analysis requires product and numeric value columns.")
            result = product_mix_analysis(df, product_col=product_col, value_col=decision.value_col)

        elif decision.task_type == "channel_region":
            region_col = "region" if "region" in df.columns else decision.group_col
            channel_col = decision.channel_col
            if region_col is None or channel_col is None or decision.value_col is None:
                raise ValueError("Channel-region analysis requires region, channel and numeric value columns.")
            result = channel_region_matrix(
                df,
                region_col=region_col,
                channel_col=channel_col,
                value_col=decision.value_col,
            )

        elif decision.task_type == "customer_efficiency":
            group_col = "product" if "product" in df.columns else decision.group_col
            if group_col is None or decision.value_col is None or decision.customer_col is None:
                raise ValueError("Customer efficiency analysis requires group, sales and customer columns.")
            result = customer_efficiency_analysis(
                df,
                group_col=group_col,
                value_col=decision.value_col,
                customer_col=decision.customer_col,
            )

        elif decision.task_type == "missing":
            result = missing_value_summary(df)

        elif decision.task_type == "outlier":
            if decision.value_col is None:
                raise ValueError("Outlier detection requires a numeric value column.")
            result = outlier_detection(df, value_col=decision.value_col)

        elif decision.task_type == "period_comparison":
            if decision.date_col is None or decision.value_col is None:
                raise ValueError("Period comparison analysis requires date and numeric value columns.")
            q = question.lower()
            period_type = "yoy" if self._contains_any(q, ["同比", "yoy"]) else "mom"
            freq = "ME" if self._contains_any(q, ["月", "monthly", "month", "同比"]) else "D"
            result = period_comparison_analysis(
                df,
                date_col=decision.date_col,
                value_col=decision.value_col,
                freq=freq,
                period_type=period_type,
            )

        elif decision.task_type == "forecast":
            if decision.date_col is None or decision.value_col is None:
                raise ValueError("Forecast analysis requires date and numeric value columns.")
            q = question.lower()
            freq = "ME" if self._contains_any(q, ["月", "monthly", "month"]) else "D"
            result = trend_forecast_analysis(
                df,
                date_col=decision.date_col,
                value_col=decision.value_col,
                periods=3,
                freq=freq,
            )

        elif decision.task_type == "trend":
            if decision.date_col is None or decision.value_col is None:
                raise ValueError("Trend analysis requires date and numeric value columns.")
            result = trend_analysis(df, date_col=decision.date_col, value_col=decision.value_col)

        elif decision.task_type == "top_n":
            if decision.group_col is None or decision.value_col is None:
                raise ValueError("Top N analysis requires group and numeric value columns.")
            result = top_n(
                df,
                group_col=decision.group_col,
                value_col=decision.value_col,
                n=decision.top_n or 3,
            )

        elif decision.task_type == "sql":
            if run_readonly_sql is None:
                raise RuntimeError("sql_tools.run_readonly_sql is unavailable.")
            result, _ = run_readonly_sql(df, question)

        else:
            if decision.group_col is None or decision.value_col is None:
                raise ValueError("Groupby analysis requires group and numeric value columns.")
            result = groupby_aggregate(
                df,
                group_col=decision.group_col,
                value_col=decision.value_col,
            )

        elapsed = round(time.perf_counter() - start, 4)

        trace.append(
            f"Observation: tool returned {len(result)} rows and {len(result.columns)} columns in {elapsed}s."
        )

        if self.memory is not None:
            memory_output = (
                f"task_type={decision.task_type}; "
                f"tool_name={decision.tool_name}; "
                f"result_shape={len(result)}x{len(result.columns)}; "
                f"elapsed_seconds={elapsed}"
            )
            self.memory.save_context(
                {"input": question},
                {"output": memory_output},
            )

        return AgentRunResult(
            question=question,
            task_type=decision.task_type,
            tool_name=decision.tool_name,
            result=result,
            elapsed_seconds=elapsed,
            reasoning_trace=trace,
            langchain_available=LANGCHAIN_AVAILABLE,
        )

    def build_langchain_tool_specs(self) -> List[Any]:
        """
        Optional LangChain tool wrapper.

        如果环境安装了 langchain-core，这里可以生成 StructuredTool；
        如果没有安装，项目仍可用 fallback ReAct-style routing 跑通。
        """
        if not LANGCHAIN_AVAILABLE:
            return []

        def describe_tools(_: str = "") -> str:
            return self.list_tools().to_markdown(index=False)

        return [
            StructuredTool.from_function(
                func=describe_tools,
                name="describe_available_data_tools",
                description="List available data analysis tools and their descriptions.",
            )
        ]


if __name__ == "__main__":
    df = pd.read_csv("data/sample_sales.csv")
    agent = ReActDataAnalysisAgent()
    output = agent.run("分析产品结构和销售贡献。", df)

    print("LangChain available:", output.langchain_available)
    print("Task type:", output.task_type)
    print("Tool:", output.tool_name)
    print("Elapsed:", output.elapsed_seconds)
    print(output.result.head())
    print("\nTrace:")
    for item in output.reasoning_trace:
        print("-", item)
