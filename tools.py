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

# =========================
# V3.1 Business Analysis Tools
# =========================

import pandas as pd


def product_mix_analysis(df, product_col="product", value_col="sales"):
    """
    产品结构占比分析：
    按产品统计销售额、销售占比、累计占比，并给出 ABC 分类。
    """
    if product_col not in df.columns:
        raise ValueError(f"产品字段不存在: {product_col}")

    if value_col not in df.columns:
        raise ValueError(f"数值字段不存在: {value_col}")

    temp = df[[product_col, value_col]].copy()
    temp[value_col] = pd.to_numeric(temp[value_col], errors="coerce")
    temp = temp.dropna(subset=[value_col])

    if temp.empty:
        raise ValueError(f"字段 {value_col} 没有可用于分析的数值。")

    result = (
        temp.groupby(product_col)[value_col]
        .agg(["sum", "mean", "count"])
        .reset_index()
    )

    result = result.rename(columns={
        "sum": f"{value_col}_sum",
        "mean": f"{value_col}_mean",
        "count": f"{value_col}_count"
    })

    sum_col = f"{value_col}_sum"
    total = result[sum_col].sum()

    result = result.sort_values(sum_col, ascending=False).reset_index(drop=True)
    result["sales_share_pct"] = (result[sum_col] / total * 100).round(2)
    result["cumulative_share_pct"] = result["sales_share_pct"].cumsum().round(2)

    def abc_class(x):
        if x <= 80:
            return "A 核心产品"
        elif x <= 95:
            return "B 重要产品"
        else:
            return "C 长尾产品"

    result["abc_class"] = result["cumulative_share_pct"].apply(abc_class)

    return result


def channel_region_matrix(df, region_col="region", channel_col="channel", value_col="sales"):
    """
    地区 × 渠道交叉分析：
    查看不同地区在线上/线下等渠道的销售分布。
    """
    for col in [region_col, channel_col, value_col]:
        if col not in df.columns:
            raise ValueError(f"字段不存在: {col}")

    temp = df[[region_col, channel_col, value_col]].copy()
    temp[value_col] = pd.to_numeric(temp[value_col], errors="coerce")
    temp = temp.dropna(subset=[value_col])

    if temp.empty:
        raise ValueError(f"字段 {value_col} 没有可用于分析的数值。")

    pivot = pd.pivot_table(
        temp,
        index=region_col,
        columns=channel_col,
        values=value_col,
        aggfunc="sum",
        fill_value=0
    ).reset_index()

    numeric_cols = [c for c in pivot.columns if c != region_col]
    pivot["total_sales"] = pivot[numeric_cols].sum(axis=1)

    grand_total = pivot["total_sales"].sum()
    pivot["total_share_pct"] = (pivot["total_sales"] / grand_total * 100).round(2)

    pivot = pivot.sort_values("total_sales", ascending=False).reset_index(drop=True)

    return pivot


def customer_efficiency_analysis(
    df: pd.DataFrame,
    group_col: str,
    value_col: str,
    customer_col: str,
) -> pd.DataFrame:
    """
    客户效率分析。
    逻辑：
    - group_col：分析维度，例如 product
    - value_col：业务价值字段，优先使用 sales
    - customer_col：客户数字段，例如 customer_count

    注意：
    如果 value_col 被误识别成 customer_col，会自动优先切换到 sales，
    避免“客户数字段既当销售额又当客户数”的错误。
    """
    if group_col not in df.columns:
        raise ValueError(f"分组字段不存在：{group_col}")

    if customer_col not in df.columns:
        raise ValueError(f"客户数字段不存在：{customer_col}")

    if not pd.api.types.is_numeric_dtype(df[customer_col]):
        raise ValueError(f"客户数字段 {customer_col} 不是数值型字段。")

    # 客户效率的价值字段应该优先是 sales，而不是 customer_count
    business_value_col = value_col

    if business_value_col == customer_col:
        if "sales" in df.columns and pd.api.types.is_numeric_dtype(df["sales"]):
            business_value_col = "sales"
        else:
            numeric_candidates = [
                c for c in df.select_dtypes(include="number").columns
                if c != customer_col
            ]
            if not numeric_candidates:
                raise ValueError("没有可用于衡量客户效率的业务价值字段。")
            business_value_col = numeric_candidates[0]

    if business_value_col not in df.columns:
        raise ValueError(f"业务价值字段不存在：{business_value_col}")

    if not pd.api.types.is_numeric_dtype(df[business_value_col]):
        raise ValueError(f"业务价值字段 {business_value_col} 不是数值型字段。")

    value_sum_col = f"{business_value_col}_sum"
    value_mean_col = f"{business_value_col}_mean"
    customer_sum_col = f"{customer_col}_sum"

    result = (
        df.groupby(group_col)
        .agg(
            **{
                value_sum_col: (business_value_col, "sum"),
                value_mean_col: (business_value_col, "mean"),
                customer_sum_col: (customer_col, "sum"),
                "order_count": (customer_col, "count"),
                f"{customer_col}_max": (customer_col, "max"),
                f"{customer_col}_min": (customer_col, "min"),
            }
        )
        .reset_index()
    )

    result["sales_per_customer"] = (
        result[value_sum_col] / result[customer_sum_col].replace(0, pd.NA)
    ).round(2)

    result["avg_order_value"] = (
        result[value_sum_col] / result["order_count"].replace(0, pd.NA)
    ).round(2)

    return result.sort_values("sales_per_customer", ascending=False)

def period_comparison_analysis(
    df: pd.DataFrame,
    date_col: str,
    value_col: str,
    freq: str = "D",
    period_type: str = "mom",
) -> pd.DataFrame:
    """同比 / 环比分析：按时间聚合指标，并计算上期或同期增长率。"""
    if date_col not in df.columns:
        raise ValueError(f"日期字段不存在：{date_col}")
    if value_col not in df.columns:
        raise ValueError(f"数值字段不存在：{value_col}")
    if not pd.api.types.is_numeric_dtype(df[value_col]):
        raise ValueError(f"字段 {value_col} 不是数值型字段，不能做同比/环比分析。")

    temp = df[[date_col, value_col]].copy()
    temp[date_col] = pd.to_datetime(temp[date_col], errors="coerce")
    temp[value_col] = pd.to_numeric(temp[value_col], errors="coerce")
    temp = temp.dropna(subset=[date_col, value_col])

    if temp.empty:
        raise ValueError(f"字段 {date_col} 或 {value_col} 没有可用于同比/环比分析的数据。")

    value_sum_col = f"{value_col}_sum"
    result = (
        temp.set_index(date_col)
        .resample(freq)[value_col]
        .sum()
        .reset_index()
        .rename(columns={value_col: value_sum_col})
    )

    shift_periods = 12 if period_type == "yoy" and freq in ("M", "MS", "ME") else 1
    previous_col = f"previous_{value_sum_col}"
    result[previous_col] = result[value_sum_col].shift(shift_periods)
    result["change_value"] = result[value_sum_col] - result[previous_col]
    result["growth_rate_pct"] = (
        result["change_value"] / result[previous_col].replace(0, pd.NA) * 100
    ).round(2)
    result["comparison_type"] = "同比" if period_type == "yoy" else "环比"

    return result


def trend_forecast_analysis(
    df: pd.DataFrame,
    date_col: str,
    value_col: str,
    periods: int = 3,
    freq: str = "D",
) -> pd.DataFrame:
    """简单趋势预测：基于历史聚合序列做线性外推，适合作为原型系统预测能力。"""
    if date_col not in df.columns:
        raise ValueError(f"日期字段不存在：{date_col}")
    if value_col not in df.columns:
        raise ValueError(f"数值字段不存在：{value_col}")
    if not pd.api.types.is_numeric_dtype(df[value_col]):
        raise ValueError(f"字段 {value_col} 不是数值型字段，不能做趋势预测。")

    temp = df[[date_col, value_col]].copy()
    temp[date_col] = pd.to_datetime(temp[date_col], errors="coerce")
    temp[value_col] = pd.to_numeric(temp[value_col], errors="coerce")
    temp = temp.dropna(subset=[date_col, value_col])

    if temp.empty:
        raise ValueError(f"字段 {date_col} 或 {value_col} 没有可用于趋势预测的数据。")

    value_sum_col = f"{value_col}_sum"
    history = (
        temp.set_index(date_col)
        .resample(freq)[value_col]
        .sum()
        .reset_index()
        .rename(columns={value_col: value_sum_col})
        .sort_values(date_col)
        .reset_index(drop=True)
    )

    if history.empty:
        raise ValueError("没有可用于趋势预测的历史序列。")

    if len(history) >= 2:
        slope = (history[value_sum_col].iloc[-1] - history[value_sum_col].iloc[0]) / (len(history) - 1)
    else:
        slope = 0

    last_date = history[date_col].iloc[-1]
    last_value = history[value_sum_col].iloc[-1]
    future_dates = pd.date_range(start=last_date, periods=periods + 1, freq=freq)[1:]

    forecast = pd.DataFrame({
        date_col: future_dates,
        value_sum_col: [round(last_value + slope * i, 2) for i in range(1, periods + 1)],
    })

    history["forecast_flag"] = "historical"
    forecast["forecast_flag"] = "forecast"
    return pd.concat([history, forecast], ignore_index=True)

