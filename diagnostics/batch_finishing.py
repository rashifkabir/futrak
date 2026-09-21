"""Batch-test finishing across many clips. Prints a compact table
of model outcomes so you can compare against the true outcome
(which you note while watching each clip).
  python3 diagnostics/batch_finishing.py [goal_type] [clip1 clip2 ...]
  python3 diagnostics/batch_finishing.py large fin1 fin2 fin3
  python3 diagnostics/batch_finishing.py           # runs a default set
"""
import sys, io, contextlib
sys.path.insert(0, ".")
from backend.cv_engine.finishing_analyser import analyse_finishing

args = sys.argv[1:]
goal_type = "medium"
if args and args[0] in ("large", "medium", "small"):
    goal_type = args.pop(0)

if args:
    clips = [a if a.endswith(".mp4") else a + ".mp4" for a in args]
else:
    clips = ["f5save.mp4", "f8save.mp4", "f6s1miss.mp4",
             "f9s3miss.mp4", "fin1.mp4", "fin10.mp4", "fin50shot10.mp4"]

print(f"\n{'clip':22}{'outcome':12}{'conf':>6}{'zone':>16}{'score':>6}")
print("-" * 62)
for name in clips:
    path = f"data/new_videos/{name}"
    try:
        # suppress the verbose per-frame prints for a clean table
        with contextlib.redirect_stdout(io.StringIO()):
            r = analyse_finishing(path, goal_type=goal_type)
        oc = r.get("outcome", "?")
        conf = r.get("confidence", 0) or 0
        zone = r.get("zone") or "-"
        score = r.get("zone_score", 0) or 0
        reason = r.get("reason", "")
        line = f"{name:22}{oc:12}{conf:>6.2f}{str(zone):>16}{score:>6}"
        if oc in ("rejected", "unclear"):
            line += f"  | {reason[:40]}"
        print(line)
    except Exception as e:
        print(f"{name:22}ERROR: {str(e)[:40]}")
print()
