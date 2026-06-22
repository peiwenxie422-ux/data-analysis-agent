import os
from dotenv import load_dotenv
from anthropic import Anthropic


load_dotenv()


def get_anthropic_client():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    base_url = os.getenv("ANTHROPIC_BASE_URL", "https://devaicode.dev")

    if not api_key:
        raise ValueError("没有读取到 ANTHROPIC_API_KEY，请检查 .env 文件。")

    return Anthropic(
        api_key=api_key,
        base_url=base_url,
    )


def explain_analysis_result(user_question: str, result_text: str) -> str:
    """
    让 Claude 基于 Pandas 已经计算出的真实结果进行业务解释。
    重要原则：数值只能来自 Pandas 结果，业务原因只能作为假设。
    """
    model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    client = get_anthropic_client()

    system_prompt = """
你是一个严谨的数据分析 Agent，服务对象是业务用户。

你的职责：
- 根据 Pandas 工具已经计算出的真实结果，生成业务解释。
- 你不能重新计算、猜测或编造结果表中没有的数值。
- 你不能把没有字段支持的业务原因说成事实。
- 你可以提出“可能原因”或“待验证假设”，但必须明确说明需要更多字段或数据验证。
- 如果样本量较小，必须提醒用户结论仅适用于当前样本。
- 如果结果表中没有某个字段，不要引用它。
- 如果用户问题无法被当前结果完全回答，要说明限制。

硬性禁止：
1. 禁止编造同比、环比、增长率、转化率、利润率等结果表中没有的指标。
2. 禁止声称存在促销、节假日、客户画像、库存、利润、渠道策略等信息，除非结果表中明确提供。
3. 禁止把“建议”写成已经发生的事实。
4. 禁止输出过度夸张的结论，比如“绝对领先”“一定说明”“证明了”。

推荐输出结构：
# 分析结论
用 1-2 句话直接回答用户问题。

# 关键数据依据
列出来自结果表的关键数值，必须与结果表一致。

# 业务解读
解释这些数值可能意味着什么。若涉及原因，请使用“可能”“需要进一步验证”。

# 当前限制
说明样本量、字段范围、缺失字段等限制。

# 下一步建议
给出可以落地的分析或业务建议，区分“当前可做”和“需要更多数据才能做”。
"""

    user_prompt = f"""
用户提出的问题：
{user_question}

下面是 Pandas 工具已经计算出的真实结果：
{result_text}

请严格基于这些真实结果进行业务解释。
不要编造结果表中没有的数字或字段。
如果需要推测业务原因，请明确标注为“待验证假设”。
"""

    message = client.messages.create(
        model=model,
        max_tokens=1000,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": user_prompt,
            }
        ],
    )

    return message.content[0].text
