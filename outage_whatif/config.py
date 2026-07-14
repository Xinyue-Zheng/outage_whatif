"""Central configuration.

Everything tunable lives here.  Values may be overridden by a ``config.yaml``
sitting next to this file (top-level keys map onto Config fields; the nested
``policy`` mapping onto Policy fields).

The ``Policy`` dataclass is the clearly-labelled "policy rules" section:
every threshold marked [POLICY] in the design requires advisor sign-off
before being changed.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from pathlib import Path


# =====================================================================
# POLICY RULES — ADVISOR SIGN-OFF REQUIRED
# Every constant in this block is a [POLICY] value: it encodes a
# discretionary judgment, not a definitional rule.  Do not change
# without recorded advisor approval.
# =====================================================================
@dataclass(frozen=True)
class Policy:
    # [POLICY] coverage pass proportion the Wilson interval is tested against
    theta: float = 0.90
    # [POLICY] PRB utilisation level treated as "no headroom"
    pi_hi: float = 0.85
    # [POLICY] max tolerable top-owner share of best alternatives (robustness)
    kappa: float = 0.60
    # [POLICY] raster settlements below this population are not offered as
    # candidate pins (pin granularity only — severity no longer uses
    # population)
    P_min: int = 50
    # [POLICY] major-exit share: a neighbor is a genuine exit for an object
    # iff it is best alternative for >= sigma of that object's footprint cells
    sigma: float = 0.20
    # [POLICY] 15-minute tier: refute iff fraction of bins >= pi_hi exceeds this
    cap15_refute_frac: float = 0.10
    # [POLICY] calibration: max false-pass rate allowed for the hourly
    # support-zone edge
    calib_false_pass_max: float = 0.05
    # [POLICY] comparable-days matching for per-hour capacity evidence:
    # k matched occurrences of the analysis hour (same clock-hour AND same
    # weekday, most recent k weeks; holiday outages match holiday-class
    # days instead; days on the known-outage list are excluded).
    # With k=4 the 15-minute tier sees 4k=16 bins, so cap15_refute_frac=0.10
    # refutes at >1.6 bins, i.e. >= 2 spiking bins of 16 — one isolated
    # spike is forgiven, two are not (documented sensible mapping).
    comparable_days_k: int = 4
    # [POLICY] default analysis_hour selection when the ticket omits it:
    # busiest hour of the window per the target's held historical profile,
    # else the window midpoint.  Which rule fired is recorded in the report.
    analysis_hour_default_rule: str = "busiest_profile_else_midpoint"
    # [POLICY] candidate zone margin: the zone is "closer to the target than
    # to its second-nearest site", buffered outward by this many metres
    candidate_margin_m: float = 500.0
    # [POLICY] busy-window traffic (T[c], mean RRC-connected users at the
    # analysis hour) above which an unknown/unaccounted cell is a gap the
    # audit must surface.  DESIGN-GAP: illustrative value pending advisor
    # sign-off.
    T_material: float = 50.0
    # [POLICY] a hole is severe iff its object is the sole non-dismissed
    # explanation for some cell with T[c] >= T_severe.  DESIGN-GAP:
    # illustrative value pending advisor sign-off.
    T_severe: float = 200.0
    # [POLICY] objects whose importance bound exceeds this (traffic units)
    # with an open claim are audit gaps.  DESIGN-GAP: illustrative value
    # pending advisor sign-off.
    importance_floor: float = 30.0
    # [POLICY] max unaccounted share of target busy-window traffic
    # compatible with declaring "fully absorbable"
    rho_residual: float = 0.12


@dataclass(frozen=True)
class Config:
    # ---------------- statistics ----------------
    z: float = 1.96                       # Wilson z-score

    # ---------------- radio / footprint ----------------
    tau_acc: float = -110.0               # dBm access threshold for footprint
                                          # membership and qualifying alternatives

    # ---------------- geometry ----------------
    pixel_m: float = 100.0                # population raster pixel size
    evidence_cell_m: float = 300.0        # effective-evidence cell size
    density_min_pop: float = 1.0          # raster density filter (pop per pixel)
    min_settlement_pixels: int = 3        # smaller fragments are not offered
                                          # as candidate pins

    # ---------------- demand localization ----------------
    n_min_units_per_cell: int = 3         # sampled evidence units served by a
                                          # target cell before its demand
                                          # direction is considered mapped
    dismiss_min_units: int = 4            # sampled units inside an object,
                                          # none showing the target, required
                                          # to verify a DismissRequest
    min_dir_samples: int = 3              # bearings needed before
                                          # empirical_direction is defined
    suggested_random_probes: int = 8      # exploration probe locations
                                          # generated at setup and surfaced as
                                          # a suggested gap-remedy (never
                                          # auto-executed)

    # ---------------- sampling ----------------
    densify_cells_per_round: int = 12     # unsampled evidence cells per densification

    # ---------------- claims / lifecycle ----------------
    split_after_densifications: int = 2   # coverage split trigger
    capacity_drilldown: bool = True       # False: site-level analysis only —
                                          # stuck capacity claims never spawn
                                          # per-cell children (use when the
                                          # data source has no per-cell PM)
    drilldown_after_rounds: int = 2       # capacity drill-down trigger
    cluster_sep_cells: float = 1.5        # pass/fail centroid separation (in
                                          # evidence-cell units) counted as clustered

    # ---------------- investigator ----------------
    agent_retries: int = 1                # one re-prompt with the validator
                                          # error, then the round is skipped
    max_tool_calls_per_round: int = 8     # read-only tool calls per round
    price_low_frac: float = 0.02          # gate cap: low confidence may spend
                                          # at most this fraction of B_initial
    price_mid_frac: float = 0.10          # gate cap for mid confidence
                                          # (high confidence: up to 1.0)

    # ---------------- loop ----------------
    stable_rounds_to_stop: int = 2
    max_rounds: int = 60                  # hard safety stop

    # ---------------- LLM ----------------
    llm_model: str = "llama3.1"           # ollama model tag
    llm_max_tokens: int = 4096
    ollama_host: str = ""                 # "" -> $OLLAMA_HOST or localhost:11434

    # ---------------- calendar ----------------
    # DESIGN-GAP: small illustrative holiday calendar; a real deployment
    # would load a per-country calendar.
    holidays: tuple = (
        "2025-01-01", "2025-05-01", "2025-12-24", "2025-12-25", "2025-12-26",
        "2026-01-01", "2026-04-06", "2026-05-01", "2026-07-04",
        "2026-12-24", "2026-12-25", "2026-12-26",
    )
    # months considered "summer season" for seasonal-settlement flags
    summer_months: tuple = (6, 7, 8)
    # ISO dates with known outages — excluded from comparable-day matching
    known_outage_dates: tuple = ()

    # ---------------- policy section ----------------
    policy: Policy = field(default_factory=Policy)


def _apply_overrides(cfg: Config, overrides: dict) -> Config:
    pol_over = overrides.pop("policy", None) or {}
    pol = dataclasses.replace(cfg.policy, **pol_over) if pol_over else cfg.policy
    known = {f.name for f in dataclasses.fields(Config)}
    unknown = set(overrides) - known
    if unknown:
        raise KeyError(f"unknown config keys in config.yaml: {sorted(unknown)}")
    return dataclasses.replace(cfg, policy=pol, **overrides)


def load_config() -> Config:
    """Default config, with optional overrides from config.yaml next to this file."""
    cfg = Config()
    yaml_path = Path(__file__).parent / "config.yaml"
    if yaml_path.exists():
        import yaml
        overrides = yaml.safe_load(yaml_path.read_text()) or {}
        cfg = _apply_overrides(cfg, overrides)
    return cfg


CFG = load_config()
