"""
Technique coaching for ProPath FC.

The USER STATES the shot type (auto-classification from single-
camera 2D proved unreliable — features overlap across types).
Given the stated type, we SCORE EXECUTION on the 2D features
that DO track reliably, and compare to per-type coaching
TARGETS (grounded in coaching principles, not statistically-
validated thresholds — refinable as more data is gathered).

Honest by design: we score only what we can measure reliably
(follow-through, swing path, foot speed, approach angle,
stability). Things a single side-camera can't capture (exact
foot contact surface, true 3D body lean) are flagged as
approximate or omitted, never faked.
"""
import math
import numpy as np
from backend.cv_engine.pose_extractor import extract_landmarks_from_video
from backend.cv_engine.angle_calculator import get_coords
from backend.cv_engine.ball_detector import BallDetector
from backend.cv_engine.contact_detector import (
    find_contact_frame_index, filter_foot_glued_optical_flow,
)
import cv2

SHOT_TYPES = ["laces", "knuckleball", "inside_curl",
              "finesse", "trivela", "chip", "toepoke"]

# ── Per-type coaching TARGETS (sensible defaults, NOT validated
#    thresholds). Each is a target/direction for the measurable
#    features, grounded in coaching principles. Scoring measures
#    closeness to these ideals for the USER-STATED type. ──
# Values are normalized where noted; px features scaled by the
# player's leg length (hip->ankle) so they're camera-distance
# independent.
TYPE_TARGETS = {
    "laces": {
        "label": "Laces / Instep Drive (power)",
        "follow_len": "long",        # drive through
        "follow_wrap": "low",        # relatively straight
        "foot_speed": "high",        # power
        "swing_curve": "low",        # straight into ball
        "approach": "direct",        # fairly straight run-up
        "focus": "Power and a clean, driving follow-through straight through the ball.",
    },
    "knuckleball": {
        "label": "Knuckleball",
        "follow_len": "medium",
        "follow_wrap": "low",        # minimal wrap = no spin
        "foot_speed": "high",
        "swing_curve": "low",
        "approach": "direct",
        "focus": "Firm, flat contact with minimal follow-through wrap to kill the spin.",
    },
    "inside_curl": {
        "label": "Inside Curl (everyday)",
        "follow_len": "medium",
        "follow_wrap": "medium",     # some wrap
        "foot_speed": "medium",
        "swing_curve": "medium",
        "approach": "slight_angle",
        "focus": "Wrap across the ball with the inside of the boot for curl; angle your approach a little.",
    },
    "finesse": {
        "label": "Finesse (instep curl)",
        "follow_len": "long",
        "follow_wrap": "high",       # wraps across the body
        "foot_speed": "medium",      # controlled, not max
        "swing_curve": "high",       # curved swing
        "approach": "angled",        # needs an angled run for curl
        "focus": "Angled approach, controlled pace, and a full wrap across the body to generate curl.",
    },
    "trivela": {
        "label": "Trivela (outside foot)",
        "follow_len": "long",
        "follow_wrap": "high",
        "foot_speed": "medium",
        "swing_curve": "high",
        "approach": "angled",
        "focus": "Angled approach and outside-of-boot contact with a wrapping follow-through for the reverse curl.",
    },
    "toepoke": {
        "label": "Toe-poke",
        "follow_len": "short",
        "follow_wrap": "low",
        "foot_speed": "medium",
        "swing_curve": "low",
        "approach": "direct",
        "focus": "A toe-poke is a last-resort jab — for a proper strike, "
                 "use your laces or inside foot with a fuller swing and "
                 "follow-through. It sacrifices power, accuracy and spin.",
        "penalty_cap": 4.0,   # toe-pokes are capped low (poor technique)
    },
    "chip": {
        "label": "Chip",
        "follow_len": "short",       # short stab
        "follow_wrap": "low",
        "foot_speed": "low",         # not power
        "swing_curve": "low",
        "approach": "direct",
        "focus": "Get under the ball with a short, stabbing motion and lean back slightly to lift it.",
    },
}

# qualitative band -> numeric centre (normalized by leg length
# for px features; degrees for angles). Coaching defaults.
# Calibrated from clean reference clips (real measured ranges):
#   laces follow ~0.4-0.75, finesse ~0.55-1.12, trivela ~1.0-1.2
#   speeds ~0.08-0.14 (low variance), wrap erratic (down-weighted)
_BANDS_FOLLOW = {"short": 0.45, "medium": 0.85, "long": 1.15}  # x leg-length
_BANDS_WRAP   = {"low": 0.25, "medium": 0.35, "high": 0.45}    # lateral ratio (noisy)
_BANDS_SPEED  = {"low": 0.08, "medium": 0.11, "high": 0.15}    # x leg-length /frame
_BANDS_CURVE  = {"low": 25, "medium": 35, "high": 45}          # degrees
_BANDS_APPR   = {"direct": 60, "slight_angle": 70, "angled": 80}  # degrees (real run-ups 65-89)


def _ang(dx, dy):
    return math.degrees(math.atan2(dy, dx))

def _sdiff(a, b):
    d = a - b
    while d > 180: d -= 360
    while d < -180: d += 360
    return d


def coach_technique(video_path, shot_type, kicking_right=True):
    shot_type = shot_type.lower().strip()
    if shot_type not in TYPE_TARGETS:
        return {"error": f"unknown shot_type '{shot_type}'. "
                f"Choose one of: {', '.join(SHOT_TYPES)}"}

    cap = cv2.VideoCapture(video_path)
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()

    frames = extract_landmarks_from_video(video_path, draw_skeleton=False)
    valid = [f for f in frames if f["landmarks"] is not None]
    if len(valid) < 5:
        return {"error": "Not enough pose data — ensure the player "
                "is clearly visible throughout the clip."}
    lm_by = {f["frame"]: f["landmarks"] for f in valid}

    det = BallDetector()
    detections, fps = det.track_shot_only(video_path)
    detections = filter_foot_glued_optical_flow(valid, detections, W, H)
    ball_by = {d["frame"]: d["ball"] for d in detections if d.get("ball")}

    result = find_contact_frame_index(valid, detections, video_path)
    if result is None or isinstance(result, dict):
        return {"error": "Couldn't reliably find the contact moment "
                "(camera may have moved, or the strike isn't clearly "
                "visible). Re-film with a static camera, kicking-foot "
                "side, player and ball visible from run-up through "
                "follow-through, in slow motion."}
    contact_idx, kr_det = result
    contact = valid[contact_idx]["frame"]

    ankle_i = 28 if kicking_right else 27
    knee_i  = 26 if kicking_right else 25
    hip_i   = 24 if kicking_right else 23
    hip_o   = 23 if kicking_right else 24
    sho_i   = 12 if kicking_right else 11

    def pt(fn, idx):
        lm = lm_by.get(fn)
        if not lm: return None
        c = get_coords(lm, idx)
        return (c[0]*W, c[1]*H) if c else None
    def ankle(fn): return pt(fn, ankle_i)
    def ball(fn):
        b = ball_by.get(fn); return (b["cx"], b["cy"]) if b else None

    # leg length (hip->ankle near contact) to normalize px features
    leg_len = None
    for fn in range(contact-3, contact+3):
        h, a = pt(fn, hip_i), ankle(fn)
        if h and a:
            ll = ((h[0]-a[0])**2 + (h[1]-a[1])**2) ** 0.5
            if ll > 1: leg_len = ll; break
    if not leg_len or leg_len < 1:
        leg_len = H * 0.25   # fallback

    # ── MEASURE reliable features ──
    # FOLLOW-THROUGH over a LONG window (many frames post-contact)
    ft = [p for p in (ankle(fn) for fn in range(contact, contact+18)) if p]
    ft_len = sum(((ft[i][0]-ft[i-1][0])**2+(ft[i][1]-ft[i-1][1])**2)**0.5
                 for i in range(1,len(ft))) if len(ft)>=2 else 0
    ft_norm = ft_len / leg_len
    ft_wrap = (abs(ft[-1][0]-ft[0][0]) / ft_len) if (len(ft)>=2 and ft_len>1) else None

    # FOOT SPEED (peak ankle speed near contact), normalized
    sp = []
    for fn in range(contact-5, contact+5):
        a, b = ankle(fn), ankle(fn+1)
        if a and b: sp.append(((b[0]-a[0])**2+(b[1]-a[1])**2)**0.5)
    foot_speed = (max(sp)/leg_len) if sp else None

    # SWING CURVATURE (foot path bend through contact)
    arc = [p for p in (ankle(fn) for fn in range(contact-6, contact+7)) if p]
    swing_curve = None
    if len(arc) >= 6:
        m = len(arc)//2
        d1 = _ang(arc[m][0]-arc[0][0], arc[m][1]-arc[0][1])
        d2 = _ang(arc[-1][0]-arc[m][0], arc[-1][1]-arc[m][1])
        swing_curve = abs(_sdiff(d2, d1))

    # APPROACH ANGLE (run-up direction before the plant). The
    # run-up can start well before contact, so use a WIDER window
    # and a LOWER motion threshold. Direction of the mid-hip path
    # over the approach, measured off the straight-on (vertical)
    # axis. 0 = straight at goal, larger = angled run.
    appr = []
    for fn in range(contact-40, contact-3):
        h1, h2 = pt(fn, hip_i), pt(fn, hip_o)
        if h1 and h2:
            appr.append(((h1[0]+h2[0])/2, (h1[1]+h2[1])/2))
    approach_angle = None
    if len(appr) >= 5:
        # use overall run-up vector (first quarter -> last quarter)
        q = max(1, len(appr)//4)
        x0 = sum(p[0] for p in appr[:q])/q; y0 = sum(p[1] for p in appr[:q])/q
        x1 = sum(p[0] for p in appr[-q:])/q; y1 = sum(p[1] for p in appr[-q:])/q
        dx, dy = x1-x0, y1-y0
        if (dx*dx+dy*dy) ** 0.5 > leg_len*0.08:   # lower threshold
            approach_angle = abs(_sdiff(_ang(dx, dy), -90))
            if approach_angle > 90: approach_angle = 180 - approach_angle

    # STABILITY (mid-hip jitter pre-contact = balance proxy)
    hips = []
    for fn in range(contact-8, contact):
        h1, h2 = pt(fn, hip_i), pt(fn, hip_o)
        if h1 and h2: hips.append(((h1[0]+h2[0])/2, (h1[1]+h2[1])/2))
    stability = None
    if len(hips) >= 4:
        xs = [h[0] for h in hips]; ys = [h[1] for h in hips]
        jitter = (np.std(xs) + np.std(ys)) / leg_len
        stability = jitter   # lower = steadier

    measured = {
        "follow_through_norm": ft_norm,
        "follow_wrap_ratio": ft_wrap,
        "foot_speed_norm": foot_speed,
        "swing_curvature_deg": swing_curve,
        "approach_angle_deg": approach_angle,
        "hip_jitter_norm": stability,
        "contact_frame": contact,
        "leg_length_px": round(leg_len, 1),
    }

    # ── SCORE vs the stated type's targets ──
    tgt = TYPE_TARGETS[shot_type]
    scores = {}
    notes = []

    def score_close(value, target_centre, tol):
        # 0..10, 10 at target, falling off by distance/tol
        if value is None: return None
        d = abs(value - target_centre)
        return round(max(0.0, 10.0 * (1 - d / (tol*2))), 1)

    # follow-through length
    if ft_norm is not None:
        c = _BANDS_FOLLOW[tgt["follow_len"]]
        scores["follow_through"] = score_close(ft_norm, c, 0.7)
        if ft_norm < c*0.6:
            notes.append(("follow_through", "short",
                          f"Your follow-through is short for a {tgt['label']}. "
                          f"Swing through more after contact."))
        elif ft_norm > c*1.6 and tgt["follow_len"] == "short":
            notes.append(("follow_through", "long",
                          "A chip needs a short, stabbing motion — your "
                          "follow-through is too long."))

    # wrap / cross-body
    if ft_wrap is not None:
        c = _BANDS_WRAP[tgt["follow_wrap"]]
        scores["follow_wrap"] = score_close(ft_wrap, c, 0.25)
        if tgt["follow_wrap"] == "high" and ft_wrap < 0.35:
            notes.append(("follow_wrap", "low",
                          f"For a {tgt['label']}, wrap your leg across your "
                          f"body more after contact to generate curl."))
        if tgt["follow_wrap"] == "low" and ft_wrap > 0.45:
            notes.append(("follow_wrap", "high",
                          "Your follow-through is wrapping across the body; "
                          "for this shot, drive straighter through the ball."))

    # foot speed
    if foot_speed is not None:
        c = _BANDS_SPEED[tgt["foot_speed"]]
        scores["foot_speed"] = score_close(foot_speed, c, 0.12)
        if tgt["foot_speed"] == "high" and foot_speed < c*0.7:
            notes.append(("foot_speed", "low",
                          "More foot speed through contact for power."))

    # swing curvature
    if swing_curve is not None:
        c = _BANDS_CURVE[tgt["swing_curve"]]
        scores["swing_path"] = score_close(swing_curve, c, 22)

    # approach angle
    if approach_angle is not None:
        c = _BANDS_APPR[tgt["approach"]]
        scores["approach"] = score_close(approach_angle, c, 35)
        if tgt["approach"] == "angled" and approach_angle < 45:
            notes.append(("approach", "too_straight",
                          f"A {tgt['label']} needs an angled run-up to wrap "
                          f"around the ball — your approach was too straight-on."))

    # stability
    if stability is not None:
        # lower jitter = better; map to 0..10 (jitter ~0 -> 10)
        scores["balance"] = round(max(0.0, 10.0 * (1 - stability/0.12)), 1)
        if stability > 0.10:
            notes.append(("balance", "unsteady",
                          "Your base looks unsteady before contact — plant "
                          "your standing foot firmly for better balance."))

    # Weighted overall: follow-through is the most reliable
    # separator; wrap is noisy (down-weighted); speed/swing light.
    WEIGHTS = {"follow_through": 2.0, "balance": 1.5,
               "follow_wrap": 0.5, "foot_speed": 1.0,
               "swing_path": 1.0, "approach": 0.5}
    wsum = wtot = 0.0
    for k, s in scores.items():
        if s is not None:
            w = WEIGHTS.get(k, 1.0)
            wsum += s * w; wtot += w
    overall = round(wsum/wtot, 1) if wtot > 0 else None
    # Heavily penalize toe-pokes (poor technique) even if the
    # motion superficially resembles a laces shot.
    cap = TYPE_TARGETS[shot_type].get("penalty_cap")
    if cap is not None and overall is not None:
        overall = round(min(overall, cap), 1)

    # honest confidence flags — things we did NOT / cannot measure
    unmeasured = []
    if approach_angle is None:
        unmeasured.append("approach angle (player not visible / not moving "
                          "enough before contact)")
    unmeasured.append("exact foot contact surface (instep vs inside vs "
                      "outside) — not reliably visible from one camera")
    unmeasured.append("true 3D body lean — approximate only from a single view")

    return {
        "shot_type": shot_type,
        "shot_label": tgt["label"],
        "coaching_focus": tgt["focus"],
        "overall_score": overall,
        "scores": scores,
        "measured": measured,
        "coaching_notes": notes,        # (dimension, issue, advice)
        "not_measured": unmeasured,     # honest limitations
        "detected_kicking_foot": "right" if kr_det else "left",
    }
