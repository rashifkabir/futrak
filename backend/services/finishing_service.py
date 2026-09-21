import time
from backend.cv_engine.goal_detector    import GoalDetector
from backend.cv_engine.finishing_analyser import FinishingAnalyser
from backend.cv_engine.ball_detector    import BallDetector
from backend.cv_engine.ai_feedback      import generate_ai_feedback


def run_finishing_analysis(
    video_path:       str,
    player_height_cm: float = 170.0
) -> dict:
    """
    Full finishing analysis pipeline.

    1. Detect goal in video
    2. Track ball across video
    3. Analyse each attempt
    4. Calculate finishing scores
    5. Generate AI feedback

    Returns complete finishing result ready for JSON response.
    """
    start_time = time.time()

    # ── Step 1: Detect goal ──────────────────
    print("Step 1: Detecting goal...")
    goal_detector = GoalDetector()
    goal_result   = goal_detector.find_goal_in_video(
        video_path, player_height_cm
    )

    if not goal_result.get("detected"):
        return {
            "success":           False,
            "finishing_available": False,
            "error": goal_result.get(
                "reason",
                "No goal detected in video"
            )
        }

    print(f"Goal: {goal_result['goal_type']}")
    if goal_result.get("goalkeeper", {}).get("present"):
        print("Goalkeeper detected — trajectory "
              "extrapolation enabled")

    # ── Step 2: Track ball ───────────────────
    print("Step 2: Tracking ball...")
    ball_detector   = BallDetector()
    detections, fps = ball_detector.track_shot_only(video_path)

    # ── Step 3: Analyse attempt ──────────────
    print("Step 3: Analysing finishing attempt...")
    analyser = FinishingAnalyser()
    attempt  = analyser.analyse_attempt(
        ball_detections  = detections,
        goal_result      = goal_result,
        fps              = fps,
        player_height_cm = player_height_cm
    )

    if attempt.get("error"):
        return {
            "success":           False,
            "finishing_available": True,
            "error":             attempt["error"],
            "goal_type":         goal_result.get("goal_type")
        }

    # ── Step 4: Calculate finishing score ────
    accuracy  = attempt.get("accuracy_score", 0) or 0
    placement = attempt.get("placement_score", 0) or 0

    # Only average with placement if on target
    if attempt["outcome"] in ("goal", "saved",
                               "woodwork_in"):
        finishing_score = round((accuracy + placement) / 2)
    else:
        finishing_score = 0

    # ── Step 5: AI feedback ──────────────────
    print("Step 5: Generating AI feedback...")
    feedback_prompt = {
        "shot_type":      "Finishing",
        "contact_angles": {},
        "ankle_angle":    None,
        "follow_through": None,
        "power_grade":    None
    }
    ai_feedback = _generate_finishing_feedback(attempt)

    processing_time = round(time.time() - start_time, 1)

    return {
        "success":             True,
        "finishing_available": True,
        "goal_type":           goal_result["goal_type"],
        "goal_width_m":        goal_result.get("goal_width_m"),
        "goal_height_m":       goal_result.get("goal_height_m"),
        "goalkeeper_present":  goal_result.get(
                                   "goalkeeper", {}
                               ).get("present", False),
        "outcome":             attempt["outcome"],
        "accuracy_score":      accuracy,
        "zone":                attempt.get("zone"),
        "placement_score":     placement,
        "finishing_score":     finishing_score,
        "grade_label":         _grade_label(finishing_score),
        "woodwork":            attempt.get("woodwork", False),
        "woodwork_type":       attempt.get("woodwork_type"),
        "goalkeeper_saved":    attempt.get("goalkeeper_saved"),
        "trajectory_extrapolated": attempt.get(
                                       "trajectory_extrapolated"
                                   ),
        "notes":               attempt.get("notes", ""),
        "ai_feedback":         ai_feedback,
        "processing_time":     f"{processing_time}s"
    }


def _generate_finishing_feedback(attempt: dict) -> str:
    """Generates finishing-specific AI feedback."""
    outcome   = attempt.get("outcome", "off_target")
    zone      = attempt.get("zone",    "unknown")
    placement = attempt.get("placement_score", 0) or 0

    feedback_map = {
        "goal": (
            f"Goal — {zone} zone. "
            f"Placement score {placement}/100. "
            f"{'Excellent corner finish — very hard to save.' if 'L' in zone or 'R' in zone else 'Good finish — work on hitting the corners more consistently.'}"
        ),
        "saved": (
            f"On target but saved. Zone: {zone}. "
            f"{'The goalkeeper made a good save — your placement was decent.' if placement > 55 else 'Try to aim for the corners — central shots are easier for goalkeepers to save.'}"
        ),
        "off_target": (
            "Off target. Focus on picking your spot before "
            "striking — decide where you're placing it before "
            "your approach."
        ),
        "woodwork_in": (
            f"Post and in — great result. Zone: {zone}. "
            "The woodwork counts if it crosses the line."
        ),
        "woodwork_out": (
            "Hit the woodwork — unlucky but this often means "
            "you're aiming for the right areas. Adjust your aim "
            "slightly inside the post."
        )
    }

    return feedback_map.get(
        outcome,
        "Keep working on your finishing consistency."
    )


def _grade_label(score: int) -> str:
    if score >= 88:
        return "Clinical"
    elif score >= 75:
        return "Sharp"
    elif score >= 60:
        return "Developing"
    elif score >= 45:
        return "Inconsistent"
    else:
        return "Needs Work" 