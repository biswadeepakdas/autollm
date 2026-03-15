"""Tests for the LLM cost estimation engine (pure functions, no DB needed)."""

import pytest

from app.services.cost_engine import estimate_cost_cents


async def test_openai_gpt4o_cost():
    """GPT-4o: input=0.25c/1K, output=1.0c/1K."""
    cost = estimate_cost_cents("openai", "gpt-4o", prompt_tokens=1000, completion_tokens=1000)
    # (1000/1000)*0.25 + (1000/1000)*1.0 = 1.25
    assert cost == pytest.approx(1.25, abs=0.001)


async def test_anthropic_claude_cost():
    """Claude Sonnet 4: input=0.3c/1K, output=1.5c/1K."""
    cost = estimate_cost_cents(
        "anthropic", "claude-sonnet-4-20250514",
        prompt_tokens=2000, completion_tokens=500,
    )
    # (2000/1000)*0.3 + (500/1000)*1.5 = 0.6 + 0.75 = 1.35
    assert cost == pytest.approx(1.35, abs=0.001)


async def test_unknown_model_cost():
    """Unknown models use the conservative fallback: (prompt+completion)*0.001."""
    cost = estimate_cost_cents(
        "some_provider", "some_model",
        prompt_tokens=1000, completion_tokens=500,
    )
    # (1000+500)*0.001 = 1.5
    assert cost == pytest.approx(1.5, abs=0.001)


async def test_zero_tokens():
    """Zero tokens should produce zero cost for any model."""
    cost = estimate_cost_cents("openai", "gpt-4o", prompt_tokens=0, completion_tokens=0)
    assert cost == 0.0

    cost_unknown = estimate_cost_cents("x", "y", prompt_tokens=0, completion_tokens=0)
    assert cost_unknown == 0.0
