import streamlit as st
import pandas as pd
import re

from tools import (
    get_column_candidates,
    groupby_aggregate,
    top_n,
    trend_analysis,
    missing_value_summary,
    outlier_detection,
)
from agent import explain_analysis_result


st.set_page_config(
    page_title="智能数据分析 Agent - V2.1",
    page_icon="📊",
    layout="wide"
)


def load_file(uploaded_file):
    file_name = uploaded_file.name.lower()

    if file_name.endswith(".csv"):
        return pd.read_csv(uploaded_file)
    elif file_name.endswith(".xlsx") or file_name.endswith(".xls"):
        return pd.read_excel(uploaded_file)
    else:
        raise ValueError("仅支持 CSV、XLSX、XLS 文件。")


def dtype_summary(df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({
        "字段名": df.columns,
        "数据类型": [str(dtype) for dtype in df.dtypes],
        "非空数量": df.notna().sum().values,
        "唯一值数量": df.nunique(dropna=True).values
    })


def infer_value_col(question: str, df: pd.DataFrame):
    q = question.lower()
    numeric_cols = df.select_dtypes(include="number").columns.tolist()

    aliases = {
        "sales": ["sales", "销售额", "销售", "金额", "收入", "营收"],
        "quantity": ["quantity", "销量", "数量", "销售量"],
        "customer_count": ["customer_count", "客户", "客户数", "顾客数"],
    }

    for col in numeric_cols:
        col_aliases = aliases.get(col, [col])
        if any(alias in q for alias in col_aliases):
            return col

    return numeric_cols[0] if numeric_cols else None


def infer_group_col(question: str, df: pd.DataFrame):
    q = question.lower()
    categorical_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

    aliases = {
        "region": ["region", "地区", "区域"],
        "product": ["product", "产品", "商品"],
        "channel": ["channel", "渠道"],
    }

    for col in categorical_cols:
        col_aliases = aliases.get(col, [col])
        if any(alias in q for alias in col_aliases):
            return col

    return categorical_cols[0] if categorical_cols else None


def infer_date_col(df: pd.DataFrame):
    candidates = get_column_candidates(df)["date_columns"]
    return candidates[0] if candidates else None


def infer_top_n(question: str, default_n: int = 5) -> int:
    """
    从用户问题中识别 Top N 的 N。
    例如：前3、前 3、top3、top 5。
    """
    q = question.lower()

    patterns = [
        r"前\s*(\d+)",
        r"top\s*(\d+)",
        r"最高的?\s*(\d+)",
        r"最大?的?\s*(\d+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, q)
        if match:
            return int(match.group(1))

    return default_n


def infer_task_type(question: str):
    q = question.lower()

    if any(word in q for word in ["缺失", "空值", "missing", "null"]):
        return "missing"

    if any(word in q for word in ["异常", "离群", "极端", "outlier"]):
        return "outlier"

    if any(word in q for word in ["趋势", "变化", "按日期", "每天", "每月", "时间", "trend"]):
        return "trend"

    if any(word in q for word in ["top", "前", "最高", "最大", "排名"]):
        return "top_n"

    if any(word in q for word in ["按", "统计", "分组", "对比", "比较"]):
        return "groupby"

    return "groupby"


def render_result_chart(task_type, result, group_col=None, value_col=None):
    if result.empty:
        return

    if task_type in ["groupby", "top_n"]:
        sum_col = f"{value_col}_sum"
        if group_col and sum_col in result.columns:
            chart_data = result[[group_col, sum_col]].set_index(group_col)
            st.bar_chart(chart_data)

    elif task_type == "trend":
        sum_col = f"{value_col}_sum"
        date_col = result.columns[0]
        if sum_col in result.columns:
            chart_data = result[[date_col, sum_col]].set_index(date_col)
            st.line_chart(chart_data)


st.title("📊 智能数据分析 Agent - V2.1")
st.caption("当前版本：支持分组聚合、Top N、趋势分析、缺失值分析、异常检测，并调用 Claude 基于真实结果做业务解释。")

uploaded_file = st.file_uploader(
    "请上传一个 CSV 或 Excel 文件",
    type=["csv", "xlsx", "xls"]
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
st.dataframe(df.head(10), width="stretch")

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
    st.write("分类字段候选：", candidates["categorical_columns"])
    st.write("数值字段候选：", candidates["numeric_columns"])
    st.write("日期字段候选：", candidates["date_columns"])

example_questions = [
    "按地区统计销售额，并判断哪个地区表现最好。",
    "找出销售额最高的前 3 个产品。",
    "按日期分析销售额趋势。",
    "检测销售额是否存在异常值。",
    "分析这个数据集有没有缺失值。"
]

st.write("你可以尝试这些问题：")
for q in example_questions:
    st.code(q, language="text")

user_question = st.text_area(
    "请输入你想问的数据分析问题",
    value="按地区统计销售额，并判断哪个地区表现最好。",
)

if st.button("开始分析"):
    if not user_question.strip():
        st.warning("请先输入一个分析问题。")
        st.stop()

    try:
        task_type = infer_task_type(user_question)
        group_col = infer_group_col(user_question, df)
        value_col = infer_value_col(user_question, df)
        date_col = infer_date_col(df)

        st.info(f"Agent 识别到的任务类型：`{task_type}`")

        result = None
        tool_description = ""

        if task_type == "missing":
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
            if value_col is None:
                st.error("无法识别数值字段，不能进行趋势分析。")
                st.stop()
            result = trend_analysis(df, date_col=date_col, value_col=value_col)
            tool_description = f"趋势分析工具，日期字段：{date_col}，指标字段：{value_col}"

        elif task_type == "top_n":
            if group_col is None or value_col is None:
                st.error("无法识别分组字段或数值字段，不能进行 Top N 分析。")
                st.stop()
            n = infer_top_n(user_question)
            result = top_n(df, group_col=group_col, value_col=value_col, n=n)
            tool_description = f"Top N 工具，按 {group_col} 分组，统计 {value_col}，返回前 {n} 名"

        else:
            if group_col is None or value_col is None:
                st.error("无法识别分组字段或数值字段，不能进行分组聚合。")
                st.stop()
            result = groupby_aggregate(df, group_col=group_col, value_col=value_col)
            tool_description = f"分组聚合工具，按 {group_col} 分组，统计 {value_col}"

        st.success(f"已调用：{tool_description}")

        st.subheader("7. Pandas 工具真实计算结果")
        st.dataframe(result, width="stretch")

        st.subheader("8. 图表展示")
        render_result_chart(task_type, result, group_col=group_col, value_col=value_col)

        st.subheader("9. Claude 基于真实结果的业务解释")

        result_text = result.to_string(index=False)

        with st.spinner("Claude 正在基于真实计算结果生成解释..."):
            explanation = explain_analysis_result(user_question, result_text)

        st.markdown(explanation)

    except Exception as e:
        st.error(f"分析失败：{e}")
