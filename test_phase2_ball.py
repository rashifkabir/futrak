import sys
sys.path.append(".")

from backend.cv_engine.ball_detector import BallDetector

# Pass a clip path as the first argument; test footage is not committed.
VIDEO_PATH = sys.argv[1] if len(sys.argv) > 1 else "data/test_videos/shot_clip.mp4"

print("=" * 45)
print("PHASE 2 — POWER ESTIMATION TEST")
print("=" * 45 + "\n")

detector  = BallDetector()
detections, fps = detector.track_shot_only(VIDEO_PATH)

result = detector.estimate_power_score(detections, fps)

print("\n--- Results ---")
if result["speed_kmh"]:
    print(f"Estimated speed:  {result['speed_kmh']} km/h")
    print(f"Power grade:      {result['power_grade']}/100")
else:
    print("Could not estimate power — try a cleaner video angle")