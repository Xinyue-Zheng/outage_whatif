"""LLM transport interface.

All LLM I/O goes through ``LLMClient`` so a mock/replay implementation can be
substituted in tests — all unit tests run without any LLM server.

The real client (``OllamaLLM``) talks to a local Ollama server through
LangChain's ``langchain-ollama`` integration, with strict JSON output
enforced by passing the JSON schema as Ollama's ``format`` parameter.
"""

from __future__ import annotations

import json
import os


class LLMError(RuntimeError):
    pass


class LLMClient:
    """complete_json(system, user, schema) -> parsed dict."""

    def complete_json(self, system: str, user: str, schema: dict) -> dict:
        raise NotImplementedError


class MockLLM(LLMClient):
    """Scripted responses for tests: dicts, JSON strings, Exceptions, or
    callables ``f(system, user) -> response`` (for multi-step tool->commit
    sequences that react to tool outputs in the accumulated prompt)."""

    def __init__(self, responses: list):
        self.responses = list(responses)
        self.calls: list = []

    def complete_json(self, system, user, schema):
        self.calls.append({"system": system, "user": user})
        if not self.responses:
            raise LLMError("mock exhausted")
        r = self.responses.pop(0)
        if callable(r) and not isinstance(r, Exception):
            r = r(system, user)
        if isinstance(r, Exception):
            raise r
        if isinstance(r, str):
            return json.loads(r)
        return r


class OllamaLLM(LLMClient):
    """Real client: Ollama server via LangChain (``langchain-ollama``),
    strict JSON output via Ollama's ``format`` = the JSON schema.
    Host resolution: explicit arg, else ``OLLAMA_HOST`` env var, else
    http://localhost:11434."""

    def __init__(self, model: str = "llama3.1",
                 max_tokens: int = 4096,
                 host: str | None = None,
                 timeout: float = 300.0):
        from langchain_ollama import ChatOllama
        self.model = model
        self.max_tokens = max_tokens
        host = host or os.environ.get("OLLAMA_HOST") or "http://localhost:11434"
        if not host.startswith(("http://", "https://")):
            host = "http://" + host
        self.host = host.rstrip("/")
        self.timeout = timeout
        self._chat = ChatOllama(model=model, base_url=self.host,
                                num_predict=max_tokens, temperature=0,
                                client_kwargs={"timeout": timeout})

    def complete_json(self, system: str, user: str, schema: dict) -> dict:
        messages = [("system", system), ("human", user)]
        try:
            resp = self._chat.bind(format=schema).invoke(messages)
        except Exception as e:
            raise LLMError(f"ollama request failed: {e}") from e
        text = resp.content if isinstance(resp.content, str) else None
        if not text:
            raise LLMError("empty ollama response")
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise LLMError(f"non-JSON model output: {e}") from e
