// Canonical shot-type identity + availability — single source of truth for
// which shot types are eligible for the main ranked flow vs. the (not yet
// built) £2.50 side-competition path. Mirrors backend/shot_types.py; the
// two are kept in sync by hand since there's no shared codegen between the
// Python and TS sides.
//
// Trivela is fully built and scored (backend/cv_engine/trivela_technique.py,
// screens/FilmGuide.tsx's planting-foot-side guidance) but disabled in
// ranked for now. To re-enable it in the main ranked flow: flip its
// `ranked` flag to `true` here AND in backend/shot_types.py — nothing else
// needs to change.

export type ShotType = 'laces' | 'finesse' | 'trivela';

export interface ShotTypeAvailability {
  ranked: boolean;
  sideComp: boolean;
}

export const SHOT_TYPE_CONFIG: Record<ShotType, ShotTypeAvailability> = {
  laces:   { ranked: true,  sideComp: true },
  finesse: { ranked: true,  sideComp: true },
  trivela: { ranked: false, sideComp: true },
};

const ALL_IDS = Object.keys(SHOT_TYPE_CONFIG) as ShotType[];

// Main ranked flow (Assess matrix, Rank leaderboard) — currently laces + finesse.
export const RANKED_SHOT_TYPE_IDS: ShotType[] = ALL_IDS.filter((id) => SHOT_TYPE_CONFIG[id].ranked);

// £2.50 side-competition path — not built yet (dormant hook). All 3 shot
// types are eligible here, including trivela.
export const SIDE_COMP_SHOT_TYPE_IDS: ShotType[] = ALL_IDS.filter((id) => SHOT_TYPE_CONFIG[id].sideComp);
