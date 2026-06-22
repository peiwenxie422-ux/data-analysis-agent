import re
import sqlite3
import time
from typing import Tuple

import pandas as pd


FORBIDDEN_SQL_KEYWORDS = [
    "insert", "update", "delete", "drop", "alter", "create",
    "replace", "truncate", "attach", "detach", "pragma",
    "vacuum", "grant", "revoke"
]


class SQLSafetyError(ValueError):
    """SQL safety validation error."""


def _remove_sql_comments(sql: str) -> str:
    """Remove SQL comments before safety checking."""
    sql = re.sub(r"--.*?$", "", sql, flags=re.MULTILINE)
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    return sql


def validate_readonly_sql(sql: str) -> str:
    """
    Validate that SQL is read-only.

    Allowed:
    - SELECT ...
    - WITH ... SELECT ...

    Blocked:
    - INSERT / UPDATE / DELETE / DROP / ALTER / CREATE ...
    - Multiple SQL statements
    - Empty SQL
    """
    if not isinstance(sql, str) or not sql.strip():
        raise SQLSafetyError("SQL 不能为空。")

    cleaned = _remove_sql_comments(sql).strip()
    cleaned = cleaned.rstrip(";").strip()

    if not cleaned:
        raise SQLSafetyError("SQL 不能为空。")

    lowered = cleaned.lower()

    if ";" in cleaned:
        raise SQLSafetyError("检测到多个 SQL 语句。为了安全，只允许执行单条只读查询。")

    if not (lowered.startswith("select") or lowered.startswith("with")):
        raise SQLSafetyError("只允许 SELECT 或 WITH 开头的只读查询。")

    for keyword in FORBIDDEN_SQL_KEYWORDS:
        pattern = rf"\b{keyword}\b"
        if re.search(pattern, lowered):
            raise SQLSafetyError(f"SQL 中包含危险关键字：{keyword}。该项目只允许只读查询。")

    return cleaned


def build_schema_summary(df: pd.DataFrame, table_name: str = "sales_data") -> pd.DataFrame:
    """Return schema summary for UI display."""
    rows = []
    for col in df.columns:
        sample_values = df[col].dropna().head(3).astype(str).tolist()
        rows.append({
            "table_name": table_name,
            "column_name": col,
            "dtype": str(df[col].dtype),
            "non_null_count": int(df[col].notna().sum()),
            "sample_values": ", ".join(sample_values)
        })
    return pd.DataFrame(rows)


def run_readonly_sql(
    df: pd.DataFrame,
    sql: str,
    table_name: str = "sales_data",
    max_rows: int = 200
) -> Tuple[pd.DataFrame, float]:
    """
    Load dataframe into in-memory SQLite and execute read-only SQL.

    The uploaded dataframe is registered as table_name.
    Default table name: sales_data.
    """
    safe_sql = validate_readonly_sql(sql)

    start_time = time.perf_counter()

    conn = sqlite3.connect(":memory:")
    try:
        df.to_sql(table_name, conn, index=False, if_exists="replace")

        # After data is loaded, force SQLite into read-only query mode.
        conn.execute("PRAGMA query_only = ON")

        lowered = safe_sql.lower()
        if " limit " not in lowered and not lowered.endswith(" limit"):
            safe_sql = f"{safe_sql} LIMIT {int(max_rows)}"

        result = pd.read_sql_query(safe_sql, conn)
        elapsed = time.perf_counter() - start_time
        return result, elapsed

    finally:
        conn.close()
