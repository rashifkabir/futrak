"""Full coaching chain: analyse + natural-language advice.
  python3 diagnostics/test_full_coach.py CLIP.mp4 SHOT_TYPE
"""
import sys
sys.path.insert(0, ".")
from backend.cv_engine.technique_coach import coach_technique
from backend.cv_engine.coaching_llm import build_coaching

video, stype = sys.argv[1], sys.argv[2]
r = coach_technique(video, stype)
coaching = build_coaching(r, use_api=True)
print("\n" + "="*60)
if "error" in r:
    print("ERROR:", r["error"]); sys.exit(0)
print(f"{r['shot_label']}  —  {r['overall_score']}/10")
print("="*60)
print("SCORES:", {k: v for k, v in r["scores"].items() if v is not None})
print(f"\nPrimary fix: {coaching['primary_fix']}  |  Strength: {coaching['strength']}")
print("\nCOACHING:")
print(" ", coaching["text"])
