from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod

from bridgescout.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL
from bridgescout.ingestion.preprocessing import split_sentences

_CUE_PHRASES = [
    "however",
    "limitation",
    "future work",
    "future research",
    "remains a challenge",
    "does not",
    "fails to",
    "should explore",
    "should investigate",
    "should address",
    "should focus on",
    "is costly",
    "is expensive",
    "time-consuming",
    "is poor",
    "drops",
    "degrade",
    "challenge because",
    "is needed",
    "prohibitively",
]


class LLMClient(ABC):
    """Pluggable interface for gap extraction and paraphrasing."""

    @abstractmethod
    def extract_gaps(self, text: str) -> list[str]:
        """Return a list of limitation / future-work statements found in text."""

    @abstractmethod
    def paraphrase_generic(self, gap_text: str, domain: str) -> str:
        """Rewrite a domain-specific gap statement as a domain-neutral problem statement."""


class HeuristicLLMClient(LLMClient):
    """Regex/cue-phrase based fallback used when no LLM API key is configured."""

    def extract_gaps(self, text: str) -> list[str]:
        sentences = split_sentences(text)
        gaps = [s for s in sentences if any(cue in s.lower() for cue in _CUE_PHRASES)]
        return gaps or sentences[:1]

    def paraphrase_generic(self, gap_text: str, domain: str) -> str:
        # No LLM available: strip domain-specific proper nouns is out of scope for a
        # heuristic fallback, so we return the original sentence unchanged.
        return gap_text


class AnthropicLLMClient(LLMClient):
    def __init__(self, model: str = ANTHROPIC_MODEL, api_key: str = ANTHROPIC_API_KEY):
        import anthropic

        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def extract_gaps(self, text: str) -> list[str]:
        prompt = (
            "You are analyzing a research paper excerpt. Extract every distinct "
            "unresolved research problem, limitation, or future-work suggestion "
            "mentioned in the text below. Return ONLY a JSON array of short strings, "
            "one per gap, with no extra commentary.\n\nTEXT:\n" + text
        )
        response = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = "".join(block.text for block in response.content if hasattr(block, "text"))
        return _parse_json_string_list(raw)

    def paraphrase_generic(self, gap_text: str, domain: str) -> str:
        prompt = (
            f"The following research limitation is from the domain '{domain}':\n"
            f'"{gap_text}"\n\n'
            "Rewrite it as a single generic, domain-neutral problem statement that "
            "describes the underlying technical challenge without naming the specific "
            "field, application, or dataset. Return ONLY the rewritten sentence."
        )
        response = self._client.messages.create(
            model=self._model,
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = "".join(block.text for block in response.content if hasattr(block, "text"))
        return raw.strip().strip('"')


def _parse_json_string_list(raw: str) -> list[str]:
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    candidate = match.group(0) if match else raw
    try:
        parsed = json.loads(candidate)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
    except json.JSONDecodeError:
        pass
    return [line.strip("- ").strip() for line in raw.splitlines() if line.strip()]


def get_llm_client() -> LLMClient:
    if ANTHROPIC_API_KEY:
        return AnthropicLLMClient()
    return HeuristicLLMClient()
