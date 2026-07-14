"""Shared validator primitives for the investigator seat.

The citation check is mechanical and identical for real and mock LLMs:
a citation must appear verbatim in what the agent was actually shown this
round — the rendered briefing plus this turn's tool outputs.
"""

from __future__ import annotations

GRADES = ("high", "mid", "low")


def verify_citation(citation: str, shown_text: str) -> bool:
    """A citation must be a verbatim substring of the text shown to the
    agent (briefing + this turn's tool outputs)."""
    return isinstance(citation, str) and len(citation.strip()) >= 4 \
        and citation.strip() in shown_text
