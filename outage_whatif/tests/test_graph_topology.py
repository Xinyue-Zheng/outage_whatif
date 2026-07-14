"""Locks the investigator round graph: exact node set and edge set.

The orchestration shape is part of the design — changing it must break a
test.  advance -> adjudicate_lifecycle -> assess -> stop_check -> briefing
-> investigator -> gate -> execute -> reconcile, with the gate's
single-retry edge back to the investigator.
"""

from pathlib import Path

from outage_whatif.agents import Investigator, MockLLM
from outage_whatif.config import Config
from outage_whatif.loop import CaseRunner, CaseSpec
from outage_whatif.loop.graph import build_round_graph
from outage_whatif.provider import SimProvider, generate_world

CFG = Config()
CASE01 = Path(__file__).parent.parent / "cases" / "case01.yaml"

NODES = {"advance", "adjudicate_lifecycle", "assess", "stop_check",
         "briefing", "investigator", "gate", "execute", "reconcile"}

EDGES = {
    ("__start__", "advance"),
    ("advance", "adjudicate_lifecycle"),
    ("advance", "__end__"),
    ("adjudicate_lifecycle", "assess"),
    ("assess", "stop_check"),
    ("stop_check", "briefing"),
    ("stop_check", "__end__"),
    ("briefing", "investigator"),
    ("investigator", "gate"),
    ("investigator", "__end__"),
    ("gate", "execute"),
    ("gate", "investigator"),           # denial -> single retry
    ("gate", "__end__"),
    ("execute", "reconcile"),
    ("reconcile", "__end__"),
}


def test_round_graph_topology_is_locked():
    spec = CaseSpec.load(CASE01)
    world = generate_world(spec.sim, spec.seed, CFG)
    runner = CaseRunner(spec, SimProvider(world),
                        Investigator(MockLLM([]), CFG), CFG)
    g = build_round_graph(runner).get_graph()
    assert set(g.nodes) - {"__start__", "__end__"} == NODES
    assert {(e.source, e.target) for e in g.edges} == EDGES
