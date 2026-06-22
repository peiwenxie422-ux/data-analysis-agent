import pandas as pd


def get_column_candidates(df: pd.DataFrame):
    """返回分类字段、数值字段和日期字段候选。"""
    categorical_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    numeric_cols = df.select_dtypes(include="number").columns.tolist()

    date_cols = []
    for col in df.columns:
        if "date" in col.lower() or "time" in col.lower() or "日期" in col or "时间" in col:
            date_cols.append(col)

    return {
        "categorical_columns": categorical_cols,
        "numeric_columns": numeric_cols,
        "date_columns": date_cols,
    }


def groupby_aggregate(
    df: pd.DataFrame,
    group_col: str,
    value_col: str,
    agg_funcs=None
) -> pd.DataFrame:
    """按分类字段对数值字段做聚合统计。"""
    if agg_funcs is None:
        agg_funcs = ["sum", "mean", "count", "max", "min"]

    if group_col not in df.columns:
        raise ValueError(f"分组字段不存在：{group_col}")

    if value_col not in df.columns:
        raise ValueError(f"数值字段不存在：{value_col}")

    if not pd.api.types.is_numeric_dtype(df[value_col]):
        raise ValueError(f"字段 {value_col} 不是数值型字段，不能做聚合统计。")

    result = (
        df.groupby(group_col)[value_col]
        .agg(agg_funcs)
        .reset_index()
    )

    rename_map = {
        "sum": f"{value_col}_sum",
        "mean": f"{value_col}_mean",
        "count": f"{value_col}_count",
        "max": f"{value_col}_max",
        "min": f"{value_col}_min",
    }

    result = result.rename(columns=rename_map)

    if f"{value_col}_sum" in result.columns:
        result = result.sort_values(f"{value_col}_sum", ascending=False)

    return result


def top_n(
    df: pd.DataFrame,
    group_col: str,
    value_col: str,
    n: int = 5
) -> pd.DataFrame:
    """按分类字段统计数值总和，并返回 Top N。"""
    result = groupby_aggregate(
        df=df,
        group_col=group_col,
        value_col=value_col,
        agg_funcs=["sum", "mean", "count"]
    )

    sum_col = f"{value_col}_sum"
    return result.sort_values(sum_col, ascending=False).head(n)


def trend_analysis(
    df: pd.DataFrame,
    date_col: str,
    value_col: str,
    freq: str = "D"
) -> pd.DataFrame:
    """按日期字段聚合数值字段，生成趋势数据。"""
    if date_col not in df.columns:
        raise ValueError(f"日期字段不存在：{date_col}")

    if value_col not in df.columns:
        raise ValueError(f"数值字段不存在：{value_col}")

    if not pd.api.types.is_numeric_dtype(df[value_col]):
        raise ValueError(f"字段 {value_col} 不是数值型字段，不能做趋势分析。")

    temp = df.copy()
    temp[date_col] = pd.to_datetime(temp[date_col], errors="coerce")
    temp = temp.dropna(subset=[date_col])

    if temp.empty:
        raise ValueError(f"字段 {date_col} 无法解析为日期。")

    result = (
        temp.set_index(date_col)
        .resample(freq)[value_col]
        .sum()
        .reset_index()
        .rename(columns={value_col: f"{value_col}_sum"})
    )

    return result


def missing_value_summary(df: pd.DataFrame) -> pd.DataFrame:
    """生成缺失值统计。"""
    result = pd.DataFrame({
        "字段名": df.columns,
        "缺失值数量": df.isna().sum().values,
        "缺失率": (df.isna().mean().values * 100).round(2)
    })
    return result.sort_values("缺失率", ascending=False)


def outlier_detection(
    df: pd.DataFrame,
    value_col: str,
    method: str = "iqr"
) -> pd.DataFrame:
    """使用 IQR 方法检测数值异常值。"""
    if value_col not in df.columns:
        raise ValueError(f"数值字段不存在：{value_col}")

    if not pd.api.types.is_numeric_dtype(df[value_col]):
        raise ValueError(f"字段 {value_col} 不是数值型字段，不能做异常检测。")

    series = df[value_col].dropna()

    if series.empty:
        raise ValueError(f"字段 {value_col} 没有可用数值。")

    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1

    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr

    result = df[(df[value_col] < lower_bound) | (df[value_col] > upper_bound)].copy()

    if result.empty:
        return pd.DataFrame({
            "说明": [f"字段 {value_col} 暂未发现明显异常值。"],
            "下界": [round(lower_bound, 2)],
            "上界": [round(upper_bound, 2)]
        })

    result["异常下界"] = round(lower_bound, 2)
    result["异常上界"] = round(upper_bound, 2)
    return result
