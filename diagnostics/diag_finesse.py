"""
Sanity-check diagnostic for finesse_technique.py. Prints raw measured
values and the score breakdown per clip so they can be eyeballed for
sensible good/average/bad separation before any bands get re-tuned.
"""
import sys
sys.path.append(".")
from backend.cv_engine.finesse_technique import (
    measure_finesse_form, score_finesse_technique)

CLIPS = [
    ("sh7finesse",    "data/new_videos/sh7finesse.mp4"),
    # fin51shot10 and sh1finesse EXCLUDED -- confirmed not filmed at
    # 90 deg side-on, so their geometry/timing features aren't
    # comparable to the rest of this set.
    ("average_finesse", "data/new_videos/average_finesse.mp4"),
    ("bad_finesse",   "data/new_videos/bad_finesse.mp4"),
    ("bad_finesse2",  "data/new_videos/bad_finesse2.mp4"),
    ("s1",            "data/new_videos/s1.mp4"),
]

MEASURED_FIELDS = [
    "hip_peak_at", "knee_peak_at", "foot_peak_at",
    "hip_to_knee_gap", "knee_to_foot_gap", "chain_order_ok",
    "peak_ank_speed", "contact_ank_speed", "decel_ratio",
    "body_open_ratio", "follow_through",
]
BREAKDOWN_FIELDS = [
    "decel", "body_open", "follow", "hip_timing", "knee_timing",
    "foot_timing", "hip_knee_gap_score", "knee_foot_gap_score",
    "order_veto",
]

for label, path in CLIPS:
    print(f"\n{'=' * 55}\n{label}\n{'=' * 55}")
    m = measure_finesse_form(path)
    if m is None:
        print("  measure_finesse_form returned None (no contact / no pose)")
        continue
    print("  -- measured --")
    for f in MEASURED_FIELDS:
        v = m.get(f)
        print(f"  {f:<20} {v:.4f}" if isinstance(v, float) else f"  {f:<20} {v}")
    score, breakdown = score_finesse_technique(m)
    print(f"  -- score: {score}/100 --")
    for f in BREAKDOWN_FIELDS:
        v = breakdown.get(f)
        print(f"  {f:<20} {v:.4f}" if isinstance(v, float) else f"  {f:<20} {v}")
