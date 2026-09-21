"""
Test the finishing analyser on one or more clips.

Usage:
  python3 diagnostics/test_finishing.py                       # runs CLIPS list
  python3 diagnostics/test_finishing.py CLIP.mp4              # single (large)
  python3 diagnostics/test_finishing.py CLIP.mp4 medium       # single, 9/7-a-side
  python3 diagnostics/test_finishing.py CLIP.mp4 small        # single, 5-a-side

goal_type: 'large' (11-a-side), 'medium' (9/7-a-side),
'small' (5-a-side). Defaults to 'large'.
"""
import sys
sys.path.insert(0, ".")
from backend.cv_engine.finishing_analyser import analyse_finishing

# ── EDIT: (label_with_KNOWN_outcome, video_path, goal_type) ──
CLIPS = [
    #("f10s4 (KNOWN: goal)",             "data/new_videos/f10s4.mp4",        "large"),
    #("f5save (KNOWN: save/miss)","data/new_videos/f5save.mp4",       "large"),
    #("f6s1miss (KNOWN: miss)", "data/new_videos/f6s1miss.mp4", "large"),
    #("f12 (KNOWN: goal)",     "data/new_videos/f12.mp4",  "large"),
    #("f9s3miss (KNOWN: rejected)", "data/new_videos/f9s3miss.mp4", "large"),
    #("f8save (KNOWN: save)", "data/new_videos/f8save.mp4", "large"),
    ("f2 (KNOWN: woodwork then in)", "data/new_videos/f2.mp4", "large"),
    ("f1 (KNOWN: save)", "data/new_videos/f1.mp4", "large"),
]


def run(label, video, goal_type="large"):
    print(f"\n{'='*55}\n{label}  [goal_type={goal_type}]\n{video}\n{'='*55}")
    try:
        result = analyse_finishing(video, goal_type=goal_type)
        print("RESULT:")
        for k, v in result.items():
            print(f"  {k}: {v}")
        oc = result.get("outcome", "?")
        if result.get("zone"):
            print(f"  >>> {oc.upper()} in {result['zone']} "
                  f"(score {result['zone_score']})")
        else:
            print(f"  >>> {oc.upper()}"
                  + (f" — {result['reason']}" if result.get("reason") else ""))
    except Exception as e:
        print(f"  ERROR: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        path = sys.argv[1]
        gtype = sys.argv[2] if len(sys.argv) > 2 else "large"
        run(f"clip: {path}", path, gtype)
    else:
        for clip in CLIPS:
            if len(clip) == 3:
                label, video, gtype = clip
            else:
                label, video = clip
                gtype = "large"
            run(label, video, gtype)
        print(f"\n{'='*55}")
        print("VALIDATION: known miss->'miss', save->'save',")
        print("woodwork->'woodwork', moving camera->'rejected'.")
        print("If a non-goal reads 'goal', tune on that clip.")
        print('='*55)
