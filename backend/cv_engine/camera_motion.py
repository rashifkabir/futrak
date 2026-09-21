"""
Camera-motion detection for ProPath FC shooting analysis.

Shooting clips need a STATIC camera. This measures BACKGROUND
motion via optical flow on feature points OUTSIDE the central
player/ball region (which move legitimately). Calibrated to real
clips: clean static-handheld footage reads low mean motion;
panning or shaky footage reads high.

Strict mode: flags BOTH smooth pans and erratic shake (requires a
properly still camera), while tolerating the tiny unavoidable
tremor of a handheld phone.
"""
import cv2
import numpy as np

# Calibrated thresholds (mean background motion px/frame):
#   clean static handheld: sh6laces 0.22, sh1finesse ~0.09
#   moving (reject): fin14shot2 pan 0.55, fin47shot9 shake 0.58
MOTION_MEAN_LIMIT = 0.35   # above this = camera moving too much
MOTION_STD_LIMIT  = 0.35   # erratic-shake catch (secondary)


def measure_camera_motion(video_path, window=(0.1, 0.7), n=20):
    """Return dict with mean/max/std background motion + verdict."""
    cap = cv2.VideoCapture(video_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    W = int(cap.get(3)); H = int(cap.get(4))
    if total < 10:
        cap.release()
        return {"ok": True, "mean": 0.0, "reason": None}  # too short to judge

    lo, hi = int(total*window[0]), int(total*window[1])
    step = max(1, (hi - lo) // n)
    cx0, cx1 = int(W*0.25), int(W*0.75)
    cy0, cy1 = int(H*0.20), int(H*0.85)

    vecs = []
    prev_gray = None; prev_i = None
    for i in range(lo, hi, step):
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ret, fr = cap.read()
        if not ret: continue
        gray = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
        if prev_gray is not None:
            pts = cv2.goodFeaturesToTrack(prev_gray, 200, 0.01, 10)
            if pts is not None:
                bg = [p for p in pts if not
                      (cx0 < p[0][0] < cx1 and cy0 < p[0][1] < cy1)]
                if len(bg) >= 8:
                    bg = np.array(bg, dtype=np.float32).reshape(-1, 1, 2)
                    nxt, st, _ = cv2.calcOpticalFlowPyrLK(
                        prev_gray, gray, bg, None)
                    st = st.flatten()
                    go = bg.reshape(-1, 2)[st == 1]
                    gn = nxt.reshape(-1, 2)[st == 1]
                    if len(go) >= 8:
                        d = (gn - go) / max(i - prev_i, 1)
                        vecs.append([float(np.median(d[:, 0])),
                                     float(np.median(d[:, 1]))])
        prev_gray = gray; prev_i = i
    cap.release()

    if len(vecs) < 2:
        return {"ok": True, "mean": 0.0, "reason": None}  # can't judge

    v = np.array(vecs)
    mags = np.linalg.norm(v, axis=1)
    mean_m = float(np.mean(mags))
    std_m = float(np.std(mags))
    max_m = float(np.max(mags))

    moving = mean_m > MOTION_MEAN_LIMIT or std_m > MOTION_STD_LIMIT
    reason = None
    if moving:
        reason = ("The camera moved too much during this clip. "
                  "Rest your phone on something solid and keep it "
                  "completely still — don't pan or follow the ball. "
                  "Then re-film and try again.")
    return {"ok": not moving, "mean": round(mean_m, 2),
            "std": round(std_m, 2), "max": round(max_m, 2),
            "reason": reason}
