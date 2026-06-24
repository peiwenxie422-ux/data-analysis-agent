import pandas as pd

from python_sandbox import SandboxSafetyError, run_safe_python_analysis


df = pd.read_csv("data/sample_sales.csv")

print("=== Safe Python sandbox allowed analysis ===")
allowed = 'result = df.groupby("product")["sales"].sum().reset_index()'
output = run_safe_python_analysis(df, allowed)
print(output.result)
assert output.result.shape[0] >= 1
assert "sales" in output.result.columns

print("\n=== Safe Python sandbox blocks import ===")
try:
    run_safe_python_analysis(df, "import os\nresult = df.head()")
    raise AssertionError("import should have been blocked")
except SandboxSafetyError as e:
    print("Blocked import:", e)

print("\n=== Safe Python sandbox blocks open ===")
try:
    run_safe_python_analysis(df, 'result = open("x.txt", "w")')
    raise AssertionError("open should have been blocked")
except SandboxSafetyError as e:
    print("Blocked open:", e)

print("\nSafe Python sandbox tests passed.")
