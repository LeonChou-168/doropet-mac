"""
Token 成本计算器。

基于已知模型定价表估算单次对话的费用。
价格以 2025 Q4 为参考，实际使用时请更新。
"""

# 已知模型定价（USD / 1M tokens），格式: (input_price, output_price)
_MODEL_PRICING = {
    # OpenAI
    "gpt-4o":               (2.50, 10.00),
    "gpt-4o-mini":          (0.15, 0.60),
    "gpt-4-turbo":          (10.00, 30.00),
    "gpt-3.5-turbo":        (0.50, 1.50),
    # DeepSeek
    "deepseek-chat":        (0.14, 0.28),
    "deepseek-reasoner":    (0.55, 2.19),
    # Anthropic
    "claude-3-5-sonnet":    (3.00, 15.00),
    "claude-3-haiku":       (0.25, 1.25),
    # Google
    "gemini-2.5-flash":     (0.15, 0.60),
    "gemini-1.5-flash":     (0.075, 0.30),
    "gemini-1.5-pro":       (1.25, 5.00),
    # Groq
    "llama-3.3-70b":        (0.59, 0.79),
    "llama-3.1-8b":         (0.05, 0.08),
    # Moonshot
    "moonshot-v1-8k":       (0.016, 0.016),
    "moonshot-v1-32k":      (0.024, 0.024),
    "moonshot-v1-128k":     (0.060, 0.060),
    # Alibaba
    "qwen-turbo":           (0.016, 0.016),
    "qwen-plus":            (0.032, 0.032),
    "qwen-max":             (0.080, 0.080),
    # Zhipu
    "glm-4-flash":          (0.016, 0.016),
    "glm-4":                (0.050, 0.050),
    # Ollama (local)
    "llama3.2":             (0.0, 0.0),
    "qwen2.5":              (0.0, 0.0),
}


def estimate_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    """估算 Token 费用。

    Args:
        model: 模型名称
        tokens_in: 输入 token 数
        tokens_out: 输出 token 数

    Returns:
        估算费用（USD）
    """
    price_in, price_out = _MODEL_PRICING.get(model, (None, None))

    if price_in is None:
        for key, prices in _MODEL_PRICING.items():
            if model.startswith(key):
                price_in, price_out = prices
                break

    if price_in is None:
        price_in, price_out = 0.0, 0.0

    cost = (tokens_in / 1_000_000) * price_in + (tokens_out / 1_000_000) * price_out
    return round(cost, 6)
