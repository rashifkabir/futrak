import sys
import cv2
import numpy as np
sys.path.append(".")

from backend.cv_engine.goal_detector  import GoalDetector
from backend.cv_engine.ball_detector  import BallDetector

VIDEO_PATH = "data/new_videos/f10s4.mp4"
OUTPUT_PATH = "data/new_videos/f10s4_debug.mp4"

# ─────────────────────────────────────────
# STEP 1 — Detect goal
# ─────────────────────────────────────────
print("Detecting goal...")
detector = GoalDetector()
goal     = detector.find_goal_in_video(VIDEO_PATH)

if not goal["detected"]:
    print(f"Goal not detected: {goal.get('reason')}")
    exit()

print(f"Goal type:   {goal['goal_type']}")
print(f"Post left:   {goal['post_left']}")
print(f"Post right:  {goal['post_right']}")
print(f"Crossbar y:  {goal['crossbar_y']}")
print(f"Ground y:    {goal['ground_y']}")
print(f"Goalkeeper:  {goal['goalkeeper']}")
print(f"Zones:")
for name, coords in goal["zones"].items():
    print(f"  {name}: {[round(c) for c in coords]}")

# ─────────────────────────────────────────
# STEP 2 — Track ball
# ─────────────────────────────────────────
print("\nTracking ball...")
ball_det        = BallDetector()
detections, fps = ball_det.track_shot_only(VIDEO_PATH)

ball_positions = [
    d for d in detections if d["ball"] is not None
]
print(f"Ball detected in {len(ball_positions)} frames")

# Print ball positions near goal area
goal_y1 = goal["crossbar_y"]
goal_y2 = goal["ground_y"]
goal_x1 = goal["post_left"]
goal_x2 = goal["post_right"]

print("\nBall positions near goal area:")
for d in ball_positions:
    b  = d["ball"]
    cy = b["cy"]
    cx = b["cx"]
    near = (
        goal_x1 - 50 <= cx <= goal_x2 + 50 and
        goal_y1 - 50 <= cy <= goal_y2 + 100
    )
    if near:
        inside = (goal_x1 <= cx <= goal_x2 and
                  goal_y1 <= cy <= goal_y2)
        print(f"  Frame {d['frame']:>4}: "
              f"({cx:>4},{cy:>4}) "
              f"{'IN GOAL ✓' if inside else 'near goal'} "
              f"[{b.get('method','?')}]")

# ─────────────────────────────────────────
# STEP 3 — Draw annotated video
# ─────────────────────────────────────────
print("\nDrawing debug video...")

cap     = cv2.VideoCapture(VIDEO_PATH)
fps_out = cap.get(cv2.CAP_PROP_FPS)
w       = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h       = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

out = cv2.VideoWriter(
    OUTPUT_PATH,
    cv2.VideoWriter_fourcc(*"mp4v"),
    fps_out,
    (w, h)
)

# Ball position lookup
ball_map = {
    d["frame"]: d["ball"]
    for d in detections
    if d["ball"] is not None
}

frame_num = 0
zone_colours = {
    "Top Left":   (0,   255, 0),
    "Top Centre": (0,   200, 0),
    "Top Right":  (0,   255, 0),
    "Mid Left":   (255, 165, 0),
    "Mid Centre": (0,   0,   255),
    "Mid Right":  (255, 165, 0),
    "Bot Left":   (255, 255, 0),
    "Bot Centre": (0,   0,   200),
    "Bot Right":  (255, 255, 0),
}

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # ── Draw goal zones ──────────────────────
    zones = goal.get("zones", {})
    for zone_name, (zx1, zy1, zx2, zy2) in zones.items():
        colour = zone_colours.get(zone_name, (255, 255, 255))
        cv2.rectangle(frame,
                      (int(zx1), int(zy1)),
                      (int(zx2), int(zy2)),
                      colour, 1)
        # Zone label
        label_x = int(zx1 + (zx2 - zx1) / 2 - 15)
        label_y = int(zy1 + (zy2 - zy1) / 2)
        cv2.putText(frame,
                    zone_name[:3],
                    (label_x, label_y),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.3, colour, 1)

    # ── Draw goal outline ────────────────────
    cv2.rectangle(frame,
                  (goal["post_left"],  goal["crossbar_y"]),
                  (goal["post_right"], goal["ground_y"]),
                  (0, 255, 0), 2)

    # ── Draw goalkeeper ──────────────────────
    gk = goal.get("goalkeeper", {})
    if gk.get("present") and gk.get("bbox"):
        gx1, gy1, gx2, gy2 = gk["bbox"]
        cv2.rectangle(frame,
                      (gx1, gy1), (gx2, gy2),
                      (255, 0, 0), 2)
        cv2.putText(frame, "GK",
                    (gx1, gy1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, (255, 0, 0), 1)

    # ── Draw ball ────────────────────────────
    if frame_num in ball_map:
        ball   = ball_map[frame_num]
        cx, cy = ball["cx"], ball["cy"]
        method = ball.get("method", "yolo")

        # Yellow = YOLO, Orange = optical flow
        col = (0, 255, 255) if method == "yolo" \
              else (0, 165, 255)

        cv2.circle(frame, (cx, cy), 8, col, 2)
        cv2.putText(frame,
                    f"f{frame_num}",
                    (cx + 10, cy),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.3, col, 1)

        # Red dot if ball is inside goal bbox
        in_goal = (
            goal_x1 <= cx <= goal_x2 and
            goal_y1 <= cy <= goal_y2
        )
        if in_goal:
            cv2.circle(frame, (cx, cy), 12,
                       (0, 0, 255), 3)

    # ── Frame counter ────────────────────────
    cv2.putText(frame, f"Frame: {frame_num}",
                (10, 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5, (255, 255, 255), 1)

    out.write(frame)
    frame_num += 1

cap.release()
out.release()

print(f"\nDebug video saved: {OUTPUT_PATH}")
print("Open it and look for:")
print("  Green box  = detected goal bbox")
print("  Blue box   = goalkeeper")
print("  Yellow dot = ball (YOLO)")
print("  Orange dot = ball (optical flow)")
print("  Red ring   = ball detected INSIDE goal bbox")
print("  Zone labels show TL/TC/TR etc")
print("\nIf green box is in wrong position — goal detection is the issue")
print("If no yellow dots near goal — ball tracking is the issue")
print("If no red rings — ball never detected inside goal bbox") 