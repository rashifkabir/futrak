import time
from backend.cv_engine.laces_technique   import analyse_laces_technique
from backend.cv_engine.finesse_technique import analyse_finesse_technique
from backend.cv_engine.trivela_technique import analyse_trivela_technique
from backend.cv_engine.ball_detector     import BallDetector

ANALYSERS = {
    "laces":   analyse_laces_technique,
    "finesse": analyse_finesse_technique,
    "trivela": analyse_trivela_technique,
}


def run_shooting_analysis(
    video_path: str,
    shot_type:  str,
    condition:  str = "static",
) -> dict:
    """
    Full shooting analysis pipeline. Dispatches to the canonical
    fault-gate scorer for the declared shot type (laces_technique.py
    is the reference implementation; finesse/trivela share its
    helpers). Technique and power are returned separately — never
    averaged into one hidden score.
    """
    start_time = time.time()

    result = ANALYSERS[shot_type](video_path)

    if result is None:
        return {
            "success": False,
            "error":   "Could not find ball contact or extract pose — "
                       "ensure the full kicking motion and body are "
                       "visible throughout the video"
        }

    measured = result["measured"]

    power_grade    = None
    power_speed_kmh = None
    if condition == "static":
        detector = BallDetector()
        detections, fps = detector.track_shot_only(video_path)
        power_result = detector.estimate_power_score(
            detections, fps, contact_frame=measured["contact_frame"]
        )
        power_grade     = power_result["power_grade"]
        power_speed_kmh = power_result["speed_kmh"]

    processing_time = round(time.time() - start_time, 1)

    return {
        "success":         True,
        "shot_type":       shot_type,
        "condition":       condition,
        "kicking_foot":    "right" if measured["kicking_right"] else "left",
        "contact_frame":   measured["contact_frame"],
        "technique_score": result["score"],
        "measured":        measured,
        "breakdown":       result["breakdown"],
        "power_grade":     power_grade,
        "power_speed_kmh": power_speed_kmh,
        "processing_time": f"{processing_time}s"
    }
