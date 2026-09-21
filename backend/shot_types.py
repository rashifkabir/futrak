"""
Single source of truth for which shot types are available where.

Trivela is fully built and scored (see cv_engine/trivela_technique.py) but is
currently reserved for the (not yet built) GBP2.50 side-competition path --
disabled in the main ranked flow / leaderboard for now. Mirrors
frontend/src/lib/shotTypes.ts (and mobile's copy of the same file); the two
are kept in sync by hand since there's no shared codegen between the Python
and TS sides.

To re-enable trivela in the main ranked flow: flip its "ranked" flag to True
here AND in frontend/src/lib/shotTypes.ts / mobile/src/lib/shotTypes.ts --
nothing else needs to change.

This does NOT gate the raw /analyse/shooting endpoint (see api/routes.py) --
that stays shot-type-agnostic infrastructure so the trivela scorer remains
fully callable (required for the side-competition path once it's built).
The "ranked" flag gates ranked-flow/leaderboard surfacing only.
"""

SHOT_TYPE_CONFIG = {
    "laces":   {"ranked": True,  "side_comp": True},
    "finesse": {"ranked": True,  "side_comp": True},
    "trivela": {"ranked": False, "side_comp": True},
}

ALL_SHOT_TYPES = set(SHOT_TYPE_CONFIG)
RANKED_SHOT_TYPES = {k for k, v in SHOT_TYPE_CONFIG.items() if v["ranked"]}
SIDE_COMP_SHOT_TYPES = {k for k, v in SHOT_TYPE_CONFIG.items() if v["side_comp"]}
