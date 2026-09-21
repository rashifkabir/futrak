"""
Laces technique scorer (90 deg side-on, re-calibrated).

Design (validated against good/avg/bad laces):
  - Foot speed REMOVED from technique (lives in power; no double-count).
  - Body lean = forgiving FAULT GATE: acceptable posture scores fine;
    only EXTREME back-lean is penalised (band + veto).
  - Hip-drive TIMING (not magnitude) = top positive separator.
  - Swing path, balance, pre-impact foot accel = supporting form.
  - Fault-free form plateaus (~0.60) so 'solid but ordinary' lands
    mid-70s; compression above 80 so 88+ needs a near-perfect shot.

NOTE: thresholds calibrated from a small clip set -- a STARTING point.
Re-calibrate against a coach-graded dataset before locking.
"""
import cv2
import numpy as np
from scipy.signal import butter, filtfilt

from backend.cv_engine.pose_extractor import extract_landmarks_from_video
from backend.cv_engine.angle_calculator import get_coords, calculate_angle
from backend.cv_engine.ball_detector import BallDetector
from backend.cv_engine.contact_detector import (
    find_contact_frame_index, filter_foot_glued_optical_flow)


# ---------------------------------------------------------------- helpers
def _smooth(arr, cutoff=6.0, fs=240.0, order=3):
    arr = np.array(arr, float)
    if len(arr) <= order * 3:
        return arr
    b, a = butter(order, cutoff / (fs / 2), 'low')
    return filtfilt(b, a, arr)


def _ms_to_frames(ms, fps):
    """Convert a millisecond window to a frame count at the clip's
    actual fps (never assume 240 -- get_actual_fps already resolves
    iPhone slow-mo containers that misreport as 30fps)."""
    return max(1, round(ms / 1000.0 * fps))


def _pos_jitter(fn_range, point_fn, norm):
    """Std-dev of Euclidean distance from the mean position over a
    frame window, normalised by `norm`. Same idea as balance_jit
    (positional wobble = instability, not a deviation-from-ideal
    score) generalised from 1D (x-only) to full 2D drift."""
    pts = [point_fn(fn) for fn in fn_range]
    pts = [p for p in pts if p is not None]
    if len(pts) < 3:
        return 0.0
    arr = np.array(pts)
    d = np.linalg.norm(arr - arr.mean(axis=0), axis=1)
    return float(np.std(d) / norm)


def _make_geometry_helpers(lm, W, H):
    """pt()/mid() pixel-space landmark lookups, shared by every shot-type
    scorer -- factored out so laces/finesse/trivela don't each reimplement
    the same normalised-coord-to-pixel conversion."""
    def pt(fn, i):
        l = lm.get(fn)
        if not l:
            return None
        co = get_coords(l, i)
        return np.array([co[0] * W, co[1] * H]) if co else None

    def mid(fn, a, b):
        pa, pb = pt(fn, a), pt(fn, b)
        return (pa + pb) / 2.0 if (pa is not None and pb is not None) else None

    return pt, mid


def _nearest_frame_all_visible(lm, fn, idxs, max_off=6):
    """Nearest frame to `fn` (search order 0,-1,+1,-2,+2,...) where every
    landmark in `idxs` clears get_coords' visibility threshold. Shared
    fallback for landmarks that are routinely occluded at the exact
    contact frame (e.g. the plant leg behind the swinging kicking leg)."""
    for off in sorted(range(-max_off, max_off + 1), key=abs):
        l = lm.get(fn + off)
        if l and all(get_coords(l, i) is not None for i in idxs):
            return fn + off
    return None


def _band(value, lo_ok, hi_ok, lo_fail, hi_fail, plateau=0.60):
    """plateau inside [lo_ok,hi_ok] rising to 1.0 at band centre;
    ramps to 0 at the fail edges."""
    if lo_ok <= value <= hi_ok:
        centre = (lo_ok + hi_ok) / 2.0
        half = (hi_ok - lo_ok) / 2.0 or 1.0
        closeness = 1.0 - abs(value - centre) / half
        return plateau + (1.0 - plateau) * closeness
    if value < lo_ok:
        return max(0.0, plateau * (value - lo_fail) / (lo_ok - lo_fail)) if lo_ok > lo_fail else 0.0
    return max(0.0, plateau * (hi_fail - value) / (hi_fail - hi_ok)) if hi_fail > hi_ok else 0.0


def _compress_top(linear, cap=80, ceiling=9, exponent=0.45):
    """Compression above `cap`: shared plateau curve so 88+ needs a
    near-perfect input, regardless of shot type."""
    if linear <= cap:
        return linear
    over = (linear - cap) / (100 - cap)
    return cap + ceiling * (over ** exponent)


def _peak_angvel_at(fn_range, angle_fn, fps, direction=None):
    """Angle time-series (degrees) -> frame offset (neg = before contact)
    of peak angular velocity. Shared by hip/knee timing below.
    direction=None: peak |velocity| (hip -- validated as-is, don't touch).
    direction=+1: peak POSITIVE velocity only, i.e. angle increasing
    (knee -- the raw joint angle rises during cocking-then-extend AND
    falls during cocking depending on phase; abs() can't tell the fast
    cocking-phase flex from the release-phase extension apart, so we
    pin to the extension sign instead)."""
    ang = []
    for fn in fn_range:
        a = angle_fn(fn)
        ang.append(a if a is not None else np.nan)
    ang = np.array(ang)
    if np.isnan(ang).any():
        idx = np.arange(len(ang)); g = ~np.isnan(ang)
        if g.sum() > 2:
            ang = np.interp(idx, idx[g], ang[g])
        else:
            return -99
    vel = np.diff(_smooth(ang) if len(ang) > 10 else ang) * fps
    if not len(vel):
        return -99
    idx = np.argmax(vel) if direction == 1 else np.argmax(np.abs(vel))
    return int(idx - len(vel))


def _kinetic_chain(pt, mid, kr, knee_i, ank_i, c, fps, window_frames=18):
    """hip->knee->foot peak-velocity sequencing (timing, gaps, order
    fault-gate). Shared by every shot-type scorer -- the proximal-to-
    distal firing-order PHYSICS doesn't change by shot type, only each
    scorer's score bands do."""
    chain_window = range(c - window_frames, c + 1)

    # HIP TIMING: peak torso-thigh angular-velocity, frames before impact
    def _hip_angle(fn):
        sh, hp, kn = mid(fn, 11, 12), mid(fn, 23, 24), pt(fn, knee_i)
        if sh is None or hp is None or kn is None:
            return None
        v1, v2 = sh - hp, kn - hp
        cs = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-9)
        return np.degrees(np.arccos(np.clip(cs, -1, 1)))
    hip_angle_series = [_hip_angle(fn) for fn in chain_window]
    hip_peak_at = _peak_angvel_at(chain_window, _hip_angle, fps)

    # KNEE TIMING: peak knee-EXTENSION angular-velocity (hip-knee-ankle).
    # Angle -> 180 deg as the leg straightens, so extension = angle
    # increasing; direction=+1 isolates that from the earlier cocking-phase
    # flex (angle decreasing), which argmax(abs(vel)) can't tell apart.
    def _knee_angle(fn):
        hp, kn, an = pt(fn, 23 if not kr else 24), pt(fn, knee_i), pt(fn, ank_i)
        if hp is None or kn is None or an is None:
            return None
        v1, v2 = hp - kn, an - kn
        cs = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-9)
        return np.degrees(np.arccos(np.clip(cs, -1, 1)))
    knee_peak_at = _peak_angvel_at(chain_window, _knee_angle, fps, direction=1)

    # FOOT/ANKLE TIMING: peak ankle LINEAR speed (most distal link -- by
    # contact the foot is travelling, not rotating about a distal joint).
    ank_speed = []
    for fn in chain_window:
        a0, a1 = pt(fn - 1, ank_i), pt(fn, ank_i)
        ank_speed.append(np.linalg.norm(a1 - a0) if (a0 is not None and a1 is not None) else np.nan)
    ank_speed = np.array(ank_speed)
    if np.isnan(ank_speed).any():
        idx = np.arange(len(ank_speed)); g = ~np.isnan(ank_speed)
        ank_speed = np.interp(idx, idx[g], ank_speed[g]) if g.sum() > 2 else ank_speed
    ank_speed_s = _smooth(ank_speed) if len(ank_speed) > 10 else ank_speed
    foot_peak_at = int(np.argmax(ank_speed_s) - len(ank_speed_s)) if len(ank_speed_s) else -99

    # ORDERING + GAPS: proximal-to-distal fault-gate check, not reward-the-ideal.
    hip_to_knee_gap = knee_peak_at - hip_peak_at
    knee_to_foot_gap = foot_peak_at - knee_peak_at
    chain_order_ok = bool(hip_peak_at <= knee_peak_at <= foot_peak_at)

    return dict(hip_peak_at=hip_peak_at, knee_peak_at=knee_peak_at,
                foot_peak_at=foot_peak_at, hip_to_knee_gap=hip_to_knee_gap,
                knee_to_foot_gap=knee_to_foot_gap, chain_order_ok=chain_order_ok,
                ank_speed_s=ank_speed_s, hip_angle_series=hip_angle_series)


# ---------------------------------------------------------------- measure
def measure_laces_form(video_path):
    """Returns dict of measured form signals, or None if no contact."""
    frames = extract_landmarks_from_video(video_path, draw_skeleton=False)
    if frames is None:
        return None
    valid = [f for f in frames if f["landmarks"] is not None]
    if not valid:
        return None

    cap = cv2.VideoCapture(video_path)
    W = int(cap.get(3)); H = int(cap.get(4)); cap.release()
    lm = {f["frame"]: f["landmarks"] for f in valid}

    det = BallDetector()
    dets, fps = det.track_shot_only(video_path)
    dets = filter_foot_glued_optical_flow(valid, dets, W, H)
    res = find_contact_frame_index(valid, dets, video_path)
    if res is None or isinstance(res, dict):
        return None
    ci, kr = res
    c = valid[ci]["frame"]
    knee_i, ank_i = (26, 28) if kr else (25, 27)
    # support (plant) leg = opposite of the kicking leg
    supp_hip_i, supp_knee_i, supp_ank_i = (23, 25, 27) if kr else (24, 26, 28)

    pt, mid = _make_geometry_helpers(lm, W, H)

    hp_c, ka_c = mid(c, 23, 24), pt(c, ank_i)
    ball_dir = np.sign(ka_c[0] - hp_c[0]) if (hp_c is not None and ka_c is not None) else 1

    # LEAN: trunk vs vertical across downswing (+fwd / -back), smoothed
    lean = []
    for fn in range(c - 15, c + 1):
        sh, hp = mid(fn, 11, 12), mid(fn, 23, 24)
        if sh is not None and hp is not None:
            lean.append(np.degrees(np.arctan2((sh[0] - hp[0]) * ball_dir, abs(hp[1] - sh[1]))))
    lean = _smooth(lean) if len(lean) > 10 else np.array(lean)
    lean_impact = float(lean[-1]) if len(lean) else 0.0
    lean_stab = float(np.std(lean)) if len(lean) else 0.0

    chain = _kinetic_chain(pt, mid, kr, knee_i, ank_i, c, fps)
    hip_peak_at = chain["hip_peak_at"]
    knee_peak_at = chain["knee_peak_at"]
    foot_peak_at = chain["foot_peak_at"]
    hip_to_knee_gap = chain["hip_to_knee_gap"]
    knee_to_foot_gap = chain["knee_to_foot_gap"]
    chain_order_ok = chain["chain_order_ok"]

    # BALANCE: horizontal hip jitter pre-contact
    hipj = [mid(fn, 23, 24) for fn in range(c - 10, c + 1)]
    hipj = [h for h in hipj if h is not None]
    balance_jit = float(np.std([h[0] for h in hipj]) / W) if len(hipj) > 3 else 0.0

    # STABILITY WINDOW (~150-200ms pre-contact, converted to frames at
    # this clip's ACTUAL fps -- never hardcode a frame count, slow-mo
    # containers can misreport fps). Positional jitter = instability
    # fault signal, not a deviation-from-ideal score.
    stab_window_frames = _ms_to_frames(175, fps)
    stab_range = range(c - stab_window_frames, c + 1)
    head_jit = _pos_jitter(stab_range, lambda fn: pt(fn, 0), W)
    trunk_sway = _pos_jitter(stab_range, lambda fn: mid(fn, 11, 12), W)
    pelvis_jit = _pos_jitter(stab_range, lambda fn: mid(fn, 23, 24), W)
    support_knee_jit = _pos_jitter(stab_range, lambda fn: pt(fn, supp_knee_i), W)
    plant_foot_jit = _pos_jitter(stab_range, lambda fn: pt(fn, supp_ank_i), W)

    # PLANT-FOOT / SUPPORT-LEG GEOMETRY at contact. Ball position from
    # the already-tracked/filtered detections; fall back to the
    # nearest nearby frame if the exact contact frame has no detection
    # (same pattern as contact_detector._kicking_foot_by_proximity).
    ball_by_frame = {d["frame"]: d["ball"] for d in dets if d.get("ball")}
    ball_c = ball_by_frame.get(c)
    if ball_c is None:
        for off in (1, -1, 2, -2, 3, -3):
            ball_c = ball_by_frame.get(c + off)
            if ball_c is not None:
                break

    # The support leg is frequently occluded by the kicking leg
    # swinging through right at the contact frame (visibility drops
    # below get_coords' 0.7 threshold at that single frame on every
    # clip tested) -- but the plant foot is, by definition, grounded
    # and near-stationary through contact, so a nearby frame where
    # it's actually visible is a sound stand-in, not a fudge.
    supp_ank_fn = _nearest_frame_all_visible(lm, c, (supp_ank_i,))
    supp_ank_c = pt(supp_ank_fn, supp_ank_i) if supp_ank_fn is not None else None
    if ball_c is not None and supp_ank_c is not None:
        diam = ball_c.get("diameter") or 1
        dx = supp_ank_c[0] - ball_c["cx"]
        dy = supp_ank_c[1] - ball_c["cy"]
        # distances in ball-widths (scale-invariant), not raw pixels --
        # mirrors how ball_detector.py itself calibrates scale from
        # ball diameter rather than frame width.
        plant_ball_dist = float(np.hypot(dx, dy) / diam)
        # x-only, signed by ball_dir: + = plant foot AHEAD of the ball
        # (toward the target), - = behind. This is fore-aft/swing-
        # direction placement, NOT true medial-lateral -- a side-on
        # camera can't see the sideways-from-above axis at all.
        plant_lateral_offset = float((dx * ball_dir) / diam)
    else:
        plant_ball_dist = None
        plant_lateral_offset = None

    knee_fn = _nearest_frame_all_visible(lm, c, (supp_hip_i, supp_knee_i, supp_ank_i))
    support_knee_flexion = calculate_angle(
        pt(knee_fn, supp_hip_i), pt(knee_fn, supp_knee_i), pt(knee_fn, supp_ank_i)
    ) if knee_fn is not None else None

    # PRE-IMPACT FOOT ACCEL: ankle still speeding up into contact?
    sp = []
    for fn in range(c - 6, c + 1):
        a0, a1 = pt(fn - 1, ank_i), pt(fn, ank_i)
        if a0 is not None and a1 is not None:
            sp.append(np.linalg.norm(a1 - a0))
    foot_accel = float(sp[-1] - np.mean(sp[:3])) if len(sp) >= 4 else 0.0

    return dict(lean_impact=lean_impact, lean_stab=lean_stab,
                hip_peak_at=hip_peak_at, knee_peak_at=knee_peak_at,
                foot_peak_at=foot_peak_at, hip_to_knee_gap=hip_to_knee_gap,
                knee_to_foot_gap=knee_to_foot_gap, chain_order_ok=chain_order_ok,
                balance_jit=balance_jit, foot_accel=foot_accel,
                stab_window_frames=stab_window_frames, head_jit=head_jit,
                trunk_sway=trunk_sway, pelvis_jit=pelvis_jit,
                support_knee_jit=support_knee_jit, plant_foot_jit=plant_foot_jit,
                plant_ball_dist=plant_ball_dist,
                plant_lateral_offset=plant_lateral_offset,
                support_knee_flexion=support_knee_flexion,
                contact_frame=c, kicking_right=kr)


# ---------------------------------------------------------------- score
def score_laces_technique(m, swing_path=None):
    """m = measure_laces_form output. swing_path: 0..1 from your real
    swing measurement (None -> neutral placeholder)."""
    lean = _band(m["lean_impact"], lo_ok=-12, hi_ok=18, lo_fail=-24, hi_fail=30)
    hip_timing = _band(m["hip_peak_at"], lo_ok=-9, hi_ok=-3, lo_fail=-16, hi_fail=2)
    # knee/foot bands: starting points only (small clip set) -- one link
    # closer to contact than hip's, per proximal-to-distal firing order.
    # Re-calibrate against coach-banded clips before locking, per the project's calibration policy.
    knee_timing = _band(m["knee_peak_at"], lo_ok=-7, hi_ok=-2, lo_fail=-14, hi_fail=3)
    foot_timing = _band(m["foot_peak_at"], lo_ok=-4, hi_ok=0, lo_fail=-10, hi_fail=4)
    # gap scores: fault-gate on a broken/collapsed/inverted gap, not reward
    # for hitting one ideal spacing -- wide plateau in the middle.
    hip_knee_gap_score = _band(m["hip_to_knee_gap"], lo_ok=1, hi_ok=8, lo_fail=-4, hi_fail=14)
    knee_foot_gap_score = _band(m["knee_to_foot_gap"], lo_ok=1, hi_ok=6, lo_fail=-4, hi_fail=12)
    balance = _band(m["balance_jit"], lo_ok=0.0, hi_ok=0.012, lo_fail=-1, hi_fail=0.035)
    accel = _band(m["foot_accel"], lo_ok=0.0, hi_ok=99, lo_fail=-8, hi_fail=1e9)
    stab = _band(m["lean_stab"], lo_ok=0.0, hi_ok=2.0, lo_fail=-1, hi_fail=4.5)
    swing = swing_path if swing_path is not None else 0.60

    W = dict(lean=0.18, hip_timing=0.09, knee_timing=0.09, foot_timing=0.09,
              hip_knee_gap=0.04, knee_foot_gap=0.04, balance=0.14, accel=0.12,
              stab=0.08, swing=0.13)
    raw = (lean * W["lean"] + hip_timing * W["hip_timing"] + knee_timing * W["knee_timing"]
           + foot_timing * W["foot_timing"] + hip_knee_gap_score * W["hip_knee_gap"]
           + knee_foot_gap_score * W["knee_foot_gap"] + balance * W["balance"]
           + accel * W["accel"] + stab * W["stab"] + swing * W["swing"])

    lean_veto = 0.70 if m["lean_impact"] < -16 else 1.0    # extreme back-lean fault
    order_veto = 0.65 if not m["chain_order_ok"] else 1.0  # out-of-order kinetic chain
    veto = lean_veto * order_veto
    linear = raw * veto * 100
    final = _compress_top(linear)

    return round(final, 1), dict(lean=lean, hip_timing=hip_timing,
                                 knee_timing=knee_timing, foot_timing=foot_timing,
                                 hip_knee_gap_score=hip_knee_gap_score,
                                 knee_foot_gap_score=knee_foot_gap_score,
                                 balance=balance, accel=accel, stab=stab,
                                 swing=swing, veto=veto, order_veto=order_veto,
                                 chain_order_ok=m["chain_order_ok"])


def analyse_laces_technique(video_path, swing_path=None):
    """Convenience: measure + score in one call."""
    m = measure_laces_form(video_path)
    if m is None:
        return None
    score, breakdown = score_laces_technique(m, swing_path=swing_path)
    return dict(score=score, measured=m, breakdown=breakdown)