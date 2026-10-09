from __future__ import annotations

import hashlib
import json
import logging
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
# worth retrying on the next model
FAILOVER_STATUS = frozenset({429, 500, 502, 503, 504})
COOLDOWN_SECONDS = {"rate-limited": 60, "overloaded": 20, "timed out": 15}
MIN_ATTEMPT_SECONDS = 0.8
PRIMARY_SHARE = 0.6


class LLMError(Exception):
    pass


@dataclass(frozen=True)
class Turn:
    role: str  # "user" or "model"
    text: str


class LLMClient(Protocol):
    model: str

    def generate(
        self,
        system: str,
        turns: list[Turn],
        *,
        temperature: float = 0.6,
        max_tokens: int = 400,
        json_schema: dict | None = None,
        deadline: float | None = None,
    ) -> str: ...


class GeminiClient:
    def __init__(self, api_key: str, models: str | list[str], timeout: float = 6.0, thinking_level: str = "minimal"):
        self.api_key, self.timeout, self.thinking_level = api_key, timeout, thinking_level
        self.models = [models] if isinstance(models, str) else list(models)
        self.model = self.models[0]

    def generate(
        self,
        system: str,
        turns: list[Turn],
        *,
        temperature: float = 0.6,
        max_tokens: int = 400,
        json_schema: dict | None = None,
        deadline: float | None = None,
    ) -> str:
        config: dict = {"temperature": temperature, "maxOutputTokens": max_tokens}
        if json_schema:
            config["responseMimeType"] = "application/json"
            config["responseSchema"] = json_schema
        if self.thinking_level:
            # thinking tokens count against maxOutputTokens
            config["thinkingConfig"] = {"thinkingLevel": self.thinking_level}
        body = json.dumps(
            {
                "systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": t.role, "parts": [{"text": t.text}]} for t in _normalise(turns)],
                "generationConfig": config,
            }
        ).encode()
        ends_at = time.monotonic() + (deadline or self.timeout * len(self.models))
        failures = []
        for model in self.models:
            if cache.get(f"llm:cooldown:{model}"):
                failures.append(f"{model}: cooling down")
                continue
            remaining = ends_at - time.monotonic()
            if remaining < MIN_ATTEMPT_SECONDS:
                failures.append(f"{model}: out of time")
                break
            # leave part of the budget for the fallback model
            share = PRIMARY_SHARE if model != self.models[-1] else 1.0
            try:
                return self._call(model, body, timeout=min(self.timeout, max(remaining * share, MIN_ATTEMPT_SECONDS)))
            except _Unavailable as exc:
                cache.set(f"llm:cooldown:{model}", True, COOLDOWN_SECONDS[exc.kind])
                logger.warning("Gemini %s %s; skipping it for %ss", model, exc.kind, COOLDOWN_SECONDS[exc.kind])
                failures.append(f"{model}: {exc.kind}")
        raise LLMError("No Gemini model available: " + "; ".join(failures))

    def _call(self, model: str, body: bytes, timeout: float) -> str:
        request = urllib.request.Request(
            API_URL.format(model=model),
            data=body,
            headers={"Content-Type": "application/json", "x-goog-api-key": self.api_key},
            method="POST",
        )
        started = time.monotonic()
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                data = json.load(response)
        except urllib.error.HTTPError as exc:
            detail = exc.read()[:300].decode(errors="replace")
            if exc.code in FAILOVER_STATUS:
                raise _Unavailable("rate-limited" if exc.code == 429 else "overloaded") from exc
            raise LLMError(f"Gemini HTTP {exc.code}: {detail}") from exc
        except TimeoutError as exc:
            raise _Unavailable("timed out") from exc
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, TimeoutError):
                raise _Unavailable("timed out") from exc
            raise LLMError(f"Gemini request failed: {exc}") from exc
        except ValueError as exc:
            raise LLMError(f"Gemini returned invalid JSON: {exc}") from exc

        candidate = (data.get("candidates") or [{}])[0]
        text = "".join(p.get("text", "") for p in candidate.get("content", {}).get("parts", []) if not p.get("thought")).strip()
        if candidate.get("finishReason") == "MAX_TOKENS":
            text = _last_complete_sentence(text)
        if not text:
            reason = candidate.get("finishReason") or data.get("promptFeedback", {}).get("blockReason", "unknown")
            raise LLMError(f"Gemini returned no usable text (reason: {reason})")
        logger.info("Gemini %s answered in %.0f ms", model, (time.monotonic() - started) * 1000)
        return text


class _Unavailable(Exception):
    def __init__(self, kind: str):
        super().__init__(kind)
        self.kind = kind


def _last_complete_sentence(text: str) -> str:
    match = re.search(r"^(.*[.!?।])", text, re.S)
    return match.group(1).strip() if match else ""


def _normalise(turns: list[Turn]) -> list[Turn]:
    # Gemini wants a user turn first and alternating roles
    merged: list[Turn] = []
    for turn in turns:
        if not merged and turn.role != "user":
            continue
        if merged and merged[-1].role == turn.role:
            merged[-1] = Turn(turn.role, f"{merged[-1].text}\n\n{turn.text}")
        else:
            merged.append(turn)
    return merged


_override: LLMClient | None = None


def get_client() -> LLMClient | None:
    if _override is not None:
        return _override
    if not settings.GEMINI_API_KEY:
        return None
    models = [settings.GEMINI_MODEL, *settings.GEMINI_FALLBACK_MODELS]
    return GeminiClient(settings.GEMINI_API_KEY, list(dict.fromkeys(models)), settings.GEMINI_TIMEOUT, settings.GEMINI_THINKING_LEVEL)


def set_client(client: LLMClient | None) -> None:
    global _override
    _override = client


def within_budget(scope: str) -> bool:
    scope = hashlib.sha256(scope.encode()).hexdigest()[:16]
    minute = int(time.time() // 60)
    hour = int(time.time() // 3600)
    checks = [
        (f"llm:rpm:{minute}", settings.GEMINI_MAX_RPM, 70),
        (f"llm:visitor:{scope}:{hour}", settings.GEMINI_MAX_PER_VISITOR_HOUR, 3700),
    ]
    for key, limit, ttl in checks:
        cache.add(key, 0, ttl)
        if cache.incr(key) > limit:
            logger.warning("LLM budget exhausted for %s", key)
            return False
    return True
