"""
Natural-language coaching layer for ProPath FC.

Takes the structured output of technique_coach.coach_technique()
and produces player-facing advice. Follows strict rules:
  - reference ONLY observed/measured metrics
  - ONE primary fix (the weakest reliable dimension)
  - max 2 corrections + 1 positive
  - shot-type specific
  - NEVER comment on things flagged "not measured" (foot
    surface, 3D lean) — we can't see them
  - no generic advice

Uses the Anthropic API if a key is available; otherwise falls
back to a deterministic template built from the same structured
data (so it always works offline).
"""
import os, json

# dimensions we can reliably comment on (exclude noisy/unmeasured)
RELIABLE_DIMS = {"follow_through", "foot_speed", "swing_path",
                 "approach", "balance"}
# follow_wrap is noisy — mention only mildly, never as primary fix
SOFT_DIMS = {"follow_wrap"}


def _pick_primary_fix(result):
    """Weakest RELIABLE dimension = the one primary fix."""
    scores = result.get("scores", {})
    candidates = {k: v for k, v in scores.items()
                  if k in RELIABLE_DIMS and v is not None}
    if not candidates:
        return None
    worst = min(candidates, key=candidates.get)
    return worst if candidates[worst] < 7.0 else None


def _pick_strength(result):
    """Best reliable dimension = the positive note."""
    scores = result.get("scores", {})
    candidates = {k: v for k, v in scores.items()
                  if k in RELIABLE_DIMS and v is not None}
    if not candidates:
        return None
    best = max(candidates, key=candidates.get)
    return best if candidates[best] >= 7.0 else None


def build_coaching(result, use_api=True):
    """Return {'text': ..., 'primary_fix': ..., 'strength': ...}."""
    if "error" in result:
        return {"text": result["error"], "primary_fix": None,
                "strength": None}

    primary = _pick_primary_fix(result)
    strength = _pick_strength(result)

    # Build a compact, honest brief for the LLM (only reliable data)
    brief = {
        "shot_type": result["shot_label"],
        "overall_score": result["overall_score"],
        "coaching_focus": result["coaching_focus"],
        "reliable_scores": {k: v for k, v in result["scores"].items()
                            if k in RELIABLE_DIMS and v is not None},
        "primary_fix_dimension": primary,
        "strength_dimension": strength,
        "do_not_mention": ["exact foot contact surface",
                           "3D body lean", "anything not in scores"],
    }

    if use_api and os.environ.get("ANTHROPIC_API_KEY"):
        try:
            text = _llm_coach(brief)
            return {"text": text, "primary_fix": primary,
                    "strength": strength}
        except Exception:
            pass  # fall through to template

    # Deterministic template fallback (always works)
    return {"text": _template_coach(result, primary, strength),
            "primary_fix": primary, "strength": strength}


def _llm_coach(brief):
    import anthropic
    client = anthropic.Anthropic()
    prompt = (
        "You are a football shooting coach giving feedback on ONE shot.\n"
        "Use ONLY the data below. Rules:\n"
        "- Reference specific observed metrics.\n"
        "- Give ONE primary fix (the primary_fix_dimension) with a concrete cue.\n"
        "- Add at most ONE more minor point.\n"
        "- End with one genuine positive (the strength_dimension).\n"
        "- Be specific to the shot type.\n"
        "- NEVER mention anything in 'do_not_mention'. Do not invent\n"
        "  metrics (foot surface, body lean) we did not measure.\n"
        "- 3-4 sentences, encouraging, concrete. No bullet points.\n\n"
        f"DATA:\n{json.dumps(brief, indent=2)}"
    )
    msg = client.messages.create(
        model="claude-sonnet-4-6", max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in msg.content if hasattr(b, "text")).strip()


# human-readable cue per dimension (for the template + LLM context)
_CUES = {
    "follow_through": "swing your leg fully through the ball after contact",
    "foot_speed": "accelerate your kicking foot harder into the ball",
    "swing_path": "keep a cleaner swing path into the ball",
    "approach": "set your run-up angle to suit this shot",
    "balance": "plant your standing foot firmly and stay balanced over the ball",
}
_PRAISE = {
    "follow_through": "Your follow-through is strong",
    "foot_speed": "You generate good foot speed",
    "swing_path": "Your swing path is clean",
    "approach": "Your approach angle is well-judged",
    "balance": "Your balance over the ball is excellent",
}


def _template_coach(result, primary, strength):
    label = result["shot_label"]
    ov = result["overall_score"]
    parts = [f"On this {label}, you scored {ov}/10 overall."]
    if primary:
        sc = result["scores"][primary]
        parts.append(f"Your main area to work on is {primary.replace('_',' ')} "
                     f"({sc}/10) — {_CUES.get(primary, 'refine this aspect')}.")
    else:
        parts.append("Your execution is solid across the board for this shot.")
    if strength:
        parts.append(f"{_PRAISE.get(strength, 'Good work')} — keep that.")
    return " ".join(parts)
