import os
os.environ["MEDIAPIPE_DISABLE_GPU"] = "1"

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as tasks_python
from mediapipe.tasks.python import vision

MODEL_PATH = "models/pose_landmarker.task"

# Skeleton connections — pairs of landmark indices to draw lines between
CONNECTIONS = [
    (11, 12), (11, 13), (13, 15),        # left arm
    (12, 14), (14, 16),                   # right arm
    (11, 23), (12, 24), (23, 24),         # torso
    (23, 25), (25, 27), (27, 29),         # left leg
    (24, 26), (26, 28), (28, 30),         # right leg
]

def _extract_core(video_path: str, draw_skeleton: bool = True):

    if not os.path.exists(MODEL_PATH):
        print(f"Model not found at {MODEL_PATH}")
        print("Run: curl -o models/pose_landmarker.task https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task")
        return None

    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        print(f"Error: could not open video at {video_path}")
        return None

    fps          = cap.get(cv2.CAP_PROP_FPS)
    width        = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height       = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    print(f"Video loaded: {width}x{height} at {fps}fps — {total_frames} frames")

    output_path = video_path.replace(".mp4", "_annotated.mp4")
    writer = cv2.VideoWriter(
        output_path,
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height)
    )

    # New Tasks API configuration
    base_options = tasks_python.BaseOptions(model_asset_path=MODEL_PATH)
    options = vision.PoseLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.VIDEO,
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5
    )

    all_frames = []

    with vision.PoseLandmarker.create_from_options(options) as landmarker:

        frame_num = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            rgb_frame  = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image   = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

            # Timestamp in milliseconds — required by VIDEO mode
            timestamp_ms = int((frame_num / fps) * 1000)
            result       = landmarker.detect_for_video(mp_image, timestamp_ms)

            frame_data = {"frame": frame_num, "landmarks": None}

            if result.pose_landmarks and len(result.pose_landmarks) > 0:
                raw = result.pose_landmarks[0]

                # Store all 33 landmarks
                landmarks = {}
                for idx, lm in enumerate(raw):
                    landmarks[idx] = {
                        "x":          lm.x,
                        "y":          lm.y,
                        "z":          lm.z,
                        "visibility": getattr(lm, "visibility", 1.0)
                    }

                frame_data["landmarks"] = landmarks

                # Draw skeleton overlay
                if draw_skeleton:
                    for idx, lm in enumerate(raw):
                        cx = int(lm.x * width)
                        cy = int(lm.y * height)
                        cv2.circle(frame, (cx, cy), 4, (0, 255, 0), -1)

                    for start_idx, end_idx in CONNECTIONS:
                        if start_idx in landmarks and end_idx in landmarks:
                            s = raw[start_idx]
                            e = raw[end_idx]
                            cv2.line(
                                frame,
                                (int(s.x * width), int(s.y * height)),
                                (int(e.x * width), int(e.y * height)),
                                (255, 255, 255), 2
                            )
            else:
                print(f"  Frame {frame_num}: no pose detected")

            all_frames.append(frame_data)
            writer.write(frame)
            frame_num += 1

    cap.release()
    writer.release()

    detected = sum(1 for f in all_frames if f["landmarks"] is not None)
    print(f"\nDone — pose detected in {detected}/{total_frames} frames")
    print(f"Annotated video saved: {output_path}")

    return all_frames


def extract_landmarks_from_video(video_path: str, draw_skeleton: bool = True):
    """Public entry. Runs pose extraction; retries ONCE only if
    detections are SUSPICIOUSLY near-zero (the intermittent
    MediaPipe init-glitch signature). Genuine brief presence
    (low but non-zero) is NOT retried — that's a real
    'player barely in frame' case for the validation gate to
    reject, not a glitch."""
    result = _extract_core(video_path, draw_skeleton)
    if result is None:
        return None
    total = len(result)
    detected = sum(1 for f in result if f["landmarks"] is not None)
    # near-zero on a real-length clip => suspected init glitch
    near_zero = total > 30 and detected <= max(2, int(total * 0.01))
    if near_zero:
        print(f"[pose] near-zero detections ({detected}/{total}) "
              f"— retrying once (suspected init glitch)")
        retry = _extract_core(video_path, draw_skeleton)
        if retry is not None:
            retry_detected = sum(1 for f in retry
                                 if f["landmarks"] is not None)
            if retry_detected > detected:
                print(f"[pose] retry rescued: {retry_detected}/{total}")
                return retry
            print("[pose] retry did not help — genuine failure")
    return result
