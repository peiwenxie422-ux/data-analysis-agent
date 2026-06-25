import pandas as pd

from data_guardrails import dataframe_memory_mb, is_large_dataframe, preview_dataframe


def test_dataframe_memory_mb():
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    assert dataframe_memory_mb(df) > 0


def test_preview_dataframe_small():
    df = pd.DataFrame({"a": [1, 2, 3]})
    preview, sampled = preview_dataframe(df, limit=10)
    assert sampled is False
    assert len(preview) == 3


def test_preview_dataframe_large():
    df = pd.DataFrame({"a": range(100)})
    preview, sampled = preview_dataframe(df, limit=10)
    assert sampled is True
    assert len(preview) == 10


def test_is_large_dataframe_by_shape():
    df = pd.DataFrame({"a": range(100_000)})
    assert is_large_dataframe(df, memory_mb=1.0) is True


if __name__ == "__main__":
    test_dataframe_memory_mb()
    test_preview_dataframe_small()
    test_preview_dataframe_large()
    test_is_large_dataframe_by_shape()
    print("data_guardrails tests passed.")
