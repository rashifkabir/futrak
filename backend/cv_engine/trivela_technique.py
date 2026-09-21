"""
Trivela technique scorer (filmed from the PLANTING-foot side -- the
opposite convention to laces/finesse's kicking-foot side. The wrap-
around trivela swing crosses in FRONT of the body; filmed from the
kicking-foot side that crossing motion is mostly along the camera's
depth axis (invisible to a 2D camera), but from the planting-foot side
it shows up as clear in-frame horizontal motion. See project design notes.).

Same fault-gate + coordination + plateau structure as laces/finesse,
reusing shared logic rather than duplicating it: _make_geometry_helpers,
_kinetic_chain (same proximal-to-distal firing-order physics, trivela-
tuned bands only), _pos_jitter, _band, _compress_top, contact
detection are all imported from laces_technique.py / contact_detector.py.

Trivela-specific:
  - Hip-foot DISSOCIATION (the defining trait): the hip/torso should
    stay relatively quiet while the foot independently whips around --
    unlike laces/finesse where hip and foot move together. Measured as
    peak (normalised) ankle speed vs. hip angular RANGE-of-motion, not
    hip TIMING (that's a different question, already covered by the
    reused kinetic-chain gaps below).
  - INSIDE-OUT / cross-body swing direction: does the kicking ankle's
    in-frame position actually cross the hip midline between the start
    of the backswing and contact? This is only measurable at all
    because of the planting-foot-side filming convention above.
  - TIMING SEPARATION: reused directly from _kinetic_chain's existing
    hip_to_knee_gap / knee_to_foot_gap, just with wider trivela-tuned
    bands (a delayed, independent foot action is the trivela signature,
    not a fault the way a big gap might be for laces).
  - BALANCE COMPENSATION on a compact backswing: reused directly via
    _pos_jitter over the same chain window (pelvis jitter) -- no new
    measurement code, trivela just cares about it more given the more
    awkward compact backswing.

NOTE: every band below is a STARTING POINT -- there is no trivela-
specific coach-graded dataset yet (same caveat as laces/finesse).
Re-calibrate against coach bands before locking, per the project's calibration policy.
"""
import cv2
import numpy as np

from backend.cv_engine.pose_extractor import extract_landmarks_from_video
from backend.cv_engine.ball_detector import BallDetector
from backend.cv_engine.contact_detector import (
    find_contact_frame_index, filter_foot_glued_optical_flow)
from backend.cv_engine.laces_technique import (
    _make_geometry_helpers, _kinetic_chain, _pos_jitter, _band, _compress_top)

CHAIN_WINDOW_FRAMES = 18   # must match the _kinetic_chain() call below


# ---------------------------------------------------------------- measure
def measure_trivela_form(video_path):
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

    # KINETIC CHAIN: same physics as laces/finesse (proximal-to-distal
    # firing order), reused unchanged. Also gives us hip_angle_series
    # (for dissociation below) and the timing gaps (for timing
    # separation below) without recomputing anything.
    chain = _kinetic_chain(pt, mid, kr, knee_i, ank_i, c, fps,
                            window_frames=CHAIN_WINDOW_FRAMES)
    chain_window = range(c - CHAIN_WINDOW_FRAMES, c + 1)

    # HIP-FOOT DISSOCIATION: hip angular RANGE-of-motion (how much the
    # hip itself rotates through the swing) vs peak ankle speed
    # (normalised by frame width -- scale-invariant, matches
    # _pos_jitter's /W convention elsewhere). High ratio = the foot did
    # the work while the hip stayed quiet (correct trivela wrap); low
    # ratio = the whole body rotated together, i.e. more laces-like --
    # a fault for trivela.
    hip_series = [a for a in chain["hip_angle_series"] if a is not None]
    hip_range_deg = float(max(hip_series) - min(hip_series)) if len(hip_series) >= 2 else 0.0
    ank_speed_s = chain["ank_speed_s"]
    peak_ank_speed_norm = float(np.max(ank_speed_s)) / W if len(ank_speed_s) else 0.0
    dissociation_ratio = peak_ank_speed_norm / (hip_range_deg + 1e-6)

    # INSIDE-OUT / CROSS-BODY SWING: kicking-ankle x relative to the
    # hip-midline x, comparing the start of the backswing to contact.
    # Only measurable because of the planting-foot-side filming
    # convention (see module docstring) -- from the kicking-foot side
    # this crossing motion is mostly along the invisible depth axis.
    def rel_ankle_x(fn):
        an, hp = pt(fn, ank_i), mid(fn, 23, 24)
        return (an[0] - hp[0]) if (an is not None and hp is not None) else None

    chain_start = c - CHAIN_WINDOW_FRAMES
    rel_start = rel_ankle_x(chain_start)
    if rel_start is None:
        for off in range(1, 7):
            rel_start = rel_ankle_x(chain_start + off)
            if rel_start is not None:
                break
    rel_contact = rel_ankle_x(c)
    if rel_contact is None:
        for off in (1, -1, 2, -2, 3, -3):
            rel_contact = rel_ankle_x(c + off)
            if rel_contact is not None:
                break
    if rel_start is not None and rel_contact is not None:
        crossed_midline = bool(np.sign(rel_start) != np.sign(rel_contact))
        cross_body_shift_norm = float((rel_contact - rel_start) / W)
    else:
        crossed_midline = None
        cross_body_shift_norm = None

    # TIMING SEPARATION: reused directly from the shared kinetic chain,
    # no new computation -- just scored differently below (trivela
    # expects a WIDER, more independent gap than laces).
    hip_to_knee_gap = chain["hip_to_knee_gap"]
    knee_to_foot_gap = chain["knee_to_foot_gap"]

    # BALANCE COMPENSATION on a compact backswing: reused directly via
    # _pos_jitter (pelvis position jitter) over the same chain window.
    pelvis_jit = _pos_jitter(chain_window, lambda fn: mid(fn, 23, 24), W)

    return dict(hip_peak_at=chain["hip_peak_at"], knee_peak_at=chain["knee_peak_at"],
                foot_peak_at=chain["foot_peak_at"],
                hip_to_knee_gap=hip_to_knee_gap, knee_to_foot_gap=knee_to_foot_gap,
                chain_order_ok=chain["chain_order_ok"],
                hip_range_deg=hip_range_deg, peak_ank_speed_norm=peak_ank_speed_norm,
                dissociation_ratio=dissociation_ratio,
                crossed_midline=crossed_midline,
                cross_body_shift_norm=cross_body_shift_norm,
                pelvis_jit=pelvis_jit, contact_frame=c, kicking_right=kr)


# ---------------------------------------------------------------- score
def score_trivela_technique(m):
    """m = measure_trivela_form output.

    All bands are STARTING POINTS from zero trivela-specific coach
    data -- re-calibrate against coach bands before locking, per
    the calibration policy. Same applies to combinations of these features, not
    just each threshold individually.
    """
    # HIP-FOOT DISSOCIATION: fault-gate on a LOW ratio (hip and foot
    # moved together, not a reward for one ideal amount of separation).
    dissociation = _band(m["dissociation_ratio"], lo_ok=0.0006, hi_ok=0.0015,
                          lo_fail=0.0001, hi_fail=0.0022)

    # INSIDE-OUT / CROSS-BODY SWING: crossing the midline at all is the
    # hard fault-gate (didn't wrap = not a real trivela); magnitude of
    # the crossing is the graded component on top of that.
    if m["crossed_midline"] is None:
        cross_body = 0.6  # not measurable this clip -- neutral, not a penalty
        cross_veto = 1.0
    else:
        cross_veto = 1.0 if m["crossed_midline"] else 0.55
        cross_body = _band(abs(m["cross_body_shift_norm"]), lo_ok=0.05, hi_ok=0.20,
                            lo_fail=0.0, hi_fail=0.35)

    # TIMING SEPARATION: reused gaps, WIDER bands than laces -- a more
    # delayed, independent foot action is the trivela signature here,
    # not a fault the way a big gap reads for laces.
    hip_knee_gap_score = _band(m["hip_to_knee_gap"], lo_ok=2, hi_ok=12, lo_fail=-4, hi_fail=18)
    knee_foot_gap_score = _band(m["knee_to_foot_gap"], lo_ok=2, hi_ok=10, lo_fail=-4, hi_fail=16)

    # BALANCE COMPENSATION on a compact backswing: same fault-gate
    # shape as laces' balance_jit.
    balance = _band(m["pelvis_jit"], lo_ok=0.0, hi_ok=0.014, lo_fail=-1, hi_fail=0.04)

    W = dict(dissociation=0.24, cross_body=0.20, hip_knee_gap=0.09,
              knee_foot_gap=0.09, balance=0.18, hip_timing=0.10, foot_timing=0.10)
    # hip/foot timing bands: same broad "kinetic chain is present"
    # check as laces/finesse, order-fault-gated below rather than
    # tightly banded -- trivela's dissociation feature already covers
    # WHERE the effort comes from, these just check it happens at all.
    hip_timing = _band(m["hip_peak_at"], lo_ok=-14, hi_ok=-4, lo_fail=-20, hi_fail=0)
    foot_timing = _band(m["foot_peak_at"], lo_ok=-5, hi_ok=0, lo_fail=-10, hi_fail=4)

    raw = (dissociation * W["dissociation"] + cross_body * W["cross_body"]
           + hip_knee_gap_score * W["hip_knee_gap"] + knee_foot_gap_score * W["knee_foot_gap"]
           + balance * W["balance"] + hip_timing * W["hip_timing"]
           + foot_timing * W["foot_timing"])

    order_veto = 0.65 if not m["chain_order_ok"] else 1.0  # out-of-order kinetic chain
    veto = order_veto * cross_veto
    linear = raw * veto * 100
    final = _compress_top(linear)

    return round(final, 1), dict(dissociation=dissociation, cross_body=cross_body,
                                 hip_knee_gap_score=hip_knee_gap_score,
                                 knee_foot_gap_score=knee_foot_gap_score,
                                 balance=balance, hip_timing=hip_timing,
                                 foot_timing=foot_timing, order_veto=order_veto,
                                 cross_veto=cross_veto, chain_order_ok=m["chain_order_ok"],
                                 crossed_midline=m["crossed_midline"])


def analyse_trivela_technique(video_path):
    """Convenience: measure + score in one call."""
    m = measure_trivela_form(video_path)
    if m is None:
        return None
    score, breakdown = score_trivela_technique(m)
    return dict(score=score, measured=m, breakdown=breakdown)
