"""Classifier tests — mocked Gemini response, no real API calls."""
from datetime import UTC, datetime
from typing import Literal, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.ai.classifier import ClassificationResult, _build_prompt, classify_item
from app.schemas import RawItem

_NOW = datetime.now(tz=UTC)


def _make_item(title: str, body: str = "", source: str = "hn", subreddit: str | None = None) -> RawItem:
    return RawItem(
        external_id=f"{source}:test",
        source=source,
        subreddit=subreddit,
        author="tester",
        title=title,
        body=body,
        url="https://example.com",
        score=10,
        num_comments=5,
        created_utc=_NOW,
    )


_Tag = Literal["pain", "lead", "trend", "signal", "noise"]


def _mock_response(tag: _Tag, confidence: float = 0.9, reason: str = "test", topics: list = None) -> MagicMock:
    if topics is None:
        topics = []
    payload = ClassificationResult(tag=tag, confidence=confidence, reason=reason, topics=topics)
    mock = MagicMock()
    mock.text = payload.model_dump_json()
    mock.usage_metadata = MagicMock(prompt_token_count=100, candidates_token_count=50)
    return mock


@pytest.mark.parametrize("title,body,expected_tag", [
    (
        "Looking for someone to build an n8n workflow connecting HubSpot to Slack",
        "Budget $500. Need it done this week.",
        "lead",
    ),
    (
        "Why is every project management tool still terrible in 2025?",
        "Tried Asana, Linear, Notion. All miss the point.",
        "pain",
    ),
    (
        "OpenAI releases GPT-5 with 2M context window",
        "Available in API today.",
        "trend",
    ),
    (
        "How I cut client onboarding from 3 days to 2 hours with Make.com",
        "Here's the full workflow breakdown.",
        "signal",
    ),
    (
        "Monday motivation! Grind never stops 💪",
        "",
        "noise",
    ),
])
async def test_classify_item(title: str, body: str, expected_tag: str) -> None:
    item = _make_item(title, body)
    mock_resp = _mock_response(cast(_Tag, expected_tag))

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one=MagicMock(return_value=0)))
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()

    mock_genai_client = MagicMock()
    mock_genai_client.aio.models.generate_content = AsyncMock(return_value=mock_resp)
    with patch("app.ai.classifier._get_client", return_value=mock_genai_client):
        result = await classify_item(item, mock_db)

    assert result.tag == expected_tag
    assert 0.0 <= result.confidence <= 1.0


def test_build_prompt_includes_title() -> None:
    item = _make_item("Need a voice agent for sales calls", source="reddit", subreddit="automation")
    prompt = _build_prompt(item)
    assert "voice agent" in prompt
    assert "REDDIT" in prompt
    assert "r/automation" in prompt


def test_build_prompt_truncates_long_body() -> None:
    item = _make_item("Test", body="x" * 1000)
    prompt = _build_prompt(item)
    # Body preview is capped at 500 chars
    assert "x" * 501 not in prompt
