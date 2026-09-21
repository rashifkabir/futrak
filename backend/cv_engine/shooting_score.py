"""
Combined SHOOTING SCORE for ProPath FC.

  shooting_score = 0.6 x technique  +  0.4 x power   (out of 100)

Honest by design:
  - technique comes from the user-stated-type coaching system
    (overall_score /10, scaled to /100)
  - power comes from the depth-normalized estimate (power_grade
    /100) with an angle-confidence flag carried through
  - if power is unavailable (ball tracking too sparse) -> falls
    back to technique-only with a clear note (no faked power)
  - if contact can't be found -> honest re-film message, no
    fake scores
  - the score is presented WITH its components + confidence, not
    as an opaque number
"""
import cv2
from backend.cv_engine.technique_coach import coach_technique
from backend.cv_engine.camera_motion import measure_camera_motion
from backend.cv_engine.ball_detector import BallDetector
from backend.cv_engine.contact_detector import (
    find_contact_frame_index, filter_foot_glued_optical_flow,
)
from backend.cv_engine.pose_extractor import extract_landmarks_from_video

TECHNIQUE_WEIGHT = 0.6
POWER_WEIGHT     = 0.4



def validate_player_presence(valid_frames, total_frames, contact_idx=None):
    """Reject clips where the player isn't visible enough to score.
    Returns None if OK, or a user-facing rejection message."""
    detected = len(valid_frames)
    if total_frames <= 0:
        return "The video couldn't be read. Please try a different file."
    rate = detected / total_frames
    # genuinely too few detections to analyse (brief presence /
    # mostly out of frame) — NOT a glitch (retry already handled
    # near-zero); this is real low presence.
    if rate < 0.40:
        return ("We couldn't see the player clearly enough to "
                "analyse this shot. Film with yourself fully in "
                "frame from run-up through follow-through, in good "
                "lighting, and try again.")
    # player must be visible AROUND the strike, not just elsewhere
    if contact_idx is not None:
        # contact_idx is an index into valid_frames; check there's
        # continuous coverage near it (valid_frames are the
        # DETECTED ones, so a gap shows as a frame-number jump)
        i = contact_idx
        lo = valid_frames[max(0, i - 5)]["frame"]
        hi = valid_frames[min(len(valid_frames) - 1, i + 5)]["frame"]
        # if the window around contact spans far more frames than
        # the ~10 detected points it should, the player was missing
        # through the strike
        if (hi - lo) > 40:
            return ("We lost sight of the player during the strike. "
                    "Keep yourself fully in frame through the whole "
                    "shot and try again.")
    return None


def analyse_shot(video_path, shot_type, kicking_right=True):
    """Full shooting analysis: technique + power -> combined score."""

    # ── 0. VALIDATE player presence FIRST (clear, specific
    #    rejection before any scoring is attempted). ──
    _frames = extract_landmarks_from_video(video_path, draw_skeleton=False)
    if _frames is None:
        return {"error": "The video couldn't be read. Please try a "
                "different file."}
    _valid = [f for f in _frames if f["landmarks"] is not None]
    _cap = cv2.VideoCapture(video_path)
    _tot = int(_cap.get(cv2.CAP_PROP_FRAME_COUNT)); _cap.release()
    _reject = validate_player_presence(_valid, _tot, None)
    if _reject:
        return {"error": _reject}

    # ── Camera-motion gate: require a static camera ──
    _motion = measure_camera_motion(video_path)
    if not _motion["ok"]:
        return {"error": _motion["reason"]}

    # ── 1. Technique coaching (does its own pose+contact) ──
    tech = coach_technique(video_path, shot_type, kicking_right)
    if "error" in tech:
        return {"error": tech["error"]}

    technique_10  = tech["overall_score"]
    technique_100 = round(technique_10 * 10, 1) if technique_10 is not None else None

    # ── 2. Power (shares the same pose+ball+contact pipeline) ──
    det = BallDetector()
    dets, fps = det.track_shot_only(video_path)
    frames = extract_landmarks_from_video(video_path, draw_skeleton=False)
    valid = [f for f in frames if f["landmarks"] is not None]
    cap = cv2.VideoCapture(video_path)
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    dets = filter_foot_glued_optical_flow(valid, dets, W, H)
    # ── Validation gate: reject clips where the player isn't
    #    visible enough to analyse honestly. ──
    cap2 = cv2.VideoCapture(video_path)
    _total = int(cap2.get(cv2.CAP_PROP_FRAME_COUNT)); cap2.release()
    res = find_contact_frame_index(valid, dets, video_path)
    contact_idx = res[0] if (res is not None and not isinstance(res, dict)) else None
    reject = validate_player_presence(valid, _total, contact_idx)
    if reject:
        return {"error": reject}
    power = {"power_grade": None}
    if res is not None and not isinstance(res, dict):
        contact = valid[res[0]]["frame"]
        power = det.estimate_power_score(dets, fps, contact_frame=contact)
    power_100 = power.get("power_grade")

    # ── 3. Combine 60/40 (honest fallbacks) ──
    if technique_100 is not None and power_100 is not None:
        combined = round(TECHNIQUE_WEIGHT * technique_100 +
                         POWER_WEIGHT * power_100)
        basis = "technique + power"
        note = None
    elif technique_100 is not None:
        # power unavailable -> technique-only, honest note
        combined = round(technique_100)
        basis = "technique only"
        note = ("Power couldn't be measured (ball tracking too "
                "sparse) — score reflects technique only.")
    else:
        return {"error": "Could not score this shot."}

    return {
        "shooting_score": combined,           # /100, the headline
        "basis": basis,
        "components": {
            "technique": technique_100,        # /100 (60% weight)
            "power": power_100,                # /100 (40% weight)
        },
        "weights": {"technique": TECHNIQUE_WEIGHT, "power": POWER_WEIGHT},
        "shot_type": tech["shot_label"],
        # power detail (honest confidence carried through)
        "power_range": power.get("power_range"),
        "power_confidence": power.get("angle_confidence"),
        "power_note": power.get("power_note"),
        "speed_kmh_approx": power.get("speed_kmh"),
        # technique detail for the coaching layer
        "technique_scores": tech.get("scores"),
        "coaching_notes": tech.get("coaching_notes"),
        "coaching_focus": tech.get("coaching_focus"),
        "not_measured": tech.get("not_measured"),
        "fallback_note": note,
    }
