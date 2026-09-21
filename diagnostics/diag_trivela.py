"""
Sanity-check diagnostic for trivela_technique.py. Prints raw measured
values and the score breakdown per clip so they can be eyeballed for
sensible good/average/bad separation before any bands get re-tuned.
"""
import sys
sys.path.append(".")
from backend.cv_engine.trivela_technique import (
    measure_trivela_form, score_trivela_technique)

CLIPS = [
    # sh5trivela, sh8trivela, s6, bad_trivela3 EXCLUDED -- confirmed
    # wrong camera angle (not the planting-foot-side convention this
    # scorer assumes). Only these three in data/new_videos are
    # correctly filmed for trivela.
    ("average_trivela", "data/new_videos/average_trivela.mp4"),
    ("bad_trivela",    "data/new_videos/bad_trivela.mp4"),
    ("bad_trivela2",   "data/new_videos/bad_trivela2.mp4"),
]

MEASURED_FIELDS = [
    "hip_peak_at", "foot_peak_at", "hip_to_knee_gap", "knee_to_foot_gap",
    "chain_order_ok", "hip_range_deg", "peak_ank_speed_norm",
    "dissociation_ratio", "crossed_midline", "cross_body_shift_norm",
    "pelvis_jit",
]
BREAKDOWN_FIELDS = [
    "dissociation", "cross_body", "hip_knee_gap_score", "knee_foot_gap_score",
    "balance", "hip_timing", "foot_timing", "order_veto", "cross_veto",
]

for label, path in CLIPS:
    print(f"\n{'=' * 55}\n{label}\n{'=' * 55}")
    m = measure_trivela_form(path)
    if m is None:
        print("  measure_trivela_form returned None (no contact / no pose)")
        continue
    print("  -- measured --")
    for f in MEASURED_FIELDS:
        v = m.get(f)
        print(f"  {f:<22} {v:.4f}" if isinstance(v, float) else f"  {f:<22} {v}")
    score, breakdown = score_trivela_technique(m)
    print(f"  -- score: {score}/100 --")
    for f in BREAKDOWN_FIELDS:
        v = breakdown.get(f)
        print(f"  {f:<22} {v:.4f}" if isinstance(v, float) else f"  {f:<22} {v}")
