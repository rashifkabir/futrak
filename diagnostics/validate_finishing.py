"""
Validate finishing on purpose-filmed test clips.
Filenames encode size + true outcome: test_<size>_<outcome>.mp4
  size: 11 | 7 | 5   outcome: goal | goalbounce | miss | save | post
Place clips in data/test_clips/ (or pass a folder).
  python3 diagnostics/validate_finishing.py [folder]
'save' clips are run with has_keeper=True; others has_keeper=False.
"""
import sys, os, io, contextlib
sys.path.insert(0, ".")
from backend.cv_engine.finishing_analyser import analyse_finishing

folder = sys.argv[1] if len(sys.argv) > 1 else "data/test_clips"
SIZE_MAP = {"11": "large", "7": "medium", "5": "small"}
# how the model's outcome maps to our truth labels
def matches(truth, outcome):
    if truth in ("goal", "goalbounce"): return outcome == "goal"
    if truth == "miss":  return outcome == "miss"
    if truth == "save":  return outcome == "save"
    if truth == "post":  return outcome == "woodwork"
    return False

if not os.path.isdir(folder):
    print(f"Folder not found: {folder}"); sys.exit(1)

clips = sorted(f for f in os.listdir(folder)
               if f.startswith("test_") and f.endswith(".mp4")
               and "annotated" not in f)
if not clips:
    print(f"No test_*.mp4 clips in {folder}"); sys.exit(0)

print(f"\n{'clip':28}{'size':7}{'truth':12}{'model':12}{'conf':>5}  result")
print("-"*78)
correct = total = 0
for name in clips:
    parts = name[:-4].split("_")   # test, size, outcome
    if len(parts) < 3: continue
    size, truth = parts[1], parts[2]
    gt = SIZE_MAP.get(size, "medium")
    keeper = (truth == "save")
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            r = analyse_finishing(f"{folder}/{name}", goal_type=gt, has_keeper=keeper)
        oc = r.get("outcome","?"); conf = r.get("confidence",0) or 0
        ok = matches(truth, oc)
        total += 1; correct += ok
        flag = "✓" if ok else ("~ unclear" if oc=="unclear" else
                                "~ rejected" if oc=="rejected" else "✗ WRONG")
        print(f"{name:28}{size+'-a':7}{truth:12}{oc:12}{conf:>5.2f}  {flag}")
    except Exception as e:
        print(f"{name:28}{size:7}{truth:12}ERROR {str(e)[:24]}")
print(f"\nAccuracy: {correct}/{total} correct"
      + (f"  ({correct/total*100:.0f}%)" if total else ""))
