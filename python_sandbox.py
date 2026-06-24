from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Any, Dict

import numpy as np
import pandas as pd


class SandboxSafetyError(ValueError):
    """Raised when user-provided Python code violates sandbox rules."""


@dataclass
class SafePythonResult:
    result: pd.DataFrame
    result_type: str
    executed_code: str


FORBIDDEN_NAMES = {
    "__import__", "eval", "exec", "open", "compile", "input",
    "globals", "locals", "vars", "dir", "getattr", "setattr",
    "delattr", "help", "breakpoint",
}

DISALLOWED_NODES = (
    ast.Import,
    ast.ImportFrom,
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.ClassDef,
    ast.Lambda,
    ast.With,
    ast.AsyncWith,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.Try,
    ast.Raise,
    ast.Delete,
    ast.Global,
    ast.Nonlocal,
    ast.Await,
    ast.Yield,
    ast.YieldFrom,
)

SAFE_BUILTINS: Dict[str, Any] = {
    "abs": abs,
    "len": len,
    "sum": sum,
    "min": min,
    "max": max,
    "round": round,
    "sorted": sorted,
    "list": list,
    "dict": dict,
    "tuple": tuple,
    "set": set,
    "range": range,
}


def _validate_ast(tree: ast.AST) -> None:
    for node in ast.walk(tree):
        if isinstance(node, DISALLOWED_NODES):
            raise SandboxSafetyError(f"不允许的 Python 语法：{type(node).__name__}")

        if isinstance(node, ast.Name):
            if node.id.startswith("_") or node.id in FORBIDDEN_NAMES:
                raise SandboxSafetyError(f"不允许访问名称：{node.id}")

        if isinstance(node, ast.Attribute):
            if node.attr.startswith("_") or node.attr in FORBIDDEN_NAMES:
                raise SandboxSafetyError(f"不允许访问属性：{node.attr}")

        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in FORBIDDEN_NAMES:
                raise SandboxSafetyError(f"不允许调用函数：{func.id}")
            if isinstance(func, ast.Attribute) and func.attr in FORBIDDEN_NAMES:
                raise SandboxSafetyError(f"不允许调用方法：{func.attr}")

        if isinstance(node, ast.Assign):
            for target in node.targets:
                if not isinstance(target, ast.Name):
                    raise SandboxSafetyError("只允许给简单变量赋值，例如 result = ...")
                if target.id.startswith("_"):
                    raise SandboxSafetyError(f"不允许给内部变量赋值：{target.id}")


def _to_dataframe(value: Any) -> pd.DataFrame:
    if isinstance(value, pd.DataFrame):
        return value
    if isinstance(value, pd.Series):
        return value.reset_index()
    if isinstance(value, (list, tuple)):
        return pd.DataFrame({"result": list(value)})
    if isinstance(value, dict):
        return pd.DataFrame([value])
    return pd.DataFrame({"result": [value]})


def run_safe_python_analysis(df: pd.DataFrame, code: str) -> SafePythonResult:
    """
    Execute a tightly controlled Pandas/Numpy snippet.

    Allowed:
    - Read-only access to a copied dataframe named df
    - pd / np helpers
    - Assign final output to result, or make the last line an expression

    Blocked:
    - import, file IO, network/system access, functions/classes, loops, eval/exec/open
    """
    if not isinstance(code, str) or not code.strip():
        raise SandboxSafetyError("Python 代码不能为空。")

    tree = ast.parse(code, mode="exec")
    _validate_ast(tree)

    env: Dict[str, Any] = {
        "__builtins__": SAFE_BUILTINS,
        "pd": pd,
        "np": np,
        "df": df.copy(),
    }

    body = list(tree.body)
    last_expr = body[-1] if body and isinstance(body[-1], ast.Expr) else None

    if last_expr is not None:
        exec_tree = ast.Module(body=body[:-1], type_ignores=[])
        ast.fix_missing_locations(exec_tree)
        exec(compile(exec_tree, "<safe_python_sandbox>", "exec"), env, env)
        result_value = eval(
            compile(ast.Expression(last_expr.value), "<safe_python_sandbox>", "eval"),
            env,
            env,
        )
    else:
        exec(compile(tree, "<safe_python_sandbox>", "exec"), env, env)
        if "result" not in env:
            raise SandboxSafetyError("请将最终结果赋值给 result，或把最后一行写成表达式。")
        result_value = env["result"]

    result_df = _to_dataframe(result_value)
    return SafePythonResult(
        result=result_df,
        result_type=type(result_value).__name__,
        executed_code=code.strip(),
    )
