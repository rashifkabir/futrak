"""Test technique coaching: pass video + USER-STATED shot type.
  python3 diagnostics/test_coach.py data/new_videos/sh1finesse.mp4 finesse
Types: laces knuckleball inside_curl finesse trivela chip
"""
import sys
sys.path.insert(0, ".")
from backend.cv_engine.technique_coach import coach_technique, SHOT_TYPES

if len(sys.argv) < 3:
    print(f"usage: python3 diagnostics/test_coach.py CLIP.mp4 SHOT_TYPE")
    print(f"types: {', '.join(SHOT_TYPES)}")
    sys.exit(1)

video, stype = sys.argv[1], sys.argv[2]
r = coach_technique(video, stype)
print("\n" + "="*60)
if "error" in r:
    print("ERROR:", r["error"]); sys.exit(0)
print(f"STATED SHOT TYPE: {r['shot_label']}")
print(f"OVERALL SCORE: {r['overall_score']}/10")
print("="*60)
print("SCORES (0-10, vs ideal for THIS type):")
for k, v in r["scores"].items():
    print(f"  {k:<16} {v}")
print("\nMEASURED:")
for k, v in r["measured"].items():
    print(f"  {k:<22} {v}")
print(f"\nCOACHING FOCUS: {r['coaching_focus']}")
if r["coaching_notes"]:
    print("\nCOACHING POINTS:")
    for dim, issue, advice in r["coaching_notes"]:
        print(f"  [{dim}] {advice}")
else:
    print("\nCOACHING POINTS: execution looks on-target for this type.")
print("\nNOT MEASURED (honest limits):")
for u in r["not_measured"]:
    print(f"  - {u}")
