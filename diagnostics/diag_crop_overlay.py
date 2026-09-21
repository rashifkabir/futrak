"""
Crop-method pose demo on a wide/landscape clip (player smaller in frame).

Answers: does pose tracking survive the wider framing, and does the two-pass
CROP method (locate player -> crop+upscale -> re-run pose) recover accuracy
over plain full-frame pose? Writes two skeleton overlays so it can be eyeballed,
and prints detection-rate + mean-visibility stats for the mechanics-critical
lower-body joints (hips/knees/ankles = 23-28).

This is a standalone diagnostic -- it does NOT touch the scoring pipeline, and
it doesn't need a ball (pose is independent of ball contact).

    python diagnostics/diag_crop_overlay.py data/test_videos/landscape_test.mp4
"""
import os
os.environ["MEDIAPIPE_DISABLE_GPU"] = "1"
import sys
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as tasks_python
from mediapipe.tasks.python import vision
from ultralytics import YOLO

MODEL_PATH = "models/pose_landmarker.task"
# reuse the exact skeleton wiring from pose_extractor.py
CONNECTIONS = [
    (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),
    (11, 23), (12, 24), (23, 24),
    (23, 25), (25, 27), (27, 29), (24, 26), (26, 28), (28, 30),
]
LOWER_BODY = [23, 24, 25, 26, 27, 28]  # hips/knees/ankles -- what mechanics needs
VIS_MIN = 0.5


def make_landmarker():
    opts = vision.PoseLandmarkerOptions(
        base_options=tasks_python.BaseOptions(model_asset_path=MODEL_PATH),
        running_mode=vision.RunningMode.VIDEO,
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    return vision.PoseLandmarker.create_from_options(opts)


def draw(frame, lms, W, H, color):
    """lms: list of 33 landmarks in FULL-FRAME normalised coords (or None)."""
    if lms is None:
        return
    for lm in lms:
        cv2.circle(frame, (int(lm[0] * W), int(lm[1] * H)), 4, color, -1)
    for a, b in CONNECTIONS:
        if a < len(lms) and b < len(lms):
            cv2.line(frame, (int(lms[a][0] * W), int(lms[a][1] * H)),
                     (int(lms[b][0] * W), int(lms[b][1] * H)), (255, 255, 255), 2)


def vis_stats(per_frame_lms):
    """detection rate + mean visibility of the lower-body joints."""
    detected = [l for l in per_frame_lms if l is not None]
    rate = len(detected) / max(1, len(per_frame_lms))
    vis = []
    for l in detected:
        for i in LOWER_BODY:
            if i < len(l):
                vis.append(l[i][2])  # visibility
    return rate, (float(np.mean(vis)) if vis else 0.0)


def read_frames(path):
    cap = cv2.VideoCapture(path)
    frames = []
    while True:
        ret, f = cap.read()
        if not ret:
            break
        frames.append(f)
    cap.release()
    return frames


def pass_fullframe(frames, fps):
    """Full-frame pose. Returns per-frame landmark lists (full-frame norm coords)."""
    out = []
    with make_landmarker() as lm:
        for i, f in enumerate(frames):
            rgb = cv2.cvtColor(f, cv2.COLOR_BGR2RGB)
            img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            res = lm.detect_for_video(img, int(i * 1000 / fps))
            if res.pose_landmarks:
                out.append([(p.x, p.y, getattr(p, "visibility", 1.0))
                            for p in res.pose_landmarks[0]])
            else:
                out.append(None)
    return out


def localize_yolo(frames):
    """Coarse per-frame player bbox via YOLO person detection -- the robust
    'coarse detect' first pass. Independent of pose, so it still finds the
    player on frames where full-frame pose (a finer, more fragile detector)
    gives up on a small/edge/low-contrast player. Returns pixel [x0,y0,x1,y1]
    per frame or None."""
    model = YOLO("yolov8n.pt")
    boxes = []
    for f in frames:
        res = model(f, verbose=False)[0]
        best, best_area = None, 0
        for b in res.boxes:
            if int(b.cls[0]) != 0:      # class 0 = person
                continue
            if float(b.conf[0]) < 0.3:
                continue
            x0, y0, x1, y1 = [float(v) for v in b.xyxy[0].tolist()]
            area = (x1 - x0) * (y1 - y0)
            if area > best_area:        # the shooter = the largest person
                best_area, best = area, [x0, y0, x1, y1]
        boxes.append(best)
    return boxes


def build_boxes(raw_boxes, W, H, pad=0.30, alpha=0.4):
    """Pad + EMA-smooth + previous-box fallback + clamp the coarse YOLO boxes
    into the 'stabilised crop window' the spec describes."""
    boxes = []
    prev = None
    for rb in raw_boxes:
        box = None
        if rb is not None:
            x0, y0, x1, y1 = rb
            bw, bh = x1 - x0, y1 - y0
            box = [x0 - bw * pad, y0 - bh * pad, x1 + bw * pad, y1 + bh * pad]
        if box is None:
            box = prev
        elif prev is not None:
            box = [alpha * b + (1 - alpha) * p for b, p in zip(box, prev)]
        if box is not None:
            prev = box
            boxes.append([max(0, box[0]), max(0, box[1]), min(W, box[2]), min(H, box[3])])
        else:
            boxes.append(None)
    return boxes


def pass_cropped(frames, boxes, fps, target=720):
    """Crop each frame to its box, upscale, re-run pose, map landmarks back to
    full-frame coords."""
    out = []
    with make_landmarker() as lm:
        for i, f in enumerate(frames):
            box = boxes[i]
            if box is None:
                out.append(None)
                continue
            x0, y0, x1, y1 = [int(v) for v in box]
            if x1 - x0 < 10 or y1 - y0 < 10:
                out.append(None)
                continue
            crop = f[y0:y1, x0:x1]
            ch, cw = crop.shape[:2]
            scale = target / max(ch, cw)
            crop_up = cv2.resize(crop, (int(cw * scale), int(ch * scale)),
                                 interpolation=cv2.INTER_CUBIC)
            rgb = cv2.cvtColor(crop_up, cv2.COLOR_BGR2RGB)
            img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            res = lm.detect_for_video(img, int(i * 1000 / fps))
            if res.pose_landmarks:
                mapped = []
                for p in res.pose_landmarks[0]:
                    fx = (x0 + p.x * (x1 - x0)) / frames[0].shape[1]
                    fy = (y0 + p.y * (y1 - y0)) / frames[0].shape[0]
                    mapped.append((fx, fy, getattr(p, "visibility", 1.0)))
                out.append(mapped)
            else:
                out.append(None)
    return out


def write_overlay(frames, per_frame_lms, path, W, H, fps, color, boxes=None):
    vw = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (W, H))
    for i, f in enumerate(frames):
        canvas = f.copy()
        if boxes is not None and boxes[i] is not None:
            x0, y0, x1, y1 = [int(v) for v in boxes[i]]
            cv2.rectangle(canvas, (x0, y0), (x1, y1), (0, 180, 255), 2)
        draw(canvas, per_frame_lms[i], W, H, color)
        vw.write(canvas)
    vw.release()


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "data/test_videos/landscape_test.mp4"
    base = os.path.splitext(path)[0]
    frames = read_frames(path)
    if not frames:
        print("could not read frames"); return
    H, W = frames[0].shape[:2]
    fps = 30  # container playback rate; only used for monotonic timestamps here
    print(f"{len(frames)} frames @ {W}x{H}")

    print("pass 0: YOLO player localization...")
    raw_boxes = localize_yolo(frames)
    boxes = build_boxes(raw_boxes, W, H)
    print("pass 1: full-frame pose (pipeline default 0.5 threshold)...")
    full = pass_fullframe(frames, fps)
    print("pass 2: cropped pose (YOLO-localized crop + upscale)...")
    crop = pass_cropped(frames, boxes, fps)

    r_full, v_full = vis_stats(full)
    r_crop, v_crop = vis_stats(crop)
    # median crop size (how much zoom the crop buys)
    sizes = [(b[2] - b[0]) / W for b in boxes if b is not None]
    med_boxw = float(np.median(sizes)) if sizes else 0.0

    print("\n================ RESULT ================")
    print(f"player crop width ~ {med_boxw*100:.0f}% of frame width "
          f"(smaller = more zoom the crop recovers)")
    print(f"{'':20}{'full-frame':>12}{'cropped':>12}")
    print(f"{'detection rate':20}{r_full*100:>11.1f}%{r_crop*100:>11.1f}%")
    print(f"{'lower-body visibility':20}{v_full:>12.3f}{v_crop:>12.3f}")

    print("\nwriting overlays...")
    write_overlay(frames, full, f"{base}_fullframe.mp4", W, H, fps, (0, 255, 0))
    write_overlay(frames, crop, f"{base}_cropped.mp4", W, H, fps, (0, 255, 0), boxes=boxes)

    # sample PNGs at 25/50/75% for quick visual check
    for pct in (0.25, 0.50, 0.75):
        idx = int(len(frames) * pct)
        for tag, lms, bx in (("full", full, None), ("crop", crop, boxes)):
            canvas = frames[idx].copy()
            if bx is not None and bx[idx] is not None:
                x0, y0, x1, y1 = [int(v) for v in bx[idx]]
                cv2.rectangle(canvas, (x0, y0), (x1, y1), (0, 180, 255), 2)
            draw(canvas, lms[idx], W, H, (0, 255, 0))
            cv2.imwrite(f"{base}_{tag}_f{idx}.png", canvas)
    print(f"done: {base}_fullframe.mp4 / _cropped.mp4 + sample PNGs")


if __name__ == "__main__":
    main()
