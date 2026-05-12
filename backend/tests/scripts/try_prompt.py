"""One-off fixture test for classifier prompt. Run from backend/: uv run python tests/scripts/try_prompt.py"""
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent.parent  # content_intel/
sys.path.insert(0, str(ROOT / "backend"))

# Load .env from project root before importing settings
from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from google import genai
from google.genai import types

from datetime import datetime, timezone

from app.ai import genai_with_retry
from app.ai.classifier import ClassificationResult, _build_prompt
from app.config import settings
from app.schemas import RawItem

_NOW = datetime.now(tz=timezone.utc)

FIXTURE = Path(__file__).parent.parent / "fixtures" / "sample_posts.json"

_client = genai.Client(api_key=settings.gemini_api_key)


async def classify_direct(item: RawItem) -> ClassificationResult:
    response = await genai_with_retry(
        lambda: _client.aio.models.generate_content(
            model=settings.gemini_classify_model,
            contents=_build_prompt(item),
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ClassificationResult,
                temperature=0.0,
                max_output_tokens=1024,
            ),
        )
    )
    text = response.text
    if not text:
        raise ValueError("Empty response from model")
    return ClassificationResult.model_validate_json(text)


async def main() -> None:
    posts = json.loads(FIXTURE.read_text())
    passed = 0

    for post in posts:
        expected = post.pop("expected_tag")
        fields = {k: v for k, v in post.items() if k in RawItem.model_fields}
        fields.setdefault("created_utc", _NOW)
        item = RawItem(**fields)
        result = await classify_direct(item)

        ok = result.tag == expected
        passed += ok
        status = "✓" if ok else "✗"
        print(f"{status}  [{expected:7s} → {result.tag:7s}]  conf={result.confidence:.2f}  {item.title[:65]}")
        if not ok:
            print(f"     reason: {result.reason}")

    print(f"\n{passed}/{len(posts)} passed")
    if passed < len(posts):
        sys.exit(1)


asyncio.run(main())
