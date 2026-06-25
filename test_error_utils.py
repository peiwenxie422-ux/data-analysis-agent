from error_utils import format_exception_for_user


class SandboxSafetyError(ValueError):
    pass


class SQLSafetyError(ValueError):
    pass


def test_error_messages():
    assert "\u4ee3\u7801\u672a\u901a\u8fc7\u5b89\u5168\u6821\u9a8c" in format_exception_for_user(SandboxSafetyError("blocked import"))
    assert "SQL \u53ea\u8bfb\u5b89\u5168\u6821\u9a8c\u5931\u8d25" in format_exception_for_user(SQLSafetyError("only SELECT"))
    assert "\u5f53\u524d\u6570\u636e\u96c6\u4e2d\u6ca1\u6709\u627e\u5230\u9700\u8981\u7684\u5b57\u6bb5" in format_exception_for_user(KeyError("sales"))
    assert "\u5206\u6790\u53c2\u6570\u9519\u8bef" in format_exception_for_user(ValueError("bad column"))


if __name__ == "__main__":
    test_error_messages()
    print("error_utils tests passed.")
