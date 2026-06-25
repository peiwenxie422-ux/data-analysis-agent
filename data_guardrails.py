"""Lightweight DataFrame size and preview guardrails."""

import pandas as pd

PREVIEW_ROW_LIMIT = 10
LARGE_DATASET_ROWS = 100_000
LARGE_DATASET_CELLS = 1_000_000
LARGE_DATASET_MEMORY_MB = 100.0


def dataframe_memory_mb(df: pd.DataFrame) -> float:
    """Return approximate DataFrame memory usage in MB."""
    return float(df.memory_usage(deep=True).sum() / 1024 / 1024)


def is_large_dataframe(df: pd.DataFrame, memory_mb=None) -> bool:
    """Detect datasets that may slow down Streamlit rendering."""
    if memory_mb is None:
        memory_mb = dataframe_memory_mb(df)

    total_cells = df.shape[0] * df.shape[1]
    return (
        df.shape[0] >= LARGE_DATASET_ROWS
        or total_cells >= LARGE_DATASET_CELLS
        or memory_mb >= LARGE_DATASET_MEMORY_MB
    )


def preview_dataframe(df: pd.DataFrame, limit: int = PREVIEW_ROW_LIMIT):
    """Return a small preview frame and whether sampling was used."""
    if len(df) <= limit:
        return df.head(limit), False

    return df.sample(n=limit, random_state=42).sort_index(), True
