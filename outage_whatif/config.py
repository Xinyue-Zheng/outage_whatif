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
    # [POLICY] settlements below this population get no individual claims
    P_min: int = 50
    # [POLICY] severe-hole population line: a hole is severe iff pop >= P0
    P0: int = 200
    # [POLICY] major-exit share: a neighbor is a genuine exit for a subregion
    # iff it is best alternative for >= sigma of that subregion's footprint cells
    sigma: float = 0.20
    # [POLICY] 15-minute tier: refute iff fraction of bins >= pi_hi exceeds this
    cap15_refute_frac: float = 0.10
    # [POLICY] calibration: max false-pass rate allowed for the hourly
    # support-zone edge
    calib_false_pass_max: float = 0.05


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
    background_grid_m: float = 3000.0     # Track-2 fuse grid pitch
    background_pts_per_tile: int = 2      # random points per background tile
    r0_factor: float = 0.75               # R0 = r0_factor * median dist to 6 NN
    n_neighbors_for_r0: int = 6
    static_area_km: float = 0.0           # >0: fixed start area = the full
                                          # data square (side in km, exact
                                          # square containment) instead of the
                                          # neighbor-derived R0; no integrity
                                          # ring/claims, no expansion
    n_sectors: int = 8                    # integrity boundary direction segments
    ring_width_factor: float = 0.25       # integrity ring: [R, R*(1+factor)]
    boundary_expand_factor: float = 1.30  # sector radius multiplier on expansion
    density_min_pop: float = 1.0          # raster density filter (pop per pixel)
    min_settlement_pixels: int = 3        # smaller fragments merge into background

    # ---------------- sampling ----------------
    min_points_per_settlement: int = 4
    densify_cells_per_round: int = 12     # unsampled evidence cells per densification
    integrity_min_cells: int = 3          # sampled ring cells needed to support

    # ---------------- claims / lifecycle ----------------
    split_after_densifications: int = 2   # coverage split trigger
    drilldown_after_rounds: int = 2       # capacity drill-down trigger
    cluster_sep_cells: float = 1.5        # pass/fail centroid separation (in
                                          # evidence-cell units) counted as clustered

    # ---------------- agents ----------------
    grade_weights: dict = field(default_factory=lambda: {
        "high": 0.75, "mid": 0.45, "low": 0.15})
    escalation_mode: str = "worst_case"   # worst_case | weighted (weighted: later)
    fuse_consecutive_misses: int = 2      # per-agent fuse threshold
    agent_retries: int = 1                # one retry, then fallback
    runners_up: int = 2                   # Agent 2 sees leader + this many

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
