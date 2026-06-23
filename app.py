from __future__ import annotations

import re
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

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
)

from agent import explain_analysis_result

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
    page_title="智能数据分析 Agent - V3.1",
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
    q = question.lower()

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

def render_result_chart(task_type, result, group_col=None, value_col=None):
    """Render charts with English labels to avoid Matplotlib Chinese font issues."""
    if result is None or result.empty:
        st.info("当前结果为空，暂无图表。")
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

st.title("📊 智能数据分析 Agent - V3.1")
st.caption(
    "当前版本：支持分组聚合、Top N、趋势分析、缺失值分析、异常检测、SQL 只读查询、产品结构分析、渠道地区矩阵、客户效率分析，并调用 Claude 基于真实结果生成业务解释。"
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
    st.error(f"文件读取失败：{e}")
    st.stop()

st.success("文件上传成功！")

st.subheader("1. 数据基本信息")
col1, col2, col3 = st.columns(3)
col1.metric("行数", df.shape[0])
col2.metric("列数", df.shape[1])
col3.metric("总单元格数", df.shape[0] * df.shape[1])

st.subheader("2. 数据预览")
st.dataframe(df.head(10), use_container_width=True)

st.subheader("3. 字段类型信息")
st.dataframe(dtype_summary(df), use_container_width=True)

st.subheader("4. 缺失值分析")
st.dataframe(missing_value_summary(df), use_container_width=True)

st.subheader("5. 数值列描述性统计")
numeric_df = df.select_dtypes(include="number")
if numeric_df.empty:
    st.warning("当前数据中没有数值型字段，无法生成数值统计。")
else:
    st.dataframe(numeric_df.describe().T, use_container_width=True)

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
            st.dataframe(build_schema_summary(df), use_container_width=True)
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
            st.dataframe(sql_result, use_container_width=True)

        except SQLSafetyError as e:
            st.error(f"SQL 权限校验失败：{e}")

        except Exception as e:
            st.error(f"SQL 查询执行失败：{e}")
else:
    st.warning(f"SQL 工具暂不可用：{SQL_IMPORT_ERROR}")

example_questions = [
    "按地区统计销售额，并判断哪个地区表现最好。",
    "找出销售额最高的前 3 个产品。",
    "按日期分析销售额趋势。",
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
        task_type = infer_task_type(user_question)
        group_col = infer_group_col(user_question, df)
        value_col = infer_value_col(user_question, df)
        date_col = infer_date_col(df)

        st.info(f"Agent 识别到的任务类型：`{task_type}`")

        result = None
        tool_description = ""

        if task_type == "product_mix":
            product_col = "product" if "product" in df.columns else group_col
            if product_col is None:
                st.error("没有识别到产品字段，无法进行产品结构分析。")
                st.stop()

            result = product_mix_analysis(
                df,
                product_col=product_col,
                value_col=value_col,
            )
            tool_description = f"产品结构分析工具，按 {product_col} 统计 {value_col}"

        elif task_type == "channel_region":
            region_col = "region" if "region" in df.columns else group_col
            channel_col = "channel" if "channel" in df.columns else None

            if channel_col is None:
                for c in df.columns:
                    if "channel" in c.lower() or "渠道" in c:
                        channel_col = c
                        break

            if region_col is None or channel_col is None:
                st.error("没有识别到地区字段或渠道字段，无法进行地区 × 渠道交叉分析。")
                st.stop()

            result = channel_region_matrix(
                df,
                region_col=region_col,
                channel_col=channel_col,
                value_col=value_col,
            )
            tool_description = f"地区 × 渠道交叉分析工具，按 {region_col} 和 {channel_col} 统计 {value_col}"

        elif task_type == "customer_efficiency":
            customer_col = "customer_count" if "customer_count" in df.columns else None

            if customer_col is None:
                for c in df.columns:
                    if "customer" in c.lower() or "客户" in c:
                        customer_col = c
                        break

            if customer_col is None:
                st.error("没有识别到客户数字段，无法进行客户效率分析。")
                st.stop()

            analysis_group_col = "product" if "product" in df.columns else group_col

            result = customer_efficiency_analysis(
                df,
                group_col=analysis_group_col,
                value_col=value_col,
                customer_col=customer_col,
            )
            tool_description = f"客户效率分析工具，按 {analysis_group_col} 统计销售额、客户数、人均销售额和客单价"

        elif task_type == "missing":
            result = missing_value_summary(df)
            tool_description = "缺失值分析工具"

        elif task_type == "outlier":
            if value_col is None:
                st.error("无法识别数值字段，不能进行异常检测。")
                st.stop()

            result = outlier_detection(df, value_col=value_col)
            tool_description = f"异常值检测工具，字段：{value_col}"

        elif task_type == "trend":
            if date_col is None:
                st.error("无法识别日期字段，不能进行趋势分析。")
                st.stop()

            result = trend_analysis(
                df,
                date_col=date_col,
                value_col=value_col,
            )
            tool_description = f"趋势分析工具，日期字段：{date_col}，指标字段：{value_col}"

        elif task_type == "top_n":
            n = infer_top_n(user_question, default_n=3)
            result = top_n(
                df,
                group_col=group_col,
                value_col=value_col,
                n=n,
            )
            tool_description = f"Top N 工具，按 {group_col} 分组，统计 {value_col}，返回前 {n} 名"

        else:
            result = groupby_aggregate(
                df,
                group_col=group_col,
                value_col=value_col,
            )
            tool_description = f"分组聚合工具，按 {group_col} 分组，统计 {value_col}"

        if result is None or result.empty:
            st.warning("没有得到可展示的分析结果。")
            st.stop()

        st.success(f"已调用：{tool_description}")

    except Exception as e:
        st.error(f"分析失败：{e}")
        st.stop()

    st.subheader("7. Pandas 工具真实计算结果")
    st.dataframe(result, use_container_width=True)

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

