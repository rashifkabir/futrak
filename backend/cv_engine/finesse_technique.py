"""
Finesse technique scorer (90 deg side-on), modelled on
laces_technique.py's fault-gate + coordination + plateau structure.

Design:
  - Same fault-gate philosophy as laces: penalise clear FAULTS (no
    deceleration, closed body, an oversized release, a broken kinetic
    chain) -- don't score deviation from one ideal.
  - Kinetic-chain sequencing is REUSED from laces_technique.py
    unchanged -- proximal-to-distal firing order is the same physics
    regardless of shot type. Only the TIMING BANDS below are re-tuned
    for a controlled strike (fires later/tighter to contact than an
    explosive laces swing).
  - Finesse-specific: controlled DECELERATION into contact (the foot
    easing off, not still accelerating -- that's a laces fault here),
    OPEN BODY shape (shoulders opening up through the swing), and a
    COMPACT follow-through (short, not a full laces-style release).
  - Technique and power stay SEPARATE outputs, same as laces.

NOTE: every band below is a STARTING POINT -- there is no finesse-
specific coach-graded dataset yet (same caveat as laces_technique.py).
Re-calibrate against coach bands before locking, per the project's calibration policy.
"""
import cv2
import numpy as np

from backend.cv_engine.pose_extractor import extract_landmarks_from_video
from backend.cv_engine.angle_calculator import measure_follow_through
from backend.cv_engine.ball_detector import BallDetector
from backend.cv_engine.contact_detector import (
    find_contact_frame_index, filter_foot_glued_optical_flow)
from backend.cv_engine.laces_technique import (
    _make_geometry_helpers, _kinetic_chain, _band, _compress_top)

CHAIN_WINDOW_FRAMES = 18   # must match the _kinetic_chain() call below


# ---------------------------------------------------------------- measure
def measure_finesse_form(video_path):
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

    pt, mid = _make_geometry_helpers(lm, W, H)

    # KINETIC CHAIN: same physics as laces (proximal-to-distal firing
    # order), reused unchanged. Only the score bands differ (see
    # score_finesse_technique) -- a controlled finesse strike fires
    # later/tighter to contact, not more explosively.
    chain = _kinetic_chain(pt, mid, kr, knee_i, ank_i, c, fps,
                            window_frames=CHAIN_WINDOW_FRAMES)

    # CONTROLLED DECELERATION: ratio of ankle speed AT contact to the
    # PEAK ankle speed across the chain window. Laces wants the foot
    # still near-peak speed at contact (explosive drive-through);
    # finesse wants it easing off (wrapping through with control) --
    # so a LOW ratio here is the finesse signature, a ratio near 1 is
    # a laces-style fault.
    ank_speed_s = chain["ank_speed_s"]
    peak_ank_speed = float(np.max(ank_speed_s)) if len(ank_speed_s) else 0.0
    contact_ank_speed = float(ank_speed_s[-1]) if len(ank_speed_s) else 0.0
    decel_ratio = (contact_ank_speed / peak_ank_speed
                   if peak_ank_speed > 1e-6 else 1.0)

    # OPEN BODY SHAPE: a side-on camera can't measure absolute torso
    # rotation (that needs depth, the same limit noted for
    # plant_lateral_offset in laces_technique.py) -- but it CAN measure
    # the in-frame shoulder-to-shoulder gap widening as the body opens
    # through the swing. Ratio of that gap at contact vs. at the start
    # of the chain window (~address, before the swing rotates the
    # body): ~1 = never opened up (fault for finesse), notably >1 =
    # opened.
    def shoulder_gap(fn):
        ls, rs = pt(fn, 11), pt(fn, 12)
        return abs(ls[0] - rs[0]) if (ls is not None and rs is not None) else None

    chain_start = c - CHAIN_WINDOW_FRAMES
    ref_gap = shoulder_gap(chain_start)
    if ref_gap is None:
        for off in range(1, 7):
            ref_gap = shoulder_gap(chain_start + off)
            if ref_gap is not None:
                break
    contact_gap = shoulder_gap(c)
    if contact_gap is None:
        for off in (1, -1, 2, -2, 3, -3):
            contact_gap = shoulder_gap(c + off)
            if contact_gap is not None:
                break
    body_open_ratio = (contact_gap / ref_gap
                        if (ref_gap is not None and contact_gap is not None
                            and ref_gap > 1e-6) else None)

    # COMPACT FOLLOW-THROUGH: reuse measure_follow_through() directly
    # (angle_calculator.py) rather than reimplementing it -- max
    # upward ankle movement after contact. Laces rewards a big
    # release; finesse wants it SHORT/controlled, so this is scored
    # inverted (see score_finesse_technique).
    pre_landmarks = valid[ci - 1]["landmarks"] if ci >= 1 else None
    post_landmarks = valid[ci + 1]["landmarks"] if ci + 1 < len(valid) else None
    follow_through = (measure_follow_through(
        pre_landmarks, post_landmarks, "right" if kr else "left",
        all_frames=valid, contact_idx=ci
    ) if pre_landmarks is not None else None)

    return dict(hip_peak_at=chain["hip_peak_at"], knee_peak_at=chain["knee_peak_at"],
                foot_peak_at=chain["foot_peak_at"],
                hip_to_knee_gap=chain["hip_to_knee_gap"],
                knee_to_foot_gap=chain["knee_to_foot_gap"],
                chain_order_ok=chain["chain_order_ok"],
                peak_ank_speed=peak_ank_speed, contact_ank_speed=contact_ank_speed,
                decel_ratio=decel_ratio, body_open_ratio=body_open_ratio,
                follow_through=follow_through, contact_frame=c, kicking_right=kr)


# ---------------------------------------------------------------- score
def score_finesse_technique(m):
    """m = measure_finesse_form output.

    All bands are STARTING POINTS from zero finesse-specific coach
    data -- re-calibrate against coach bands before locking, per
    the calibration policy. Same applies to combinations of these features, not
    just each threshold individually.
    """
    # CONTROLLED DECELERATION: fault-gate on NO deceleration (ratio
    # near 1 -- foot still at peak speed at contact, explosive/laces-
    # like), not a reward for one ideal amount of easing off.
    decel = _band(m["decel_ratio"], lo_ok=0.25, hi_ok=0.70, lo_fail=0.05, hi_fail=0.95)

    # OPEN BODY SHAPE: fault-gate on failing to open up through the
    # swing (ratio ~=1), not a reward for one ideal degree of openness.
    if m["body_open_ratio"] is not None:
        body_open = _band(m["body_open_ratio"], lo_ok=1.05, hi_ok=1.6, lo_fail=0.9, hi_fail=2.2)
    else:
        body_open = 0.6  # not measurable on this clip -- neutral plateau, not a penalty

    # COMPACT FOLLOW-THROUGH: fault-gate on an oversized (laces-style)
    # release, not a reward for the shortest possible follow-through.
    if m["follow_through"] is not None:
        follow = _band(m["follow_through"], lo_ok=0.0, hi_ok=0.10, lo_fail=-0.02, hi_fail=0.22)
    else:
        follow = 0.6

    # KINETIC CHAIN: same order fault-gate as laces (chain_order_ok),
    # but TIMING bands tuned for a controlled strike -- fires later/
    # tighter to contact than an explosive laces swing.
    hip_timing = _band(m["hip_peak_at"], lo_ok=-7, hi_ok=-2, lo_fail=-13, hi_fail=2)
    knee_timing = _band(m["knee_peak_at"], lo_ok=-5, hi_ok=-1, lo_fail=-11, hi_fail=3)
    foot_timing = _band(m["foot_peak_at"], lo_ok=-3, hi_ok=0, lo_fail=-8, hi_fail=4)
    hip_knee_gap_score = _band(m["hip_to_knee_gap"], lo_ok=1, hi_ok=6, lo_fail=-4, hi_fail=11)
    knee_foot_gap_score = _band(m["knee_to_foot_gap"], lo_ok=1, hi_ok=5, lo_fail=-4, hi_fail=10)

    W = dict(decel=0.20, body_open=0.20, follow=0.15, hip_timing=0.12,
              knee_timing=0.12, foot_timing=0.11, hip_knee_gap=0.05, knee_foot_gap=0.05)
    raw = (decel * W["decel"] + body_open * W["body_open"] + follow * W["follow"]
           + hip_timing * W["hip_timing"] + knee_timing * W["knee_timing"]
           + foot_timing * W["foot_timing"] + hip_knee_gap_score * W["hip_knee_gap"]
           + knee_foot_gap_score * W["knee_foot_gap"])

    order_veto = 0.65 if not m["chain_order_ok"] else 1.0  # out-of-order kinetic chain
    linear = raw * order_veto * 100
    final = _compress_top(linear)

    return round(final, 1), dict(decel=decel, body_open=body_open, follow=follow,
                                 hip_timing=hip_timing, knee_timing=knee_timing,
                                 foot_timing=foot_timing,
                                 hip_knee_gap_score=hip_knee_gap_score,
                                 knee_foot_gap_score=knee_foot_gap_score,
                                 order_veto=order_veto, chain_order_ok=m["chain_order_ok"])


def analyse_finesse_technique(video_path):
    """Convenience: measure + score in one call."""
    m = measure_finesse_form(video_path)
    if m is None:
        return None
    score, breakdown = score_finesse_technique(m)
    return dict(score=score, measured=m, breakdown=breakdown)
