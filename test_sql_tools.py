import pandas as pd

from sql_tools import run_readonly_sql, validate_readonly_sql, SQLSafetyError


df = pd.read_csv("data/sample_sales.csv")

print("=== 测试 1：正常 SELECT 查询 ===")
result, elapsed = run_readonly_sql(
    df,
    """
    SELECT product, SUM(sales) AS sales_sum
    FROM sales_data
    GROUP BY product
    ORDER BY sales_sum DESC
    """
)

print(result)
print(f"SQL 查询耗时：{elapsed:.4f} 秒")

print("\n=== 测试 2：危险 SQL 应该被拦截 ===")
try:
    validate_readonly_sql("DROP TABLE sales_data")
    print("错误：危险 SQL 没有被拦截")
except SQLSafetyError as e:
    print("已成功拦截危险 SQL：", e)
