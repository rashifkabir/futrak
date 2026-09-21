# ─────────────────────────────────────────
# OPTIMAL ANGLE RANGES PER SHOT TYPE
# ─────────────────────────────────────────

OPTIMAL_RANGES = {

    "Power / Laces": {
        "body_lean": {
            "min": 8, "max": 20,
            "low":  "Lean your body further over the ball — "
                    "staying upright causes the ball to rise",
            "high": "You're leaning too far forward — "
                    "you'll lose power and accuracy"
        },
        "knee_bend_right": {
            "min": 140, "max": 168,
            "low":  "Bend your standing knee slightly more — "
                    "a locked straight leg kills your balance",
            "high": "Your standing leg is too bent — "
                    "you need more stability through contact"
        },
        "knee_bend_left": {
            "min": 140, "max": 168,
            "low":  "Bend your standing knee slightly more — "
                    "a locked straight leg kills your balance",
            "high": "Your standing leg is too bent — "
                    "you need more stability through contact"
        },
        "hip_shoulder_alignment": {
            "min": 5, "max": 15,
            "low":  "Drive your hips through the ball first "
                    "before your leg follows — more hip rotation "
                    "generates more power",
            "high": "Your body is opening up too early — "
                    "stay square through the strike"
        },
        "ankle_angle": {
            "min": 150, "max": 180,
            "low":  "Extend and lock your ankle at contact — "
                    "a floppy foot loses all your power",
            "high": None
        },
        "follow_through": {
            "min": 0.15, "max": 1.0,
            "low":  "Drive your foot all the way through the ball "
                    "and finish high — your follow-through is too short",
            "high": None
        }
    },

    "Finesse": {
        "body_lean": {
            "min": 0, "max": 12,
            "low":  None,
            "high": "Stay more upright for finesse shots — "
                    "leaning forward reduces your ability to "
                    "wrap around the ball"
        },
        "hip_shoulder_alignment": {
            "min": 18, "max": 50,
            "low":  "Open your body more at contact — "
                    "point your standing foot and hips toward "
                    "the target to get side spin on the ball",
            "high": "You're opening up too much — "
                    "you'll lose accuracy and spin"
        },
        "ankle_angle": {
            "min": 130, "max": 160,
            "low":  "Keep your ankle firm through contact "
                    "even for a finesse shot",
            "high": "Relax your ankle slightly — "
                    "a fully locked ankle reduces your ability "
                    "to generate side spin"
        }
    },

    "Knuckleball": {
        "body_lean": {
            "min": -5, "max": 5,
            "low":  None,
            "high": "Stay upright or lean very slightly back — "
                    "leaning forward creates topspin which "
                    "kills the knuckling effect"
        },
        "ankle_angle": {
            "min": 85, "max": 125,
            "low":  "Lock your ankle completely stiff and keep "
                    "your foot perpendicular — this is the most "
                    "important part of the knuckleball technique",
            "high": "Your foot is too pointed — "
                    "keep it flat and perpendicular to the ball, "
                    "not extended like a power shot"
        },
        "follow_through": {
            "min": 0.0, "max": 0.09,
            "low":  None,
            "high": "Cut your follow-through short — punch through "
                    "the ball and stop. A long follow-through "
                    "adds spin and removes the knuckling effect"
        },
        "hip_shoulder_alignment": {
            "min": 0, "max": 12,
            "low":  "Keep your body square and closed — "
                    "opening up adds unwanted spin",
            "high": None
        }
    },

    "Standard Drive": {
        "body_lean": {
            "min": 5, "max": 15,
            "low":  "Lean slightly over the ball to keep it down",
            "high": "Ease off the forward lean slightly"
        },
        "knee_bend_right": {
            "min": 140, "max": 168,
            "low":  "Bend your standing knee slightly for better balance",
            "high": "Standing leg too bent — straighten slightly"
        },
        "knee_bend_left": {
            "min": 140, "max": 168,
            "low":  "Bend your standing knee slightly for better balance",
            "high": "Standing leg too bent — straighten slightly"
        }
    }
}


# ─────────────────────────────────────────
# FEEDBACK GENERATOR
# ─────────────────────────────────────────

def generate_shot_feedback(shot_type: str,
                           contact_angles: dict,
                           ankle_angle: float | None = None,
                           follow_through: float | None = None
                           ) -> dict:
    """
    Generates specific coaching feedback for a shot based on
    which attributes are outside the optimal range for that shot type.

    Returns:
        {
            "shot_type":        classified shot type,
            "improvements":     list of specific coaching points,
            "strengths":        list of things done well,
            "priority":         the single most important fix,
            "overall_technique_grade": 0-100
        }
    """
    ranges = OPTIMAL_RANGES.get(shot_type, OPTIMAL_RANGES["Standard Drive"])

    improvements = []
    strengths    = []

    # Build a combined dict of all values to check
    all_values = dict(contact_angles)
    if ankle_angle is not None:
        all_values["ankle_angle"] = ankle_angle
    if follow_through is not None:
        all_values["follow_through"] = follow_through

    attributes_scored = []

    for attr, thresholds in ranges.items():
        value = all_values.get(attr)

        if value is None:
            continue

        low_msg  = thresholds.get("low")
        high_msg = thresholds.get("high")
        min_val  = thresholds["min"]
        max_val  = thresholds["max"]

        if value < min_val and low_msg:
            improvements.append({
                "attribute": attr,
                "message":   low_msg,
                "severity":  round(
                    min((min_val - value) / min_val, 1.0), 2
                )
            })
            attributes_scored.append(
                max(0, 100 - int((min_val - value) / min_val * 100))
            )

        elif value > max_val and high_msg:
            improvements.append({
                "attribute": attr,
                "message":   high_msg,
                "severity":  round(
                    min((value - max_val) / max_val, 1.0), 2
                )
            })
            attributes_scored.append(
                max(0, 100 - int((value - max_val) / max_val * 100))
            )

        else:
            strengths.append(
                attr.replace("_", " ").title()
            )
            attributes_scored.append(100)

    # Sort improvements by severity — most important fix first
    improvements.sort(key=lambda x: x["severity"], reverse=True)

    # Priority = single most important fix
    priority = (
        improvements[0]["message"]
        if improvements
        else "Technique looks solid for this shot type — "
             "focus on consistency"
    )

    # Overall technique grade
    overall = (
        int(sum(attributes_scored) / len(attributes_scored))
        if attributes_scored else 50
    )

    return {
        "shot_type":              shot_type,
        "improvements":           [i["message"] for i in improvements],
        "strengths":              strengths,
        "priority":               priority,
        "overall_technique_grade": overall
    }