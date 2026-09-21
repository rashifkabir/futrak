"""
Contact detection and related foot/camera-side analysis for
ProPath FC shooting pipeline. Extracted from test_phase1.py so
it can be imported by both the main pipeline and diagnostics
without running pipeline code.
"""
import cv2
import numpy as np
from backend.cv_engine.angle_calculator import get_coords


def filter_foot_glued_optical_flow(valid_frames, detections,
                                   frame_w, frame_h,
                                   glue_px_factor=0.7,
                                   min_run=4):
    """
    Removes optical-flow ball detections that are GLUED to a
    foot for several consecutive frames. When the real ball
    leaves the frame, optical flow can latch onto a foot and
    drift with it, creating a phantom "ball" that causes false
    contacts (e.g. a post-shot ball-retrieval walk-up).

    A detection is foot-glued if it is optical_flow, within
    ~(ball diameter * factor) of a foot landmark, and stays
    that way for >= min_run consecutive frames. YOLO detections
    are NEVER touched. Real optical flow (post-strike, finishing)
    pulls AWAY from the feet, so it isn't glued and is kept.
    """
    lm_by = {f["frame"]: f["landmarks"] for f in valid_frames}

    def foot_pts_px(lm):
        pts = []
        for idx in (27, 28, 31, 32):  # ankles + toes
            c = get_coords(lm, idx)
            if c:
                pts.append((c[0] * frame_w, c[1] * frame_h))
        return pts

    # Flag each detection as foot-glued or not
    flags = []
    for idx, d in enumerate(detections):
        ball = d.get("ball")
        if ball is None or ball.get("method") != "optical_flow":
            flags.append(False)
            continue
        lm = lm_by.get(d["frame"])
        if lm is None:
            flags.append(False)
            continue
        feet = foot_pts_px(lm)
        if not feet:
            flags.append(False)
            continue
        bx, by = ball["cx"], ball["cy"]
        nearest = min(((bx-fx)**2 + (by-fy)**2) ** 0.5
                      for (fx, fy) in feet)
        diam = ball.get("diameter", 20)
        near_foot = nearest <= diam * glue_px_factor

        # The REAL ball right after a strike is near the foot
        # but MOVING fast (launching away). A phantom (optical
        # flow stuck on a foot) is near the foot AND nearly
        # stationary. So only flag as glued if near AND barely
        # moving vs the previous frame.
        prev_ball = detections[idx - 1]["ball"] if idx > 0 else None
        if prev_ball is not None:
            move = ((bx - prev_ball["cx"]) ** 2 +
                    (by - prev_ball["cy"]) ** 2) ** 0.5
        else:
            move = 999  # no previous → assume moving (don't flag)
        stationary = move < 3.0  # px/frame — essentially still

        glued = near_foot and stationary
        flags.append(glued)

    # Find runs of consecutive glued frames >= min_run, null them
    removed = 0
    i = 0
    n = len(detections)
    while i < n:
        if flags[i]:
            j = i
            while j < n and flags[j]:
                j += 1
            run_len = j - i
            if run_len >= min_run:
                for k in range(i, j):
                    detections[k]["ball"] = None
                    removed += 1
            i = j
        else:
            i += 1

    if removed:
        print(f"[foot-glue] removed {removed} optical-flow "
              f"detections glued to a foot (phantom ball)")
    return detections


def find_contact_frame_index(valid_frames: list, detections: list = None,
                             video_path: str = None):
    """
    Finds the SHOT contact frame.

    Primary (ball-based): foot-to-ball-centre distance. The
    SHOT is the LAST foot-ball contact after which the ball
    leaves and the foot never gets close again — ignoring
    pre-shot rolls/skills/dribble touches (each followed by
    another contact).

    Fallback (ankle-based): if ball data missing/sparse, uses
    the old kicking-ankle vs plant-ankle distance method.

    Returns (contact_idx, kicking_is_right) or None.
    """
    if len(valid_frames) < 5:
        return None

    # ── Determine kicking foot (movement-based) ──
    left_x_history, right_x_history = [], []
    for f in valid_frames:
        lm = f["landmarks"]
        la = get_coords(lm, 27)
        ra = get_coords(lm, 28)
        if la:
            left_x_history.append(la[0])
        if ra:
            right_x_history.append(ra[0])
    if not left_x_history or not right_x_history:
        return None
    left_movement    = max(left_x_history) - min(left_x_history)
    right_movement   = max(right_x_history) - min(right_x_history)
    kicking_is_right = right_movement > left_movement

    # ── Try BALL-BASED contact detection ──
    if detections:
        _cap = cv2.VideoCapture(video_path)
        _fw  = int(_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        _fh  = int(_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        _cap.release()
        ball_result = _contact_via_ball(
            valid_frames, detections, kicking_is_right, _fw, _fh
        )
        if ball_result is not None:
            contact_vf_i = ball_result if isinstance(ball_result, int) \
                           else ball_result[0]

            # ── Refine kicking foot by SPEED near contact ──
            # The striking foot moves fast through contact; the
            # plant foot is near-stationary. This is more reliable
            # than the movement-range heuristic above (which can
            # pick the wrong foot at awkward camera angles).
            speed_is_right = _kicking_foot_by_speed(
                valid_frames, contact_vf_i, _fw, _fh
            )
            if speed_is_right is not None:
                kicking_is_right = speed_is_right

            # ── Wrong-side camera WARNING (swing direction) ──
            # For a right-foot shot the kicking foot swings toward
            # +x through contact; left-foot toward -x. The opposite
            # suggests a wrong-side camera (or a trivela). Warning
            # only for now — not a hard stop.
            # Camera-side warning DISABLED: it depends on MediaPipe
            # left/right foot labels, which swap when the legs cross
            # at contact (false-alarms on correctly-filmed shots).
            # Camera-side guidance is in the filming manual instead.
            # _check_camera_side_warning(
            #     valid_frames, contact_vf_i, kicking_is_right, _fw, _fh
            # )

            return ball_result, kicking_is_right

    # ── FALLBACK: old ankle-distance method ──
    print("[contact] Ball-based failed — using ankle fallback")
    raw_scores = []
    for f in valid_frames:
        lm = f["landmarks"]
        la = get_coords(lm, 27)
        ra = get_coords(lm, 28)
        if not la or not ra:
            raw_scores.append(float("inf"))
            continue
        kick_x  = ra[0] if kicking_is_right else la[0]
        plant_x = la[0] if kicking_is_right else ra[0]
        raw_scores.append(abs(kick_x - plant_x))

    smoothed = []
    for i in range(len(raw_scores)):
        window = raw_scores[max(0, i - 1): i + 2]
        v = [s for s in window if s != float("inf")]
        smoothed.append(sum(v) / len(v) if v else float("inf"))

    search_range = smoothed[2:-2]
    if not search_range:
        return None
    best_idx = 2 + int(np.argmin(search_range))
    return best_idx, kicking_is_right


def _kicking_foot_by_speed(valid_frames, contact_vf_i,
                           frame_w, frame_h, window=4):
    """
    Identifies the kicking foot by SPEED near contact.
    The striking foot moves fast through contact; the plant
    foot is near-stationary. Returns True if RIGHT foot is
    the faster (kicking) foot, False if LEFT, None if unsure.
    """
    lo = max(0, contact_vf_i - window)
    hi = min(len(valid_frames) - 1, contact_vf_i + window)

    def ankle_px(lm, idx):
        c = get_coords(lm, idx)
        return (c[0] * frame_w, c[1] * frame_h) if c else None

    l_speeds, r_speeds = [], []
    prev_l = prev_r = None
    for i in range(lo, hi + 1):
        lm = valid_frames[i]["landmarks"]
        l = ankle_px(lm, 27)
        r = ankle_px(lm, 28)
        if l and prev_l:
            l_speeds.append(((l[0]-prev_l[0])**2 + (l[1]-prev_l[1])**2)**0.5)
        if r and prev_r:
            r_speeds.append(((r[0]-prev_r[0])**2 + (r[1]-prev_r[1])**2)**0.5)
        prev_l, prev_r = l, r

    if not l_speeds or not r_speeds:
        return None
    l_mean = sum(l_speeds) / len(l_speeds)
    r_mean = sum(r_speeds) / len(r_speeds)
    print(f"[kicking-foot] speed near contact: "
          f"left {l_mean:.1f}px/f, right {r_mean:.1f}px/f -> "
          f"{'right' if r_mean > l_mean else 'left'} foot kicking")
    if abs(r_mean - l_mean) < 1.0:
        return None
    return r_mean > l_mean


def _check_camera_side_warning(valid_frames, contact_vf_i,
                               kicking_is_right, frame_w, frame_h,
                               span=5):
    """
    WARNING-only check for wrong-side camera, using BODY
    POSITION (shot-type independent, unlike swing direction).

    For a RIGHT-foot shot the camera should be on the right,
    so the player's body appears in the LEFT portion of the
    frame. If the body is in the RIGHT portion, the camera is
    likely on the wrong side. Mirror for left-foot shots.

    Threshold is conservative (>60% / <40%) to avoid false
    positives on correctly-filmed shots where the player
    stands off-centre. Warning only; does not stop analysis.
    """
    lo = max(0, contact_vf_i - span)
    hi = contact_vf_i

    xs = []
    for i in range(lo, hi):
        lm = valid_frames[i]["landmarks"]
        pts = []
        for idx in (11, 12, 23, 24):  # shoulders + hips
            c = get_coords(lm, idx)
            if c:
                pts.append(c[0] * frame_w)
        if pts:
            xs.append(sum(pts) / len(pts))

    if not xs:
        return

    body_x   = sum(xs) / len(xs)
    body_pct = body_x / frame_w * 100
    foot     = "right" if kicking_is_right else "left"

    # Right-foot: body should be LEFT (low %). Wrong if RIGHT (>60%).
    # Left-foot:  body should be RIGHT (high %). Wrong if LEFT (<40%).
    wrong_side = (kicking_is_right and body_pct > 60) or \
                 (not kicking_is_right and body_pct < 40)

    if wrong_side:
        good = "right" if kicking_is_right else "left"
        print("\n" + "!" * 55)
        print("WARNING — POSSIBLE WRONG CAMERA SIDE")
        print("!" * 55)
        print(f"The player's body is on the "
              f"{'right' if body_pct > 50 else 'left'} side of frame "
              f"({body_pct:.0f}%),")
        print(f"but for a {foot}-foot shot the camera should be on")
        print(f"your {good} side (body should appear "
              f"{'left' if kicking_is_right else 'right'} of frame).")
        print(f"Film from your {good}-foot side with the ball visible.")
        print("Results from this angle may be less reliable.")
        print(f"[debug] body at {body_pct:.0f}% across frame")
        print("!" * 55 + "\n")
    else:
        print(f"[camera-side] OK — body at {body_pct:.0f}% across "
              f"frame ({foot}-foot shot)")
def _kicking_foot_by_proximity(valid_frames, detections,
                               ball_result, frame_w, frame_h):
    """
    At the contact frame, returns True if the RIGHT foot is
    closest to the ball, False if the LEFT foot is, or None
    if undetermined. This is the physical kicking foot — more
    reliable than the movement heuristic, used to flag bad
    camera angles when the two methods disagree.
    """
    contact_vf_i = ball_result if isinstance(ball_result, int) else ball_result[0]
    if contact_vf_i >= len(valid_frames):
        return None

    f = valid_frames[contact_vf_i]
    frame_no = f["frame"]
    lm = f["landmarks"]

    ball_map = {
        d["frame"]: d["ball"]
        for d in detections if d.get("ball") is not None
    }
    ball = ball_map.get(frame_no)
    if ball is None:
        for off in (1, -1, 2, -2, 3, -3):
            ball = ball_map.get(frame_no + off)
            if ball:
                break
    if ball is None:
        return None
    bx, by = ball["cx"], ball["cy"]

    def foot_dist(toe_i, ankle_i):
        pts = []
        toe   = get_coords(lm, toe_i)
        ankle = get_coords(lm, ankle_i)
        if toe:
            pts.append((toe[0] * frame_w, toe[1] * frame_h))
        if ankle:
            pts.append((ankle[0] * frame_w, ankle[1] * frame_h))
        if not pts:
            return float("inf")
        return min(((px - bx) ** 2 + (py - by) ** 2) ** 0.5
                   for (px, py) in pts)

    right_d = foot_dist(32, 28)
    left_d  = foot_dist(31, 27)

    if right_d == float("inf") and left_d == float("inf"):
        print("[proximity] both feet undetermined → None")
        return None
    print(f"[proximity] at contact: right foot {right_d:.0f}px, "
          f"left foot {left_d:.0f}px from ball → "
          f"{'right' if right_d < left_d else 'left'} is closer")
    return right_d < left_d


def _contact_via_ball(valid_frames, detections, kicking_is_right,
                      frame_w, frame_h):
    """
    Ball-based contact detection. Foot landmarks are NORMALIZED
    (0-1) — converted to pixels via frame_w/frame_h before
    comparing to ball pixel coords. SHOT = last contact episode.
    Returns valid_frames index, or None.
    """
    ball_map = {
        d["frame"]: d["ball"]
        for d in detections
        if d.get("ball") is not None
    }
    if len(ball_map) < 5:
        return None

    # Measure against BOTH feet so a wrong kicking-foot pre-guess
    # cannot break contact detection. The ball is near whichever
    # foot strikes it; the kicking foot is refined later by speed.
    foot_indices = [27, 28, 31, 32]   # both ankles + both toes

    dists = []
    for vf_i, f in enumerate(valid_frames):
        frame_no = f["frame"]
        ball     = ball_map.get(frame_no)
        lm       = f["landmarks"]
        if ball is None:
            dists.append((vf_i, float("inf"), None))
            continue
        foot_pts = []
        for _idx in foot_indices:
            _c = get_coords(lm, _idx)
            if _c:
                foot_pts.append((_c[0] * frame_w, _c[1] * frame_h))
        if not foot_pts:
            dists.append((vf_i, float("inf"), None))
            continue
        bx, by = ball["cx"], ball["cy"]
        best_d = min(
            ((fx - bx) ** 2 + (fy - by) ** 2) ** 0.5
            for (fx, fy) in foot_pts
        )
        dists.append((vf_i, best_d, ball.get("diameter", 20)))

    valid_d = [d for (_, d, _) in dists if d != float("inf")]
    if not valid_d:
        return None
    diam_vals   = [dm for (_, _, dm) in dists if dm]
    median_diam = np.median(diam_vals) if diam_vals else 25
    threshold   = median_diam * 1.6

    in_contact = [
        (vf_i, d) for (vf_i, d, _) in dists
        if d != float("inf") and d <= threshold
    ]
    if not in_contact:
        return None

    episodes = []
    cur = [in_contact[0]]
    for k in range(1, len(in_contact)):
        if in_contact[k][0] - in_contact[k - 1][0] <= 3:
            cur.append(in_contact[k])
        else:
            episodes.append(cur)
            cur = [in_contact[k]]
    episodes.append(cur)

    # ── Select the SHOT episode by BALL LAUNCH SPEED ──
    # The shot launches the ball fast; pre-shot rolls and
    # post-shot touches/false-positives do not. Measure each
    # episode's ball velocity in the ~6 frames AFTER it and
    # pick the episode with the biggest launch. This is robust
    # to long videos where the shot is NOT the last contact.
    ball_by_frame = {
        d["frame"]: d["ball"]
        for d in detections if d.get("ball") is not None
    }

    def episode_launch_speed(episode):
        # frame number of the min-distance (contact) point
        c_vf_i = min(episode, key=lambda t: t[1])[0]
        c_frame = valid_frames[c_vf_i]["frame"]
        # Gather ball positions in the launch window after contact.
        pts = []
        for fn in range(c_frame + 1, c_frame + 10):
            b = ball_by_frame.get(fn)
            if b is not None:
                pts.append((fn, b["cx"], b["cy"]))
        if len(pts) < 3:
            return 0.0, 0.0
        # SUSTAINED DIRECTIONAL launch: net displacement from the
        # first to last launch point, per frame. A real shot moves
        # the ball CONSISTENTLY in one direction over several
        # frames. A one-frame retrieval/clearance spike does NOT
        # sustain, so its net directional speed is low relative to
        # its peak. This rejects fast retrievals and catches soft
        # but sustained shots.
        f0, x0, y0 = pts[0]
        f1, x1, y1 = pts[-1]
        span = f1 - f0
        if span <= 0:
            return 0.0, 0.0
        net = ((x1-x0)**2 + (y1-y0)**2) ** 0.5 / span
        # also peak (for reference), but SCORE on net directional
        peak = 0.0
        for k in range(1, len(pts)):
            df = pts[k][0]-pts[k-1][0]
            if df <= 0: continue
            dx = pts[k][1]-pts[k-1][1]; dy = pts[k][2]-pts[k-1][2]
            peak = max(peak, (dx*dx+dy*dy)**0.5/df)
        return net, peak

    # Score episodes by SUSTAINED directional launch. Among
    # episodes with a real launch (net directional speed above a
    # low floor that catches soft shots but excludes jitter),
    # prefer the EARLIEST — the shot comes before any later
    # retrieval/clearance. This avoids picking a fast post-shot
    # boot-back as "the shot".
    scored = []
    for ep in episodes:
        net, peak = episode_launch_speed(ep)
        c_vf_i = min(ep, key=lambda t: t[1])[0]
        c_frame = valid_frames[c_vf_i]["frame"]
        scored.append((ep, net, peak, c_frame))
    # real launches: net directional speed >= 2 px/f (soft shots
    # like 4-7px/f pass; pre-shot jitter ~0-1px/f does not)
    LAUNCH_FLOOR = 2.0
    real = [s for s in scored if s[1] >= LAUNCH_FLOOR]
    if real:
        # earliest real launch = the shot (retrievals come later)
        shot_episode = min(real, key=lambda s: s[3])[0]
    else:
        # nothing clears the floor — fall back to biggest net
        shot_episode = max(scored, key=lambda s: s[1])[0]
    contact_vf_i = min(shot_episode, key=lambda t: t[1])[0]

    _sel_net = next((s[1] for s in scored
                     if min(s[0], key=lambda t: t[1])[0] == contact_vf_i), 0.0)
    print(f"[contact] Ball-based: {len(episodes)} episode(s); "
          f"earliest sustained launch ({_sel_net:.1f}px/f net), "
          f"shot contact at frame "
          f"{valid_frames[contact_vf_i]['frame']} "
          f"(threshold {threshold:.0f}px)")
    return contact_vf_i
