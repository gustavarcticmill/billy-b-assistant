"""Utility functions for retrieving fresh information from the public web."""

from __future__ import annotations

import asyncio
from typing import Iterable

import aiohttp


DUCKDUCKGO_API_ENDPOINT = "https://api.duckduckgo.com/"


async def fetch_duckduckgo_results(query: str, *, max_entries: int = 4) -> list[str]:
    """Return up to ``max_entries`` concise snippets for the given query.

    Uses the DuckDuckGo Instant Answer API, which is anonymous and does not
    require an API key. The API can occasionally respond with nested related
    topics, so we walk the structure recursively until we have collected enough
    human-readable snippets.
    """

    params = {
        "q": query,
        "format": "json",
        "no_html": 1,
        "skip_disambig": 1,
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(DUCKDUCKGO_API_ENDPOINT, params=params) as resp:
                if resp.status != 200:
                    return [
                        f"DuckDuckGo search failed with HTTP status {resp.status}."
                    ]
                payload = await resp.json(content_type=None)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # pragma: no cover - network failure path
            return [f"DuckDuckGo search failed: {exc}"]

    snippets: list[str] = []

    def _consume(items: Iterable[dict | str]):
        for item in items:
            if isinstance(item, str):
                if item.strip():
                    snippets.append(item.strip())
            elif isinstance(item, dict):
                text = item.get("Text") or item.get("Result") or item.get("Topic")
                if text and isinstance(text, str):
                    snippets.append(text.strip())
                nested = item.get("RelatedTopics") or item.get("Topics")
                if isinstance(nested, list):
                    _consume(nested)
            if len(snippets) >= max_entries:
                break

    abstract = payload.get("AbstractText")
    if isinstance(abstract, str) and abstract.strip():
        snippets.append(abstract.strip())

    related = payload.get("RelatedTopics")
    if isinstance(related, list) and len(snippets) < max_entries:
        _consume(related)

    if not snippets:
        heading = payload.get("Heading")
        if isinstance(heading, str) and heading.strip():
            snippets.append(f"No instant answer found. Top heading: {heading.strip()}.")
        else:
            snippets.append("No instant answer or related topics found for that query.")

    unique_snippets: list[str] = []
    seen: set[str] = set()
    for snippet in snippets:
        if snippet not in seen:
            seen.add(snippet)
            unique_snippets.append(snippet)
        if len(unique_snippets) >= max_entries:
            break

    return unique_snippets


async def web_search_summary(query: str) -> str:
    """Generate a short, human-friendly summary of a web search query."""

    results = await fetch_duckduckgo_results(query)
    if not results:
        return "I couldn't find anything relevant in the instant answers."  # pragma: no cover

    if len(results) == 1:
        return results[0]

    formatted = "\n".join([f"- {snippet}" for snippet in results])
    return f"Here is what I found:\n{formatted}"
