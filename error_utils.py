"""User-facing error formatting helpers for Streamlit UI."""

def _clean_detail(exc: Exception) -> str:
    detail = str(exc).strip()
    return detail or exc.__class__.__name__


def format_exception_for_user(exc: Exception) -> str:
    """Convert technical exceptions into clear UI-safe messages."""
    detail = _clean_detail(exc)
    name = exc.__class__.__name__

    if name == "SandboxSafetyError":
        return "\u4ee3\u7801\u672a\u901a\u8fc7\u5b89\u5168\u6821\u9a8c\uff1a" + detail

    if name == "SQLSafetyError":
        return "SQL \u53ea\u8bfb\u5b89\u5168\u6821\u9a8c\u5931\u8d25\uff1a" + detail

    if isinstance(exc, KeyError):
        return "\u5f53\u524d\u6570\u636e\u96c6\u4e2d\u6ca1\u6709\u627e\u5230\u9700\u8981\u7684\u5b57\u6bb5\uff1a" + detail

    if isinstance(exc, ValueError):
        return "\u5206\u6790\u53c2\u6570\u9519\u8bef\uff1a" + detail

    return "\u6267\u884c\u5931\u8d25\uff1a" + detail
