"""Full combined shooting analysis: technique + power -> score.
  python3 diagnostics/test_shooting.py CLIP.mp4 SHOT_TYPE
Types: laces knuckleball inside_curl finesse trivela chip toepoke
"""
import sys
sys.path.insert(0, ".")
from backend.cv_engine.shooting_score import analyse_shot
from backend.cv_engine.coaching_llm import build_coaching

if len(sys.argv) < 3:
    print("usage: python3 diagnostics/test_shooting.py CLIP.mp4 TYPE")
    sys.exit(1)

video, stype = sys.argv[1], sys.argv[2]
r = analyse_shot(video, stype)

print("\n" + "=" * 56)
if "error" in r:
    print("ERROR:", r["error"]); sys.exit(0)

print(f"SHOOTING REPORT — {r['shot_type']}")
print("=" * 56)
print(f"  ⚽ SHOOTING SCORE:  {r['shooting_score']}/100   ({r['basis']})")
print(f"     Technique:  {r['components']['technique']}/100  (60%)")
pw = r['components']['power']
print(f"     Power:      {pw}/100  (40%)" if pw is not None
      else "     Power:      not measured")
if r.get("power_confidence"):
    print(f"     Power confidence: {r['power_confidence']}  "
          f"range {r.get('power_range')}")
if r.get("speed_kmh_approx"):
    print(f"     (~{r['speed_kmh_approx']} km/h approx)")
if r.get("fallback_note"):
    print(f"  NOTE: {r['fallback_note']}")
if r.get("power_note"):
    print(f"  Filming: {r['power_note']}")

# natural-language coaching from the technique side
coach_input = {
    "shot_label": r["shot_type"],
    "overall_score": (r["components"]["technique"] or 0) / 10,
    "coaching_focus": r.get("coaching_focus", ""),
    "scores": r.get("technique_scores", {}),
    "coaching_notes": r.get("coaching_notes", []),
    "not_measured": r.get("not_measured", []),
}
coaching = build_coaching(coach_input, use_api=True)
print("\n  COACHING:")
print("   ", coaching["text"])
