import os
import anthropic
from dotenv import load_dotenv

load_dotenv()

OPTIMAL_RANGES = {
    "Power / Laces": {
        "body_lean":              "8–20° forward lean",
        "knee_bend":              "140–168° (slight bend)",
        "hip_shoulder_alignment": "5–18° (square, closed body)",
        "ankle_angle":            "150–180° (fully extended)",
        "follow_through":         ">0.15 (high and long)"
    },
    "Finesse": {
        "body_lean":              "0–12° (upright)",
        "hip_shoulder_alignment": "20–60° (open body — higher is better)",
        "ankle_angle":            "110–150° (inside foot contact)",
        "follow_through":         "0.08–0.20 (controlled pendulum)"
    },
    "Power Curl": {
        "body_lean":              "5–18° forward",
        "hip_shoulder_alignment": "40–85° (very open for curl generation)",
        "ankle_angle":            "95–135° (locked for spin contact)",
        "follow_through":         ">0.12 (strong through the ball)"
    },
    "Low Driven": {
        "body_lean":              "18–35° (extreme forward lean — "
                                  "this is what keeps the ball low)",
        "hip_shoulder_alignment": "3–18° (square body)",
        "ankle_angle":            "145–180° (fully extended like power)",
        "follow_through":         "0.06–0.18 (controlled, "
                                  "directed downward)"
    },
    "Toe-poke": {
        "body_lean":              "-5 to 10° (over the ball, "
                                  "not leaning back)",
        "ankle_angle":            "60–92° (toes pointing directly "
                                  "at target — most critical)",
        "follow_through":         "0–0.05 (short contact, "
                                  "this is correct for toe-poke)"
    },
    "Knuckleball": {
        "body_lean":              "-3 to 5° (very upright — "
                                  "any lean creates spin)",
        "ankle_angle":            "85–120° (locked perpendicular — "
                                  "most critical element)",
        "follow_through":         "0–0.07 (punch action, "
                                  "stop the follow-through)",
        "hip_shoulder_alignment": "0–12° (closed body)"
    },
    "Standard Drive": {
        "body_lean":              "5–15° forward",
        "knee_bend":              "140–168°",
        "hip_shoulder_alignment": "5–20°",
        "ankle_angle":            "140–175°",
        "follow_through":         "0.10–0.20"
    }
}


def generate_ai_feedback(
    shot_type:      str,
    contact_angles: dict,
    ankle_angle:    float | None = None,
    follow_through: float | None = None,
    power_grade:    int   | None = None
) -> str:
    """
    Generates personalised coaching feedback using Claude Haiku.
    Passes full biomechanical measurements and optimal ranges
    so Claude can reason across all signals intelligently.
    """
    client = anthropic.Anthropic(
        api_key=os.getenv("ANTHROPIC_API_KEY")
    )

    lean      = contact_angles.get("body_lean")
    knee_r    = contact_angles.get("knee_bend_right")
    knee_l    = contact_angles.get("knee_bend_left")
    alignment = contact_angles.get("hip_shoulder_alignment")

    measurements = f"""
Shot type detected:     {shot_type}
Body lean at contact:   {f"{lean}°" if lean is not None else "not measured"}
Knee bend right:        {f"{knee_r}°" if knee_r else "not measured"}
Knee bend left:         {f"{knee_l}°" if knee_l else "not measured"}
Hip-shoulder alignment: {f"{alignment}°" if alignment is not None else "not measured"}
Ankle angle:            {f"{ankle_angle}°" if ankle_angle is not None else "not measured"}
Follow-through:         {f"{follow_through}" if follow_through is not None else "not measured"}
Power grade:            {f"{power_grade}/100" if power_grade is not None else "not measured"}
"""

    ranges = OPTIMAL_RANGES.get(
        shot_type,
        OPTIMAL_RANGES["Standard Drive"]
    )
    optimal_text = "\n".join(
        f"  {k.replace('_', ' ').title()}: {v}"
        for k, v in ranges.items()
    )

    prompt = f"""You are an expert football coach analysing
a player's shooting technique from computer vision data.

PLAYER MEASUREMENTS AT BALL CONTACT:
{measurements}

OPTIMAL RANGES FOR {shot_type.upper()}:
{optimal_text}

Give personalised coaching feedback:
- Maximum 3 coaching points
- Start with the single most impactful improvement
- Skip attributes already within optimal range unless exceptional
- Be direct and specific — no generic advice
- Reference exact numbers from their measurements
- If a reading is only slightly outside range, mention briefly
- End with one sentence estimating potential grade improvement
- Talk directly to the player using "you" and "your"
- Keep total response under 130 words
- Do not use markdown headers or asterisks
"""

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[{
                "role":    "user",
                "content": prompt
            }]
        )
        return message.content[0].text

    except Exception as e:
        print(f"[AI feedback error]: {e}")
        return (
            "Could not generate AI feedback right now. "
            "Please try again."
        ) 