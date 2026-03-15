"""LLM cost estimation engine — maps providers/models to $/token pricing."""

# Pricing in cents per 1K tokens (approximate, as of early 2026)
# Structure: { provider: { model: { "input": cents_per_1k, "output": cents_per_1k } } }
MODEL_PRICING = {
    "openai": {
        "gpt-4.1":          {"input": 0.2,   "output": 0.8},
        "gpt-4.1-mini":     {"input": 0.04,  "output": 0.16},
        "gpt-4.1-nano":     {"input": 0.01,  "output": 0.04},
        "gpt-4o":           {"input": 0.25,  "output": 1.0},
        "gpt-4o-mini":      {"input": 0.015, "output": 0.06},
        "o3-mini":          {"input": 0.11,  "output": 0.44},
    },
    "anthropic": {
        "claude-sonnet-4-20250514":    {"input": 0.3,   "output": 1.5},
        "claude-haiku-3.5":  {"input": 0.08,  "output": 0.4},
        "claude-opus-4":     {"input": 1.5,   "output": 7.5},
    },
    "gemini": {
        "gemini-2.5-pro":   {"input": 0.125, "output": 1.0},
        "gemini-2.5-flash": {"input": 0.015, "output": 0.06},
        "gemini-2.0-flash": {"input": 0.01,  "output": 0.04},
    },
    "nvidia_nim": {
        "llama-3.3-70b":    {"input": 0.04,  "output": 0.04},
        "llama-3.2-3b":     {"input": 0.005, "output": 0.005},
        "mistral-7b":       {"input": 0.005, "output": 0.005},
    },
}

# ── Cheaper alternatives map (used by Auto mode suggestions) ─────────────────
CHEAPER_ALTERNATIVES = {
    ("openai", "gpt-4.1"):           [("openai", "gpt-4.1-mini"), ("openai", "gpt-4.1-nano")],
    ("openai", "gpt-4o"):            [("openai", "gpt-4o-mini"), ("openai", "gpt-4.1-mini")],
    ("anthropic", "claude-sonnet-4-20250514"):   [("anthropic", "claude-haiku-3.5"), ("gemini", "gemini-2.5-flash")],
    ("anthropic", "claude-opus-4"):    [("anthropic", "claude-sonnet-4-20250514"), ("anthropic", "claude-haiku-3.5")],
    ("gemini", "gemini-2.5-pro"):    [("gemini", "gemini-2.5-flash"), ("gemini", "gemini-2.0-flash")],
}

# Token threshold: prompts below this are considered "small" (Rule 1)
SMALL_PROMPT_THRESHOLD = 500


def estimate_cost_cents(provider: str, model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Calculate estimated cost in cents for a single LLM call."""
    pricing = MODEL_PRICING.get(provider, {}).get(model)
    if not pricing:
        # Unknown model — use a conservative default
        return (prompt_tokens + completion_tokens) * 0.001  # ~$0.01 per 1K tokens

    input_cost = (prompt_tokens / 1000) * pricing["input"]
    output_cost = (completion_tokens / 1000) * pricing["output"]
    return round(input_cost + output_cost, 4)


def estimate_savings_cents(
    provider: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> float:
    """Estimate how much could be saved by using the cheapest alternative."""
    current_cost = estimate_cost_cents(provider, model, prompt_tokens, completion_tokens)
    alternatives = CHEAPER_ALTERNATIVES.get((provider, model), [])
    if not alternatives:
        return 0.0
    cheapest_alt = alternatives[-1]  # last is cheapest
    alt_cost = estimate_cost_cents(cheapest_alt[0], cheapest_alt[1], prompt_tokens, completion_tokens)
    savings = current_cost - alt_cost
    return round(max(savings, 0), 4)


def get_auto_mode_recommendation(
    provider: str,
    model: str,
    prompt_tokens: int,
    max_tokens_cap: int | None = None,
) -> dict | None:
    """If Auto mode is on, recommend a cheaper model/cap for this request.
    Returns None if no optimization is possible.
    """
    recommendation = {}

    # Rule 1: small prompts can use smaller models
    if prompt_tokens < SMALL_PROMPT_THRESHOLD:
        alternatives = CHEAPER_ALTERNATIVES.get((provider, model), [])
        if alternatives:
            alt_provider, alt_model = alternatives[0]  # first is closest quality
            recommendation["reroute_to"] = {"provider": alt_provider, "model": alt_model}
            recommendation["reason"] = f"Small prompt ({prompt_tokens} tokens) — routed to {alt_model}"

    # Rule 2: enforce token cap
    if max_tokens_cap:
        recommendation["max_tokens"] = max_tokens_cap

    return recommendation if recommendation else None


def get_all_models() -> list[dict]:
    """Return a flat list of all known models with pricing."""
    models = []
    for provider, provider_models in MODEL_PRICING.items():
        for model, pricing in provider_models.items():
            models.append({
                "provider": provider,
                "model": model,
                "input_cents_per_1k": pricing["input"],
                "output_cents_per_1k": pricing["output"],
            })
    return models
