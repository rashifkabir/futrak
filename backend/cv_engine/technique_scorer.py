# ─────────────────────────────────────────────────────
# TECHNIQUE SCORER
# Starts at 100 and deducts points for each body
# mechanic that falls outside the optimal range.
# Deductions are proportional to how far off the angle
# is — small deviations lose few points, large
# deviations lose significantly more.
# ─────────────────────────────────────────────────────

# ─────────────────────────────────────────
# SHOT PROFILES
# Each attribute has:
#   optimal_min / optimal_max  → no deduction inside this range
#   max_deduction              → most points this attribute can cost
#   rate_per_unit              → points lost per degree/unit outside range
#   description                → what this attribute measures
# ─────────────────────────────────────────

# ─────────────────────────────────────────────────────
# TECHNIQUE SCORER
# Starts at 100 and deducts points for each body
# mechanic outside the optimal range for the shot type.
# ─────────────────────────────────────────────────────

SHOT_PROFILES = {

    "Power / Laces": {
        "body_lean": {
            "optimal_min":   8.0,
            "optimal_max":  20.0,
            "max_deduction": 22,
            "rate_per_unit":  1.4,
            "description":   "Body lean over ball"
        },
        "standing_knee": {
            "optimal_min":  140.0,
            "optimal_max":  168.0,
            "max_deduction": 15,
            "rate_per_unit":  0.9,
            "description":   "Standing leg knee bend"
        },
        "hip_shoulder_alignment": {
            "optimal_min":   5.0,
            "optimal_max":  18.0,
            "max_deduction": 20,
            "rate_per_unit":  1.2,
            "description":   "Hip-shoulder alignment"
        },
        "ankle_angle": {
            "optimal_min":  150.0,
            "optimal_max":  180.0,
            "max_deduction": 25,
            "rate_per_unit":  1.6,
            "description":   "Ankle extension at contact"
        },
        "follow_through": {
            "optimal_min":  0.15,
            "optimal_max":  1.00,
            "max_deduction": 18,
            "rate_per_unit": 80.0,
            "description":   "Follow-through height"
        }
    },

    "Finesse": {
        "body_lean": {
            "optimal_min":   0.0,
            "optimal_max":  12.0,
            "max_deduction": 15,
            "rate_per_unit":  1.0,
            "description":   "Upright body for finesse"
        },
        "standing_knee": {
            "optimal_min":  135.0,
            "optimal_max":  165.0,
            "max_deduction": 12,
            "rate_per_unit":  0.7,
            "description":   "Standing leg stability"
        },
        "hip_shoulder_alignment": {
            "optimal_min":  20.0,
            "optimal_max":  60.0,
            "max_deduction": 28,
            "rate_per_unit":  1.8,
            "description":   "Open body alignment"
        },
        "ankle_angle": {
            "optimal_min":  110.0,
            "optimal_max":  150.0,
            "max_deduction": 15,
            "rate_per_unit":  0.9,
            "description":   "Inside foot ankle position"
        },
        "follow_through": {
            "optimal_min":  0.08,
            "optimal_max":  0.20,
            "max_deduction": 20,
            "rate_per_unit": 100.0,
            "description":   "Controlled follow-through"
        }
    },

    "Power Curl": {
        "body_lean": {
            "optimal_min":   5.0,
            "optimal_max":  18.0,
            "max_deduction": 18,
            "rate_per_unit":  1.2,
            "description":   "Body lean for curl power"
        },
        "standing_knee": {
            "optimal_min":  138.0,
            "optimal_max":  168.0,
            "max_deduction": 14,
            "rate_per_unit":  0.9,
            "description":   "Standing leg stability"
        },
        "hip_shoulder_alignment": {
            "optimal_min":  40.0,
            "optimal_max":  85.0,
            "max_deduction": 22,
            "rate_per_unit":  1.3,
            "description":   "Open body for curl generation"
        },
        "ankle_angle": {
            "optimal_min":   95.0,
            "optimal_max":  135.0,
            "max_deduction": 20,
            "rate_per_unit":  1.4,
            "description":   "Ankle lock for spin contact"
        },
        "follow_through": {
            "optimal_min":  0.12,
            "optimal_max":  1.00,
            "max_deduction": 18,
            "rate_per_unit": 80.0,
            "description":   "Strong follow-through for power"
        }
    },

    "Low Driven": {
        # Extreme forward lean is the defining feature
        "body_lean": {
            "optimal_min":  18.0,
            "optimal_max":  35.0,
            "max_deduction": 25,
            "rate_per_unit":  1.6,
            "description":   "Extreme forward lean to keep ball low"
        },
        "standing_knee": {
            "optimal_min":  138.0,
            "optimal_max":  165.0,
            "max_deduction": 14,
            "rate_per_unit":  0.9,
            "description":   "Standing leg bend"
        },
        # Square body like power shot
        "hip_shoulder_alignment": {
            "optimal_min":   3.0,
            "optimal_max":  18.0,
            "max_deduction": 18,
            "rate_per_unit":  1.2,
            "description":   "Square body alignment"
        },
        # Fully extended ankle like power
        "ankle_angle": {
            "optimal_min":  145.0,
            "optimal_max":  180.0,
            "max_deduction": 22,
            "rate_per_unit":  1.5,
            "description":   "Extended ankle at contact"
        },
        # Moderate follow-through — not as high as power
        "follow_through": {
            "optimal_min":  0.06,
            "optimal_max":  0.18,
            "max_deduction": 16,
            "rate_per_unit": 90.0,
            "description":   "Controlled downward follow-through"
        }
    },

    "Toe-poke": {
        # Minimal lean — reaching not driving
        "body_lean": {
            "optimal_min":  -5.0,
            "optimal_max":  10.0,
            "max_deduction": 12,
            "rate_per_unit":  0.8,
            "description":   "Body position over ball"
        },
        # Standing leg can be more bent in reactive situations
        "standing_knee": {
            "optimal_min":  125.0,
            "optimal_max":  168.0,
            "max_deduction": 10,
            "rate_per_unit":  0.6,
            "description":   "Standing leg (reactive situations)"
        },
        # Alignment variable — not graded heavily
        "hip_shoulder_alignment": {
            "optimal_min":   0.0,
            "optimal_max":  90.0,
            "max_deduction": 10,
            "rate_per_unit":  0.5,
            "description":   "Body orientation"
        },
        # Toes pointing at ball — most critical
        "ankle_angle": {
            "optimal_min":  60.0,
            "optimal_max":  92.0,
            "max_deduction": 30,
            "rate_per_unit":  1.8,
            "description":   "Toe direction at contact"
        },
        # Very short follow-through is correct
        "follow_through": {
            "optimal_min":  0.0,
            "optimal_max":  0.05,
            "max_deduction": 20,
            "rate_per_unit": 150.0,
            "description":   "Short contact follow-through"
        }
    },

    "Knuckleball": {
        "body_lean": {
            "optimal_min":  -3.0,
            "optimal_max":   5.0,
            "max_deduction": 18,
            "rate_per_unit":  1.5,
            "description":   "Very upright body"
        },
        "standing_knee": {
            "optimal_min":  140.0,
            "optimal_max":  170.0,
            "max_deduction": 10,
            "rate_per_unit":  0.6,
            "description":   "Standing leg stability"
        },
        "hip_shoulder_alignment": {
            "optimal_min":   0.0,
            "optimal_max":  12.0,
            "max_deduction": 18,
            "rate_per_unit":  1.2,
            "description":   "Closed body alignment"
        },
        "ankle_angle": {
            "optimal_min":  85.0,
            "optimal_max":  120.0,
            "max_deduction": 30,
            "rate_per_unit":  2.0,
            "description":   "Locked perpendicular ankle"
        },
        "follow_through": {
            "optimal_min":  0.0,
            "optimal_max":  0.07,
            "max_deduction": 30,
            "rate_per_unit": 200.0,
            "description":   "Short punch follow-through"
        }
    },

    "Standard Drive": {
        "body_lean": {
            "optimal_min":   5.0,
            "optimal_max":  15.0,
            "max_deduction": 18,
            "rate_per_unit":  1.2,
            "description":   "Body lean"
        },
        "standing_knee": {
            "optimal_min":  140.0,
            "optimal_max":  168.0,
            "max_deduction": 14,
            "rate_per_unit":  0.9,
            "description":   "Standing leg bend"
        },
        "hip_shoulder_alignment": {
            "optimal_min":   5.0,
            "optimal_max":  20.0,
            "max_deduction": 16,
            "rate_per_unit":  1.0,
            "description":   "Body alignment"
        },
        "ankle_angle": {
            "optimal_min":  140.0,
            "optimal_max":  175.0,
            "max_deduction": 20,
            "rate_per_unit":  1.3,
            "description":   "Ankle extension"
        },
        "follow_through": {
            "optimal_min":  0.10,
            "optimal_max":  0.20,
            "max_deduction": 15,
            "rate_per_unit": 90.0,
            "description":   "Follow-through"
        }
    }
}


# ─────────────────────────────────────────
# DEDUCTION CALCULATOR
# ─────────────────────────────────────────

def calculate_deduction(value: float, config: dict) -> float:
    low  = config["optimal_min"]
    high = config["optimal_max"]
    rate = config["rate_per_unit"]
    cap  = config["max_deduction"]

    # Grace buffer scales proportionally to range width
    # Angle ranges (large): ~2-4° grace
    # Follow-through range (small): ~0.05-0.08 grace
    range_width  = high - low
    grace_buffer = range_width * 0.08

    buffered_low  = low  - grace_buffer
    buffered_high = high + grace_buffer

    if buffered_low <= value <= buffered_high:
        return 0.0

    deviation = (
        buffered_low - value if value < buffered_low
        else value - buffered_high
    )

    raw = rate * (deviation ** 0.60)
    return round(min(raw, cap), 1) 



# ─────────────────────────────────────────
# MAIN SCORING FUNCTION
# ─────────────────────────────────────────

def score_technique(
    shot_type:      str,
    contact_angles: dict,
    ankle_angle:    float | None,
    follow_through: float | None,
    kicking_foot:   str = "right"
) -> dict:
    """
    Scores shooting technique out of 100.
    Starts at 100 and deducts per mechanic outside
    the optimal range for the detected shot type.
    """
    profile = SHOT_PROFILES.get(
        shot_type,
        SHOT_PROFILES["Standard Drive"]
    )

    # Standing leg = opposite of kicking foot
    standing_knee = (
        contact_angles.get("knee_bend_left")
        if kicking_foot == "right"
        else contact_angles.get("knee_bend_right")
    )

    values = {
        "body_lean":              contact_angles.get("body_lean"),
        "standing_knee":          standing_knee,
        "hip_shoulder_alignment": contact_angles.get(
                                      "hip_shoulder_alignment"
                                  ),
        "ankle_angle":            ankle_angle,
        "follow_through":         follow_through
    }

    score            = 100.0
    deductions       = {}
    attribute_scores = {}
    missing          = []

    for attr, config in profile.items():
        value = values.get(attr)

        if value is None:
            missing.append(attr)
            continue

        deduction = calculate_deduction(value, config)
        score    -= deduction

        deductions[attr]       = deduction
        attribute_scores[attr] = round(
            max(0, config["max_deduction"] - deduction)
            / config["max_deduction"] * 100
        )

    final_score = max(0, min(100, round(score)))

    return {
        "technique_score":  final_score,
        "deductions":       deductions,
        "attribute_scores": attribute_scores,
        "attributes_used":  len(profile) - len(missing),
        "missing":          missing,
        "grade_label":      get_grade_label(final_score)
    }


# ─────────────────────────────────────────
# GRADE LABELS
# ─────────────────────────────────────────

def get_grade_label(score: int) -> str:
    if score >= 90:
        return "Elite"
    elif score >= 78:
        return "Advanced"
    elif score >= 65:
        return "Developing"
    elif score >= 50:
        return "Beginner"
    else:
        return "Needs Work"


# ─────────────────────────────────────────
# COMBINED SHOOTING SCORE
# ─────────────────────────────────────────

def calculate_shooting_score(
    technique_score: int,
    power_grade:     int | None
) -> dict:
    """
    Shooting Score = (technique + power) / 2
    Falls back to technique only if power unavailable.
    """
    if power_grade is not None:
        shooting_score = round(
            (technique_score + power_grade) / 2
        )
        components = {
            "technique": technique_score,
            "power":     power_grade
        }
    else:
        shooting_score = technique_score
        components = {
            "technique": technique_score,
            "power":     None
        }

    return {
        "shooting_score": shooting_score,
        "components":     components,
        "grade_label":    get_grade_label(shooting_score)
    }
    