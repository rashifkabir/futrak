// Central data layer for the ProPath FC frontend prototype.
//
// HONESTY RULE: nothing here is fabricated as if it were a real measurement.
// Values that would come from the (not-yet-calibrated) scorer are null.
// The UI reads `null` and renders a genuine empty state — never a fake number.

import { type ShotType, RANKED_SHOT_TYPE_IDS } from './shotTypes';
export type { ShotType } from './shotTypes';

export type Condition = 'static' | 'runup';

export interface ShotTypeMeta {
  id: ShotType;
  name: string;
  blurb: string;
}

// All registered shot types, including trivela — the metadata itself isn't
// gated (trivela still needs a name/blurb wherever the side-competition
// path ends up surfacing it). Ranked-flow screens should use
// RANKED_SHOT_TYPES below instead of this, so trivela doesn't appear there.
export const SHOT_TYPES: ShotTypeMeta[] = [
  { id: 'laces',   name: 'Laces / Power', blurb: 'Instep drive. Straight through the ball.' },
  { id: 'finesse', name: 'Finesse',       blurb: 'Inside-foot curl. Placement over power.' },
  { id: 'trivela', name: 'Trivela',       blurb: 'Outside-foot curl. Across the body.' },
];

// Main ranked flow (Assess matrix, Rank leaderboard) — see lib/shotTypes.ts
// for the availability config. Currently laces + finesse; trivela is
// reserved for the £2.50 side-competition path (not built yet).
export const RANKED_SHOT_TYPES: ShotTypeMeta[] = SHOT_TYPES.filter((s) => RANKED_SHOT_TYPE_IDS.includes(s.id));

export const CONDITIONS: { id: Condition; name: string; note: string; measuresPower: boolean }[] = [
  { id: 'static', name: 'Static',  note: 'Still ball. Everything under your control.', measuresPower: true },
  { id: 'runup',  name: 'Run-up',  note: 'Run onto the ball, then strike.',            measuresPower: false },
];

// A cell of the assessment matrix. score/power are null until calibrated + attempted.
export interface Cell {
  attempts: number;      // how many of the base attempts are used
  baseAttempts: number;
  score: number | null;  // technique score — null = not scored yet
  power: number | null;  // null = not measured (run-up) or not attempted
  band: string | null;   // coach-style band once calibration exists
}

function emptyCell(): Cell {
  return { attempts: 0, baseAttempts: 3, score: null, power: null, band: null };
}

export interface AssessmentState {
  [key: string]: Cell; // key = `${shotType}:${condition}`
}

export function freshAssessment(): AssessmentState {
  const s: AssessmentState = {};
  for (const st of SHOT_TYPES) {
    for (const c of CONDITIONS) {
      s[`${st.id}:${c.id}`] = emptyCell();
    }
  }
  return s;
}

// Attributes shown on the profile. v1 ships SHOOTING; the rest are real
// future attributes shown as locked, so the player sees shooting is the
// first attribute, not the only one the platform will ever have.
export interface Attribute {
  id: string;
  name: string;
  status: 'live' | 'coming';
}

export const ATTRIBUTES: Attribute[] = [
  { id: 'shooting',  name: 'Shooting',  status: 'live'   },
  { id: 'finishing', name: 'Finishing', status: 'coming' },
  { id: 'pace',      name: 'Pace',      status: 'coming' },
  { id: 'dribbling', name: 'Dribbling', status: 'coming' },
];

export const LOCATIONS = ['London', 'Outside London'] as const;
