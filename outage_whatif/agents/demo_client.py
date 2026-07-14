"""A deterministic demo stand-in for the LLM transport.

``DemoInvestigatorClient`` implements ``LLMClient.complete_json`` with a
scripted policy over the investigator protocol, so the full round loop runs
end-to-end with no Ollama server (the acceptance demo and the CLI default).
It is a TRANSPORT substitute like MockLLM — the investigator seat, its
protocol, and the gate treat it exactly like a real model.  It is never a
runtime fallback: with ``--llm ollama`` the real client is used and a
failing model skips rounds, per the no-fallback rule.

Policy per round: write one notebook line, then commit the first applicable
purchase — fund the demand ledger, probe hypothesized objects, then work
ticketed claims by their briefed remedies, then explore unlocalized cells —
citing the exact briefing line it acted on.  Every commit is remembered, so
a gate denial makes the single retry pick the next option.
"""

from __future__ import annotations

import re

from .llm import LLMClient

_BUCKET = {"target_kpi": "heavy_cells_present", "probe": "target_present",
           "densify": "interval_above", "pm_hourly": "middle_zone",
           "pm_15min": "support", "profile": "anchor_confirms"}

_GAP_RE = re.compile(r"^  (GAP:\S+) \| (\S+) \| (\S+) \| .*$", re.M)
_CLAIM_RE = re.compile(
    r"^  ((?:COV|ROB|CAP)\S*) \| (\w+) \| .* \| remedy: (.+)$", re.M)


class DemoInvestigatorClient(LLMClient):
    def __init__(self):
        self.attempted: set = set()     # (kind, target) ever committed

    # ------------------------------------------------------------ protocol
    def complete_json(self, system, user, schema):
        if "TOOL notebook_write" not in user:
            plan = self._plan(user)
            note = (f"plan: {plan['kind']} on {plan['target']}"
                    if plan else "no applicable action; declaring done")
            return {"tool": "notebook_write", "args": {"text": note}}
        plan = self._plan(user)
        if plan is None:
            return {"commit": {"action": "declare_done",
                               "rationale": "no gap and no ticket left"}}
        confidence = "high" if "confidence cap" in user else "mid"
        self.attempted.add((plan["kind"], plan["target"]))
        return {"commit": {
            "action": "purchase", "kind": plan["kind"],
            "target": plan["target"], "params": plan["params"],
            "predicted_bucket": _BUCKET[plan["kind"]],
            "confidence": confidence, "citation": plan["citation"].strip(),
            "rationale": "demo policy"}}

    # ------------------------------------------------------------ policy
    def _plan(self, user: str) -> dict | None:
        briefing = user.split("\nTOOL ")[0]

        def option(kind, target, params, citation):
            if (kind, target) in self.attempted:
                return None
            return {"kind": kind, "target": target, "params": params,
                    "citation": citation}

        gaps = list(_GAP_RE.finditer(briefing))
        for m in gaps:
            gid, kind, subject = m.group(1), m.group(2), m.group(3)
            if kind == "demand_ledger_absent":
                o = option("target_kpi", gid, {}, m.group(0))
                if o:
                    return o
            if kind == "object_hypothesized":
                o = option("probe", gid, {"object": subject, "n": 6},
                           m.group(0))
                if o:
                    return o

        for m in _CLAIM_RE.finditer(briefing):
            cid, remedy = m.group(1), m.group(3)
            for kind in ("densify", "pm_hourly", "pm_15min"):
                if remedy.startswith(kind):
                    o = option(kind, cid, {}, m.group(0))
                    if o:
                        return o

        for m in gaps:                       # exploration fallback
            gid, kind = m.group(1), m.group(2)
            if kind in ("cell_unlocalized", "residual_uninvestigated"):
                o = option("probe", gid, {"use_suggested_probes": True},
                           m.group(0))
                if o:
                    return o
        return None
