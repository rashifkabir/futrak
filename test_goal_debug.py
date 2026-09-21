import sys
sys.path.append(".")
import cv2
import numpy as np

# Pass a clip path as the first argument; test footage is not committed.
VIDEO_PATH = sys.argv[1] if len(sys.argv) > 1 else "data/test_videos/goal_clip.mp4"

cap = cv2.VideoCapture(VIDEO_PATH)
total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
print(f"Total frames: {total}")

# Sample frame from middle of video where goal is visible
cap.set(cv2.CAP_PROP_POS_FRAMES, total // 3)
ret, frame = cap.read()
cap.release()

if not ret:
    print("Could not read frame")
    exit()

h, w = frame.shape[:2]
print(f"Frame size: {w}x{h}")

# White mask
hsv   = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
mask1 = cv2.inRange(hsv,
    np.array([0,   0, 180]),
    np.array([180, 50, 255]))
mask2 = cv2.inRange(hsv,
    np.array([0,   0, 160]),
    np.array([180, 40, 255]))
white_mask = cv2.bitwise_or(mask1, mask2)

# Find all contours
contours, _ = cv2.findContours(
    white_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
)

print(f"\nFound {len(contours)} white contours:")
print(f"{'Area':>10} {'x':>6} {'y':>6} {'w':>6} {'h':>6} {'ratio':>7}")
print("-" * 50)

# Sort by area descending
sorted_cnts = sorted(
    contours, key=cv2.contourArea, reverse=True
)[:15]

for cnt in sorted_cnts:
    area = cv2.contourArea(cnt)
    x, y, cw, ch = cv2.boundingRect(cnt)
    ratio = round(cw / ch, 2) if ch > 0 else 0
    min_area = w * h * 0.001
    flag = " ← potential goal" if (
        area > min_area and 1.5 < ratio < 5.0
    ) else ""
    print(f"{area:>10.0f} {x:>6} {y:>6} {cw:>6} {ch:>6} "
          f"{ratio:>7}{flag}")