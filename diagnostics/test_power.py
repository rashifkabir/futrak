"""Test shot power on one or more clips.
  python3 diagnostics/test_power.py CLIP.mp4 [CLIP2.mp4 ...]
  python3 diagnostics/test_power.py            (runs default set)
Shows: contact frame, power grade /100, range, angle confidence,
approx km/h, and the user-facing filming note.
"""
import sys
sys.path.insert(0, ".")
from backend.cv_engine.ball_detector import BallDetector
from backend.cv_engine.contact_detector import (
    find_contact_frame_index, filter_foot_glued_optical_flow,
)
from backend.cv_engine.pose_extractor import extract_landmarks_from_video
import cv2

DEFAULT_CLIPS = [
    "data/new_videos/sh6laces.mp4",
    "data/test_videos/fin14shot2.mp4",
    "data/new_videos/sh1finesse.mp4",
    "data/new_videos/sh5trivela.mp4",
]

clips = sys.argv[1:] if len(sys.argv) > 1 else DEFAULT_CLIPS

for video in clips:
    print("\n" + "=" * 56)
    print(video.split("/")[-1])
    print("=" * 56)
    try:
        det = BallDetector()
        dets, fps = det.track_shot_only(video)
        frames = extract_landmarks_from_video(video, draw_skeleton=False)
        valid = [f for f in frames if f["landmarks"] is not None]
        cap = cv2.VideoCapture(video)
        W = int(cap.get(3)); H = int(cap.get(4)); cap.release()
        dets = filter_foot_glued_optical_flow(valid, dets, W, H)
        res = find_contact_frame_index(valid, dets, video)
        if res is None or isinstance(res, dict):
            print("  Could not find contact:", res)
            continue
        contact = valid[res[0]]["frame"]
        p = det.estimate_power_score(dets, fps, contact_frame=contact)
        if p["power_grade"] is None:
            print("  Power unavailable (ball tracking too sparse).")
            continue
        lo, hi = p["power_range"]
        print(f"  Contact frame:     {contact}")
        print(f"  POWER GRADE:       {p['power_grade']}/100  "
              f"(range {lo}-{hi})")
        print(f"  Angle confidence:  {p['angle_confidence']}")
        print(f"  Approx speed:      ~{p['speed_kmh']} km/h "
              f"({p['speed_kmh_note']})")
        print(f"  Note: {p['power_note']}")
    except Exception as e:
        print(f"  ERROR: {e}")
