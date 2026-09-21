import os
import cv2
from dotenv import load_dotenv
from inference import get_model

load_dotenv(dotenv_path=".env")

API_KEY  = os.getenv("ROBOFLOW_API_KEY")
MODEL_ID = "propathfc-detection/4"

# Pick a test video frame
VIDEO = "data/test_videos/fin14shot2.mp4"  # change if needed

print("Loading custom model (first run downloads it)...")
model = get_model(model_id=MODEL_ID, api_key=API_KEY)
print("Model loaded\n")

# Grab a frame from the middle of the video
cap = cv2.VideoCapture(VIDEO)
total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
cap.set(cv2.CAP_PROP_POS_FRAMES, total // 3)
ret, frame = cap.read()
cap.release()

if not ret:
    print(f"Could not read frame from {VIDEO}")
    raise SystemExit

print(f"Running inference on frame from {VIDEO}...\n")
results = model.infer(frame)[0]

print(f"Detections: {len(results.predictions)}")
for p in results.predictions:
    print(f"  class={p.class_name:10s} "
          f"conf={p.confidence:.2f} "
          f"x={int(p.x)} y={int(p.y)} "
          f"w={int(p.width)} h={int(p.height)}")

if not results.predictions:
    print("  (nothing detected in this frame)")
