import numpy as np


# ─────────────────────────────────────────
# LANDMARK HELPERS
# ─────────────────────────────────────────

def get_coords(landmarks: dict, index: int):
    if index not in landmarks:
        return None
    lm = landmarks[index]
    if lm["visibility"] < 0.7:
        return None
    return (lm["x"], lm["y"])


def calculate_angle(a, b, c) -> float | None:
    if a is None or b is None or c is None:
        return None
    a = np.array(a)
    b = np.array(b)
    c = np.array(c)
    ba     = a - b
    bc     = c - b
    cosine = np.dot(ba, bc) / (
        np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6
    )
    cosine = np.clip(cosine, -1.0, 1.0)
    return round(np.degrees(np.arccos(cosine)), 1)


# ─────────────────────────────────────────
# CAMERA ANGLE VALIDATOR
# ─────────────────────────────────────────

def check_camera_angle(landmarks: dict,
                       mode: str = "shooting") -> dict:
    """
    Validates camera position for three filming modes.
    mode: "shooting" | "finishing" | "combined"
    """
    left_shoulder  = landmarks.get(11)
    right_shoulder = landmarks.get(12)
    left_hip       = landmarks.get(23)
    right_hip      = landmarks.get(24)
    left_ankle     = landmarks.get(27)
    right_ankle    = landmarks.get(28)

    required = [left_shoulder, right_shoulder,
                left_hip, right_hip]
    if not all(required):
        return {
            "valid":      False,
            "reason":     "Could not detect full body — "
                          "make sure your whole body is "
                          "in frame from head to toe",
            "confidence": 0.0
        }

    shoulder_x_gap = abs(
        left_shoulder["x"] - right_shoulder["x"]
    )
    hip_x_gap = abs(
        left_hip["x"] - right_hip["x"]
    )

    if mode == "shooting":
        if shoulder_x_gap < 0.04:
            return {
                "valid":      False,
                "reason":     "Camera appears to be directly "
                              "in front or behind — "
                              "please film from the side",
                "confidence": 0.0
            }
        if hip_x_gap > 0.01:
            ratio = shoulder_x_gap / hip_x_gap
            if ratio > 2.5:
                return {
                    "valid":      False,
                    "reason":     "Camera angle too diagonal — "
                                  "rotate to face your side directly",
                    "confidence": 0.3
                }
            if ratio < 0.4:
                return {
                    "valid":      False,
                    "reason":     "Camera angle too diagonal — "
                                  "film strictly side-on at 4-5m",
                    "confidence": 0.3
                }
        if left_ankle and right_ankle:
            avg_ankle_y = (
                left_ankle["y"] + right_ankle["y"]
            ) / 2
            if avg_ankle_y < 0.65:
                return {
                    "valid":      False,
                    "reason":     "Camera too high — place at "
                                  "shin to knee height",
                    "confidence": 0.4
                }
        if shoulder_x_gap < 0.08:
            return {
                "valid":      False,
                "reason":     "Too far from camera — "
                              "move to 4-5 metres away",
                "confidence": 0.5
            }
        ideal_gap  = 0.20
        gap_diff   = abs(shoulder_x_gap - ideal_gap)
        confidence = round(max(0.6, 1.0 - (gap_diff * 3)), 2)
        return {
            "valid":      True,
            "reason":     "Camera angle looks good",
            "confidence": confidence
        }

    elif mode == "finishing":
        if shoulder_x_gap > 0.15:
            return {
                "valid":      False,
                "reason":     "Too side-on for finishing — "
                              "goal zones may be unclear",
                "confidence": 0.0
            }
        return {"valid": True, "confidence": 1.0}

    elif mode == "combined":
        if 0.08 <= shoulder_x_gap <= 0.18:
            return {
                "valid":              True,
                "confidence":         0.75,
                "technique_warning":  "Technique at reduced "
                                      "accuracy — diagonal angle",
                "finishing_warning":  "Near/far post placement "
                                      "may be less precise"
            }
        return {
            "valid":  False,
            "reason": "Angle not suitable for combined analysis — "
                      "try 50-55° from the side"
        }

    return {"valid": True, "confidence": 1.0}


# ─────────────────────────────────────────
# SHOOTING ANGLE EXTRACTION
# ─────────────────────────────────────────

def extract_shooting_angles(landmarks: dict) -> dict:
    left_hip       = get_coords(landmarks, 23)
    right_hip      = get_coords(landmarks, 24)
    left_knee      = get_coords(landmarks, 25)
    right_knee     = get_coords(landmarks, 26)
    left_ankle     = get_coords(landmarks, 27)
    right_ankle    = get_coords(landmarks, 28)
    left_shoulder  = get_coords(landmarks, 11)
    right_shoulder = get_coords(landmarks, 12)

    hip_mid = None
    if left_hip and right_hip:
        hip_mid = (
            (left_hip[0] + right_hip[0]) / 2,
            (left_hip[1] + right_hip[1]) / 2
        )

    shoulder_mid = None
    if left_shoulder and right_shoulder:
        shoulder_mid = (
            (left_shoulder[0] + right_shoulder[0]) / 2,
            (left_shoulder[1] + right_shoulder[1]) / 2
        )

    vertical_ref = None
    if hip_mid:
        vertical_ref = (hip_mid[0], hip_mid[1] - 0.1)

    return {
        "knee_bend_right":        calculate_angle(
            right_hip, right_knee, right_ankle
        ),
        "knee_bend_left":         calculate_angle(
            left_hip, left_knee, left_ankle
        ),
        "body_lean":              calculate_angle(
            vertical_ref, hip_mid, shoulder_mid
        ),
        "hip_shoulder_alignment": calculate_angle(
            left_hip, hip_mid, shoulder_mid
        ) if left_hip and hip_mid and shoulder_mid else None,
    }


# ─────────────────────────────────────────
# ANKLE ANGLE EXTRACTION
# ─────────────────────────────────────────

def extract_ankle_angle(landmarks: dict,
                        kicking_foot: str = "right") -> float | None:
    """
    Measures ankle dorsiflexion of the kicking foot.
    Distinguishes power (extended), finesse (partial),
    knuckleball/toe-poke (locked/perpendicular).
    """
    if kicking_foot == "right":
        knee       = get_coords(landmarks, 26)
        ankle      = get_coords(landmarks, 28)
        foot_index = get_coords(landmarks, 32)
    else:
        knee       = get_coords(landmarks, 25)
        ankle      = get_coords(landmarks, 27)
        foot_index = get_coords(landmarks, 31)

    return calculate_angle(knee, ankle, foot_index)


# ─────────────────────────────────────────
# FOLLOW-THROUGH MEASUREMENT
# ─────────────────────────────────────────

def measure_follow_through(
    pre_contact_landmarks: dict,
    post_contact_landmarks: dict,
    kicking_foot: str = "right",
    all_frames: list = None,
    contact_idx: int = None
) -> float | None:
    """
    Measures maximum upward ankle movement after contact.

    If all_frames and contact_idx provided, looks up to
    5 frames ahead for maximum follow-through — much more
    reliable than single frame comparison.

    Falls back to single frame if extra data not available.
    """
    ankle_idx = 28 if kicking_foot == "right" else 27

    # Extended window — look up to 5 frames after contact
    if all_frames is not None and contact_idx is not None:
        pre_ankle = get_coords(
            pre_contact_landmarks, ankle_idx
        )
        if pre_ankle is None:
            return None

        max_movement = 0.0
        look_ahead   = min(
            contact_idx + 6, len(all_frames) - 1
        )

        for i in range(contact_idx + 1, look_ahead):
            f = all_frames[i]
            if f["landmarks"] is None:
                continue
            post_ankle = get_coords(f["landmarks"], ankle_idx)
            if post_ankle is None:
                continue
            # Y decreases going up — positive = upward movement
            movement = pre_ankle[1] - post_ankle[1]
            if movement > max_movement:
                max_movement = movement

        return round(max_movement, 3) if max_movement > 0 else 0.0

    # Fallback — single frame comparison
    pre_ankle  = get_coords(pre_contact_landmarks,  ankle_idx)
    post_ankle = get_coords(post_contact_landmarks, ankle_idx)

    if pre_ankle is None or post_ankle is None:
        return None

    return round(pre_ankle[1] - post_ankle[1], 3) 


# ─────────────────────────────────────────
# SHOT TYPE CLASSIFIER
# ─────────────────────────────────────────

def classify_shot_type(
    contact_angles: dict,
    ankle_angle:    float | None = None,
    follow_through: float | None = None
) -> dict:
    """
    Classifies shot type across 7 categories using
    weighted voting across all available signals.

    None values never contribute votes.
    Open body alignment dominates finesse detection.
    Ankle angle differentiates power/knuckleball/toe-poke.
    Extreme lean identifies low driven.
    """
    lean      = contact_angles.get("body_lean")
    alignment = contact_angles.get("hip_shoulder_alignment")

    signals = {}
    votes   = {
        "Power / Laces":  0,
        "Finesse":        0,
        "Power Curl":     0,
        "Low Driven":     0,
        "Toe-poke":       0,
        "Knuckleball":    0,
        "Standard Drive": 0
    }

    # ── Signal 1: Hip-shoulder alignment ────────────
    if alignment is not None:
        if alignment > 85:
            votes["Power Curl"] += 3
            votes["Finesse"]    += 2
            signals["alignment"] = (
                f"very open body ({alignment}°) → "
                f"power curl / finesse"
            )
        elif alignment > 40:
            votes["Power Curl"] += 2
            signals["alignment"] = (
                f"open body ({alignment}°) → power curl"
            )
        elif alignment > 20:
            votes["Finesse"] += 5
            signals["alignment"] = (
                f"open body ({alignment}°) → strong finesse"
            )
        elif alignment < 10:
            votes["Power / Laces"] += 1
            votes["Knuckleball"]   += 1
            votes["Low Driven"]    += 1
            signals["alignment"] = "closed body → power/knuckleball/driven"
        else:
            votes["Standard Drive"] += 1
            signals["alignment"]     = "neutral body"

    # ── Signal 2: Body lean ──────────────────────────
    if lean is not None:
        if lean > 18:
            votes["Low Driven"] += 4
            signals["body_lean"] = (
                f"extreme forward lean ({lean}°) → low driven"
            )
        elif lean > 5:
            # Don't vote low driven if alignment says open body
            if alignment is not None and alignment > 30:
                votes["Power Curl"]    += 1
                signals["body_lean"]    = (
                    "lean present — consistent with power curl"
                )
            else:
                votes["Power / Laces"] += 2
                votes["Standard Drive"] += 1
                signals["body_lean"]    = (
                    "forward lean → power/standard"
                )
        elif -3 <= lean <= 5:
            if alignment is not None and alignment > 40:
                signals["body_lean"] = (
                    "upright — consistent with finesse/curl"
                )
            else:
                votes["Knuckleball"] += 1
                signals["body_lean"] = (
                    "upright → knuckleball tendency"
                )
        else:
            signals["body_lean"] = "slight lean back — neutral"

    # ── Signal 3: Ankle angle ────────────────────────
    if ankle_angle is not None:
        body_is_open = alignment is not None and alignment > 30

        # Toe-poke: very low ankle regardless of body position
        if ankle_angle < 65:
            votes["Toe-poke"] += 5
            signals["ankle"] = (
                f"very low ankle ({ankle_angle}°) → toe-poke"
            )

        elif ankle_angle < 92:
            # Overlap between toe-poke and knuckleball
            # Use body lean and alignment to differentiate
            if lean is not None and -3 <= lean <= 5 and (
                alignment is None or alignment < 15
            ):
                votes["Knuckleball"] += 3
                signals["ankle"]      = (
                    f"locked ankle ({ankle_angle}°) → knuckleball"
                )
            else:
                votes["Toe-poke"] += 2
                signals["ankle"]   = (
                    f"low ankle ({ankle_angle}°) → toe-poke tendency"
                )

        elif ankle_angle < 120:
            if body_is_open:
                votes["Power Curl"] += 2
                signals["ankle"]     = (
                    f"ankle at {ankle_angle}° — "
                    f"consistent with power curl"
                )
            else:
                votes["Knuckleball"] += 3
                signals["ankle"]      = (
                    f"perpendicular ankle ({ankle_angle}°) → "
                    f"knuckleball"
                )

        elif ankle_angle < 150:
            if body_is_open:
                signals["ankle"] = (
                    f"ankle at {ankle_angle}° — "
                    f"normal for inside foot finesse"
                )
            else:
                votes["Standard Drive"] += 1
                signals["ankle"]         = "neutral ankle"

        else:
            # Fully extended — power or low driven
            votes["Power / Laces"] += 2
            votes["Low Driven"]    += 1
            signals["ankle"]        = (
                f"fully extended ankle ({ankle_angle}°) → power"
            )

    # ── Signal 4: Follow-through ─────────────────────
    if follow_through is not None:
        body_is_open = alignment is not None and alignment > 30

        if follow_through > 0.15:
            votes["Power / Laces"] += 2
            votes["Power Curl"]    += 1
            signals["follow_through"] = (
                "high follow-through → power"
            )

        elif follow_through > 0.08:
            if body_is_open:
                votes["Finesse"]   += 1
                votes["Power Curl"] += 1
                signals["follow_through"] = (
                    "moderate follow-through — finesse/curl"
                )
            else:
                votes["Standard Drive"] += 1
                signals["follow_through"] = "moderate follow-through"

        elif follow_through >= 0:
            if body_is_open:
                signals["follow_through"] = (
                    "short follow-through — "
                    "consistent with finesse/curl"
                )
            else:
                votes["Knuckleball"] += 2
                votes["Toe-poke"]    += 2
                signals["follow_through"] = (
                    "very short follow-through → "
                    "knuckleball or toe-poke"
                )

        else:
            # Negative = ankle moved downward
            votes["Low Driven"] += 2
            signals["follow_through"] = (
                "downward follow-through → low driven"
            )

    else:
        signals["follow_through"] = "not measured — no vote cast"

    # ── Pick winner ──────────────────────────────────
    if not any(votes.values()):
        return {
            "type":       "Standard Drive",
            "confidence": 0.5,
            "signals":    signals
        }

    shot_type   = max(votes, key=votes.get)
    total_votes = sum(votes.values())
    confidence  = round(votes[shot_type] / total_votes, 2)

    # Low confidence fallback
    if confidence < 0.40:
        shot_type  = "Standard Drive"
        confidence = 0.40

    return {
        "type":       shot_type,
        "confidence": confidence,
        "signals":    signals
    }
    