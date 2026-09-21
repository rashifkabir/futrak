"""
Sanity-check diagnostic for the two feature groups added to
laces_technique.py: the stability window (head/trunk/pelvis/
support-knee/plant-foot jitter) and plant-foot/support-leg
geometry at contact. Prints raw values per clip so they can be
eyeballed for sensible good/average/bad separation before any
scoring bands are wired in.
"""
import sys
sys.path.append(".")
from backend.cv_engine.laces_technique import measure_laces_form

CLIPS = [
    ("good_laces",      "data/new_videos/good_laces.mp4"),
    ("average_laces",   "data/new_videos/average_laces.mp4"),
    ("bad_laces",       "data/new_videos/bad_laces.mp4"),
    ("sh2instep_laces", "data/new_videos/sh2instep_laces.mp4"),
    ("sh6laces",        "data/new_videos/sh6laces.mp4"),
]

FIELDS = [
    "stab_window_frames", "head_jit", "trunk_sway", "pelvis_jit",
    "support_knee_jit", "plant_foot_jit",
    "plant_ball_dist", "plant_lateral_offset", "support_knee_flexion",
]

for label, path in CLIPS:
    print(f"\n{'=' * 55}\n{label}\n{'=' * 55}")
    m = measure_laces_form(path)
    if m is None:
        print("  measure_laces_form returned None (no contact / no pose)")
        continue
    for f in FIELDS:
        v = m.get(f)
        if isinstance(v, float):
            print(f"  {f:<22} {v:.4f}")
        else:
            print(f"  {f:<22} {v}")
