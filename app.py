from __future__ import annotations

import re
import time
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
from error_utils import format_exception_for_user
from data_guardrails import dataframe_memory_mb, is_large_dataframe, preview_dataframe

from tools import (
    get_column_candidates,
    groupby_aggregate,
    safe_python_dataframe_analysis,
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

from agent import explain_analysis_result
from analysis_pipeline import run_multistep_analysis

def result_to_text(result):
    """
    将 Pandas 真实计算结果转换成可传给 Claude 的文本。
    这里不用 to_markdown，避免额外依赖 tabulate。
    """
    if result is None:
        return "没有可用的计算结果。"

    try:
        if hasattr(result, "empty") and result.empty:
            return "计算结果为空。"

        if hasattr(result, "to_csv"):
            return result.to_csv(index=False)
    except Exception:
        pass

    return str(result)


try:
    from sql_tools import (
        build_schema_summary,
        run_readonly_sql,
        SQLSafetyError,
    )
    SQL_TOOLS_AVAILABLE = True
except Exception as e:
    SQL_TOOLS_AVAILABLE = False
    SQL_IMPORT_ERROR = e


st.set_page_config(
    page_title="智能数据分析 Agent - V3.3",
    page_icon="📊",
    layout="wide",
)


def load_file(uploaded_file) -> pd.DataFrame:
    file_name = uploaded_file.name.lower()

    if file_name.endswith(".csv"):
        return pd.read_csv(uploaded_file)
    elif file_name.endswith(".xlsx") or file_name.endswith(".xls"):
        return pd.read_excel(uploaded_file)

    raise ValueError("仅支持 CSV、XLSX、XLS 文件。")


def dtype_summary(df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "字段名": df.columns,
            "数据类型": [str(dtype) for dtype in df.dtypes],
            "非空数量": df.notna().sum().values,
            "唯一值数量": df.nunique(dropna=True).values,
        }
    )


def infer_value_col(question: str, df: pd.DataFrame) -> str:
    q = question.lower()
    numeric_cols = df.select_dtypes(include="number").columns.tolist()

    aliases = {
        "sales": ["sales", "销售额", "销售", "收入", "营收", "金额"],
        "quantity": ["quantity", "销量", "数量", "销售量"],
        "customer_count": ["customer_count", "客户", "客户数", "顾客数"],
    }

    for col, alias_list in aliases.items():
        if col in df.columns:
            if any(alias.lower() in q for alias in alias_list):
                return col

    if numeric_cols:
        return numeric_cols[0]

    raise ValueError("没有识别到可用于分析的数值字段。")


def infer_group_col(question: str, df: pd.DataFrame) -> str | None:
    q = question.lower()
    categorical_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

    aliases = {
        "product": ["product", "产品", "商品", "品类"],
        "region": ["region", "地区", "区域", "城市"],
        "channel": ["channel", "渠道", "线上", "线下"],
    }

    for col, alias_list in aliases.items():
        if col in df.columns:
            if any(alias.lower() in q for alias in alias_list):
                return col

    return categorical_cols[0] if categorical_cols else None


def infer_date_col(df: pd.DataFrame) -> str | None:
    candidates = get_column_candidates(df).get("date_columns", [])
    return candidates[0] if candidates else None


def infer_top_n(question: str, default_n: int = 3) -> int:
    q = question.lower()

    patterns = [
        r"top\s*(\d+)",
        r"前\s*(\d+)",
        r"最高的\s*(\d+)",
        r"最大的\s*(\d+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, q)
        if match:
            return int(match.group(1))

    return default_n


def infer_task_type(question: str) -> str:
    q = question.strip().lower()
    if q.startswith("python:") or q.startswith("pandas:"):
        return "python_sandbox"

    if any(word in q for word in ["客户效率", "客户效益", "客户贡献", "客户产出"]):
        return "customer_efficiency"

    if any(word in q for word in ["产品结构", "销售贡献", "品类贡献", "产品贡献", "结构"]):
        return "product_mix"

    if (
        ("地区" in q or "区域" in q or "region" in q)
        and ("渠道" in q or "channel" in q or "交叉" in q)
    ):
        return "channel_region"

    if any(word in q for word in ["缺失", "空值", "missing", "null"]):
        return "missing"

    if any(word in q for word in ["异常", "离群", "极端", "outlier"]):
        return "outlier"

    if any(word in q for word in ["预测", "预估", "未来", "forecast", "future"]):
        return "forecast"

    if any(word in q for word in ["同比", "环比", "增长率", "较上期", "比上期", "和上期", "mom", "yoy"]):
        return "period_comparison"

    if any(word in q for word in ["趋势", "变化", "按日期", "每天", "每月", "时间", "trend"]):
        return "trend"

    if any(word in q for word in ["top", "前", "最高", "最大", "排名"]):
        return "top_n"

    return "groupby"





PLOT_LABEL_MAP = {
    "笔记本": "Laptop",
    "手机": "Phone",
    "平板": "Tablet",
    "耳机": "Earphones",
    "华东": "East China",
    "华南": "South China",
    "华北": "North China",
    "线上": "Online",
    "线下": "Offline",
    "product": "Product",
    "region": "Region",
    "channel": "Channel",
    "sales": "Sales",
    "sales_sum": "Sales",
    "total_sales": "Total sales",
    "sales_per_customer": "Sales per customer",
    "customer_count_sum": "Customer count",
    "avg_order_value": "Average order value",
}

def plot_label(value):
    """Only translate labels for charts. Tables and analysis text keep original Chinese."""
    text = str(value)
    return PLOT_LABEL_MAP.get(text, text)

def translate_index_and_columns(df):
    out = df.copy()
    out.index = [plot_label(x) for x in out.index]
    out.columns = [plot_label(x) for x in out.columns]
    return out


def should_render_chart(task_type, result):
    """
    判断当前任务是否适合生成图表。
    检测类任务如果没有实际异常/缺失，不强行画图，避免出现空图或误导性图表。
    """
    if result is None:
        return False

    if task_type == "missing":
        if "缺失值数量" in result.columns:
            return result["缺失值数量"].sum() > 0
        return False

    if task_type == "outlier":
        if "说明" in result.columns:
            text = " ".join(result["说明"].astype(str).tolist())
            if "未发现" in text or "没有发现" in text:
                return False
        return len(result) > 1

    return True


def render_result_chart(task_type, result, group_col=None, value_col=None):
    # 检测类任务不生成图表，避免空图或误导性图表
    if task_type in ("missing", "outlier"):
        st.info("当前任务属于检测/说明类任务，结果已在表格和业务解释中展示，无需生成图表。")
        return

    """Render charts with English labels to avoid Matplotlib Chinese font issues."""
    if result is None or result.empty:
        st.warning("没有得到可展示的分析结果。")
        return

    try:
        chart_df = result.copy()
        fig, ax = plt.subplots(figsize=(10, 5))

        if task_type == "product_mix":
            x_col = "product" if "product" in chart_df.columns else (group_col or chart_df.columns[0])
            y_col = "sales_sum" if "sales_sum" in chart_df.columns else (value_col or chart_df.select_dtypes(include="number").columns[0])
            plot_df = chart_df.sort_values(y_col, ascending=False)
            ax.bar([plot_label(x) for x in plot_df[x_col]], plot_df[y_col])
            ax.set_title("Product sales contribution")
            ax.set_xlabel("Product")
            ax.set_ylabel("Sales")

        elif task_type == "channel_region":
            region_col = "region" if "region" in chart_df.columns else (group_col or chart_df.columns[0])
            channel_cols = [c for c in ["线上", "线下", "Online", "Offline"] if c in chart_df.columns]

            if channel_cols:
                plot_data = chart_df.set_index(region_col)[channel_cols]
                plot_data = translate_index_and_columns(plot_data)
                plot_data.plot(kind="bar", ax=ax)
                ax.set_title("Region x channel sales")
                ax.set_xlabel("Region")
                ax.set_ylabel("Sales")
            else:
                y_col = "total_sales" if "total_sales" in chart_df.columns else chart_df.select_dtypes(include="number").columns[0]
                plot_df = chart_df.sort_values(y_col, ascending=False)
                ax.bar([plot_label(x) for x in plot_df[region_col]], plot_df[y_col])
                ax.set_title("Sales by region")
                ax.set_xlabel("Region")
                ax.set_ylabel("Sales")

        elif task_type == "customer_efficiency":
            x_col = "product" if "product" in chart_df.columns else (group_col or chart_df.columns[0])
            y_col = "sales_per_customer" if "sales_per_customer" in chart_df.columns else chart_df.select_dtypes(include="number").columns[0]
            plot_df = chart_df.sort_values(y_col, ascending=False)
            ax.bar([plot_label(x) for x in plot_df[x_col]], plot_df[y_col])
            ax.set_title("Customer efficiency by product")
            ax.set_xlabel("Product")
            ax.set_ylabel("Sales per customer")

        elif task_type == "period_comparison":
            date_col = chart_df.columns[0]
            plot_df = chart_df.sort_values(date_col)
            if "growth_rate_pct" in plot_df.columns:
                ax.plot(plot_df[date_col].astype(str), plot_df["growth_rate_pct"], marker="o")
                ax.set_title("Period comparison growth rate")
                ax.set_xlabel("Date")
                ax.set_ylabel("Growth rate (%)")
            else:
                st.info("同比/环比结果中没有可绘制的增长率字段。")
                return

        elif task_type == "forecast":
            date_col = chart_df.columns[0]
            numeric_cols = chart_df.select_dtypes(include="number").columns.tolist()
            if not numeric_cols:
                st.info("预测结果中没有可绘制的数值字段。")
                return
            y_col = numeric_cols[0]
            plot_df = chart_df.sort_values(date_col)
            ax.plot(plot_df[date_col].astype(str), plot_df[y_col], marker="o")
            ax.set_title("Sales forecast")
            ax.set_xlabel("Date")
            ax.set_ylabel("Sales")

        elif task_type == "trend":
            date_col = chart_df.columns[0]
            numeric_cols = chart_df.select_dtypes(include="number").columns.tolist()
            if not numeric_cols:
                st.info("趋势结果中没有可绘制的数值字段。")
                return
            y_col = numeric_cols[0]
            plot_df = chart_df.sort_values(date_col)
            ax.plot(plot_df[date_col].astype(str), plot_df[y_col], marker="o")
            ax.set_title("Sales trend")
            ax.set_xlabel("Date")
            ax.set_ylabel("Sales")

        else:
            numeric_cols = chart_df.select_dtypes(include="number").columns.tolist()
            non_numeric_cols = [c for c in chart_df.columns if c not in numeric_cols]

            if not numeric_cols or not non_numeric_cols:
                st.info("当前结果更适合表格展示，暂无图表。")
                return

            x_col = group_col if group_col in chart_df.columns else non_numeric_cols[0]
            y_candidates = [c for c in numeric_cols if c.endswith("_sum")]
            y_col = y_candidates[0] if y_candidates else numeric_cols[0]

            plot_df = chart_df.sort_values(y_col, ascending=False)
            ax.bar([plot_label(x) for x in plot_df[x_col]], plot_df[y_col])
            ax.set_title("Analysis result chart")
            ax.set_xlabel(plot_label(x_col))
            ax.set_ylabel(plot_label(y_col))

        ax.tick_params(axis="x", rotation=30)
        ax.grid(axis="y", alpha=0.3)
        plt.tight_layout()
        st.pyplot(fig)
        plt.close(fig)

    except Exception as e:
        st.warning(f"图表生成失败：{e}")

st.title("📊 智能数据分析 Agent - V3.3")
st.caption(
    "当前版本：支持分组聚合、Top N、趋势分析、同比/环比分析、趋势预测、缺失值分析、异常检测、SQL 只读查询、产品结构分析、渠道地区矩阵、客户效率分析，并调用 Claude 基于真实结果生成业务解释。"
)

uploaded_file = st.file_uploader(
    "请上传一个 CSV 或 Excel 文件",
    type=["csv", "xlsx", "xls"],
)

if uploaded_file is None:
    st.info("请先上传一个数据文件。")
    st.stop()

try:
    df = load_file(uploaded_file)
except Exception as e:
    st.error(format_exception_for_user(e))
    st.stop()

st.success("\u6587\u4ef6\u4e0a\u4f20\u6210\u529f\uff01")

memory_mb = dataframe_memory_mb(df)
total_cells = df.shape[0] * df.shape[1]
is_large_data = is_large_dataframe(df, memory_mb=memory_mb)

st.subheader("1. \u6570\u636e\u57fa\u672c\u4fe1\u606f")
col1, col2, col3, col4 = st.columns(4)
col1.metric("\u884c\u6570", f"{df.shape[0]:,}")
col2.metric("\u5217\u6570", f"{df.shape[1]:,}")
col3.metric("\u603b\u5355\u5143\u683c\u6570", f"{total_cells:,}")
col4.metric("\u5185\u5b58\u5360\u7528", f"{memory_mb:.2f} MB")

if is_large_data:
    st.warning("\u68c0\u6d4b\u5230\u6570\u636e\u91cf\u8f83\u5927\uff1a\u9875\u9762\u9884\u89c8\u5c06\u4f7f\u7528\u56fa\u5b9a\u62bd\u6837\uff0c\u540e\u7eed\u5206\u6790\u4ecd\u57fa\u4e8e\u5b8c\u6574\u6570\u636e\u3002")

st.subheader("2. \u6570\u636e\u9884\u89c8")
preview_df, sampled_preview = preview_dataframe(df)
if sampled_preview:
    st.caption("\u5f53\u524d\u9884\u89c8\u663e\u793a\u56fa\u5b9a\u968f\u673a\u62bd\u6837\u7684 10 \u884c\uff0c\u907f\u514d\u5927\u6587\u4ef6\u9884\u89c8\u62d6\u6162\u9875\u9762\u3002")
else:
    st.caption("\u5f53\u524d\u9884\u89c8\u663e\u793a\u524d 10 \u884c\u3002")
st.dataframe(preview_df, width="stretch")

st.subheader("3. 字段类型信息")
st.dataframe(dtype_summary(df), width="stretch")

st.subheader("4. 缺失值分析")
st.dataframe(missing_value_summary(df), width="stretch")

st.subheader("5. 数值列描述性统计")
numeric_df = df.select_dtypes(include="number")
if numeric_df.empty:
    st.warning("当前数据中没有数值型字段，无法生成数值统计。")
else:
    st.dataframe(numeric_df.describe().T, width="stretch")

st.subheader("6. 多工具自然语言分析")

candidates = get_column_candidates(df)
with st.expander("可用字段信息", expanded=False):
    st.write("分类字段候选：", candidates.get("categorical_columns", []))
    st.write("数值字段候选：", candidates.get("numeric_columns", []))
    st.write("日期字段候选：", candidates.get("date_columns", []))

st.subheader("6.1 SQL 只读查询工具（V3）")

if SQL_TOOLS_AVAILABLE:
    st.caption(
        "上传的数据会被临时注册为 SQLite 表 `sales_data`。这里只允许 SELECT / WITH 只读查询，禁止 INSERT、UPDATE、DELETE、DROP、ALTER、CREATE 等写操作。"
    )

    with st.expander("查看 SQL 表结构", expanded=False):
        try:
            st.dataframe(build_schema_summary(df), width="stretch")
        except Exception as e:
            st.warning(f"表结构生成失败：{e}")

    default_sql = """SELECT product, SUM(sales) AS sales_sum
FROM sales_data
GROUP BY product
ORDER BY sales_sum DESC"""

    sql_query = st.text_area(
        "请输入只读 SQL 查询",
        value=default_sql,
        height=130,
    )

    if st.button("执行 SQL 只读查询"):
        try:
            sql_result, sql_elapsed = run_readonly_sql(df, sql_query)
            st.success(f"SQL 查询执行成功，耗时 {sql_elapsed:.4f} 秒。")
            st.dataframe(sql_result, width="stretch")

        except SQLSafetyError as e:
            st.error(format_exception_for_user(e))

        except Exception as e:
            st.error(format_exception_for_user(e))
else:
    st.warning(f"SQL 工具暂不可用：{SQL_IMPORT_ERROR}")

example_questions = [
    "按地区统计销售额，并判断哪个地区表现最好。",
    "找出销售额最高的前 3 个产品。",
    "按日期分析销售额趋势。",
    "按日期分析销售额环比增长率。",
    "预测未来 3 天销售额趋势。",
    "检测销售额是否存在异常值。",
    "分析这个数据集有没有缺失值。",
    "分析产品结构和销售贡献。",
    "分析地区和渠道的交叉表现。",
    "分析不同产品的客户效率。",
]

st.write("你可以尝试这些问题：")
for q in example_questions:
    st.code(q, language="text")

user_question = st.text_area(
    "请输入你想问的数据分析问题",
    value="分析产品结构和销售贡献。",
    height=120,
)

if st.button("开始分析"):
    if not user_question.strip():
        st.warning("请输入一个分析问题。")
        st.stop()

    try:
        pipeline_result = run_multistep_analysis(user_question, df)
        agent_output = pipeline_result.agent_result
        decision = pipeline_result.decision

        task_type = agent_output.task_type
        result = agent_output.result
        group_col = decision.group_col
        value_col = decision.value_col
        date_col = decision.date_col
        tool_description = f"{agent_output.tool_name} via ReActDataAnalysisAgent"
        elapsed_seconds = agent_output.elapsed_seconds

        if result is None or result.empty:
            st.warning("没有得到可展示的分析结果。")
            st.stop()

        result_rows = result.shape[0] if hasattr(result, "shape") else 0
        result_cols = result.shape[1] if hasattr(result, "shape") and len(result.shape) > 1 else 0

        st.info(f"Agent 识别到的任务类型：`{task_type}`")
        st.success(f"已调用：{tool_description}")

        with st.expander("Agent 执行日志 / Tool Call Trace", expanded=True):
            st.json(
                {
                    "status": "success",
                    "task_type": task_type,
                    "tool_name": agent_output.tool_name,
                    "tool_description": tool_description,
                    "agent_backend": "ReActDataAnalysisAgent",
                    "group_col": group_col,
                    "value_col": value_col,
                    "date_col": date_col,
                    "result_shape": f"{result_rows} rows x {result_cols} columns",
                    "elapsed_seconds": elapsed_seconds,
                    "reasoning_trace": agent_output.reasoning_trace,
                    "pipeline": [step.name for step in pipeline_result.steps],
                    "pipeline_details": [
                        {
                            "name": step.name,
                            "status": step.status,
                            "detail": step.detail,
                        }
                        for step in pipeline_result.steps
                    ],
                }
            )

    except Exception as e:
        st.error(format_exception_for_user(e))
        st.stop()

    st.subheader("7. Pandas 工具真实计算结果")
    st.dataframe(result, width="stretch")

    st.subheader("8. 图表展示")
    render_result_chart(task_type, result)

    st.subheader("9. Claude 基于真实结果的业务解释")

    result_text = result_to_text(result)

    try:
        with st.spinner("Claude 正在基于真实计算结果生成解释..."):
            explanation = explain_analysis_result(user_question, result_text)
        st.markdown(explanation)

    except Exception as e:
        st.warning(f"Claude 解释生成失败：{e}")
        st.markdown("已完成 Pandas 真实计算，但 Claude 业务解释暂时不可用。")

