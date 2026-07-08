"""Orchestration-graph topology lock: the round graph's nodes and edges.

Any change request that says "the graph must not change" is proven by this
test passing before and after.  It asserts the exact node set and the exact
edge set (conditional targets included) of the compiled LangGraph.
"""

from pathlib import Path

from outage_whatif.agents import RuleSeat1AllMid, RuleSeat2Cheapest
from outage_whatif.config import Config
from outage_whatif.loop import CaseRunner, CaseSpec
from outage_whatif.loop.graph import build_round_graph
from outage_whatif.provider import SimProvider, generate_world

CASE = Path(__file__).parent.parent / "cases" / "case01_calibration.yaml"

EXPECTED_NODES = {
    "__start__", "advance", "adjudicate_lifecycle", "assess",
    "expand_boundary", "stop_check", "build_tables", "seat1", "seat2",
    "execute", "__end__",
}
EXPECTED_EDGES = {
    ("__start__", "advance"),
    ("advance", "adjudicate_lifecycle"), ("advance", "__end__"),
    ("adjudicate_lifecycle", "assess"),
    ("assess", "expand_boundary"), ("assess", "stop_check"),
    ("expand_boundary", "__end__"),
    ("stop_check", "build_tables"), ("stop_check", "__end__"),
    ("build_tables", "seat1"),
    ("seat1", "seat2"), ("seat1", "__end__"),
    ("seat2", "execute"), ("seat2", "__end__"),
    ("execute", "__end__"),
}


def test_round_graph_topology_is_locked():
    cfg = Config()
    spec = CaseSpec.load(CASE)
    world = generate_world(spec.sim, spec.seed, cfg)
    runner = CaseRunner(spec, SimProvider(world), RuleSeat1AllMid(),
                        RuleSeat2Cheapest(), cfg)
    g = build_round_graph(runner).get_graph()
    assert {n for n in g.nodes} == EXPECTED_NODES
    assert {(e.source, e.target) for e in g.edges} == EXPECTED_EDGES
