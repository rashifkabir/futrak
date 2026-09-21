"""
Shared rotation decision for ProPath FC.

Real phone uploads often carry rotation metadata that OpenCV
delivers inconsistently — sometimes the frame MediaPipe sees is
sideways, so NO person is detected. This helper decides, ONCE per
video, which rotation makes a person detectable, so pose AND ball
detection apply the SAME rotation and stay coordinate-aligned.

Conservative: only recommends a non-zero rotation if the as-is
frames FAIL to detect a person but a rotated version SUCCEEDS.
Clips that already work are left untouched (returns 0).
"""
import os
os.environ["MEDIAPIPE_DISABLE_GPU"] = "1"
import cv2
import mediapipe as mp
from mediapipe.tasks import python as tasks_python
from mediapipe.tasks.python import vision

MODEL_PATH = "models/pose_landmarker.task"

_ROT_CODE = {
    90:  cv2.ROTATE_90_CLOCKWISE,
    180: cv2.ROTATE_180,
    270: cv2.ROTATE_90_COUNTERCLOCKWISE,
}


def apply_rotation(frame, rotation):
    """Rotate a frame upright by the given degrees (0/90/180/270)."""
    if rotation in _ROT_CODE:
        return cv2.rotate(frame, _ROT_CODE[rotation])
    return frame


def _make_landmarker():
    base_options = tasks_python.BaseOptions(model_asset_path=MODEL_PATH)
    options = vision.PoseLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.IMAGE,   # static frames
        num_poses=1,
        min_pose_detection_confidence=0.3,
    )
    return vision.PoseLandmarker.create_from_options(options)


def determine_rotation(video_path, sample_count=6):
    """
    Returns the rotation (0/90/180/270) that makes a person
    detectable. Tries as-is (0) first; only if that fails does it
    test rotations. Returns 0 if as-is works OR nothing works.
    """
    if not os.path.exists(MODEL_PATH):
        return 0
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return 0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total <= 0:
        cap.release()
        return 0

    idxs = [int(total * f) for f in
            (0.2, 0.35, 0.5, 0.65, 0.8, 0.95)][:sample_count]
    frames = []
    for i in idxs:
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ret, fr = cap.read()
        if ret:
            frames.append(fr)
    cap.release()
    if not frames:
        return 0

    def hit_rate(rotation):
        hits = 0
        with _make_landmarker() as lm:
            for fr in frames:
                img = apply_rotation(fr, rotation)
                rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                res = lm.detect(mp_img)
                if res.pose_landmarks and len(res.pose_landmarks) > 0:
                    hits += 1
        return hits / len(frames)

    as_is = hit_rate(0)
    if as_is >= 0.5:
        return 0

    best_rot, best_rate = 0, as_is
    for rot in (90, 270, 180):
        r = hit_rate(rot)
        if r > best_rate:
            best_rot, best_rate = rot, r

    if best_rot != 0 and best_rate >= 0.5:
        print(f"[rotation] as-is {as_is:.0%} — rotating {best_rot}° "
              f"rescues to {best_rate:.0%}")
        return best_rot
    return 0
