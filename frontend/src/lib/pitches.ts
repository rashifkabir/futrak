// Shared pitch data layer for King of the Pitch.
//
// Three sources feed one combined list, all client-side (no backend yet):
//  - 'demo'  — the 4 Stage 1/2 hand-authored fixtures (pitchesMock.ts),
//              kept so the crown-state UI (mine/lost/other) stays visible.
//  - 'osm'   — real pitches from the one-off Overpass seed
//              (scripts/seed-pitches/), shipped as a static JSON asset and
//              fetched at runtime rather than imported, since a UK-wide
//              seed is tens of thousands of records — too big to bundle.
//  - 'user'  — pitches players add themselves (see screens/AddPitch.tsx),
//              kept in localStorage. OSM coverage of informal cages is
//              patchy by nature (crowd-mapped, and many are on private
//              estates) — this is a first-class gap-filling feature, not
//              an afterthought.
//
// None of the real ('osm'/'user') pitches have crown data — there's no
// backend to hold it yet — so they always start `unclaimed` with no king
// and no challengers, same honest-empty pattern as everywhere else in the
// app (see components/Empty.tsx).

import { haversineMeters, type LatLng } from './geo';

export type CrownState = 'mine' | 'lost' | 'other' | 'unclaimed';
export type PitchSource = 'demo' | 'osm' | 'user';

export interface Challenger {
  rank: number;
  name: string;
  band: string | null;
  power: number | null;
}

export interface King {
  name: string;
  band: string | null;
  power: number | null;
  heldSinceDays: number;
  timesDefended: number;
}

export interface Pitch {
  id: string;
  name: string;
  area: string;
  lat: number;
  lng: number;
  source: PitchSource;
  verified: boolean; // true for 'demo'/'osm', false for user-added until moderated
  crownState: CrownState;
  king: King | null; // null only when crownState === 'unclaimed'
  challengers: Challenger[];
}

const SEEDED_PITCHES_URL = '/data/pitches.json';
const USER_PITCHES_STORAGE_KEY = 'kotp:user-added-pitches';

let seededPitchesPromise: Promise<Pitch[]> | null = null;

// Memoised — repeated calls (e.g. re-renders) reuse the same in-flight or
// resolved fetch instead of re-requesting the asset.
export function loadSeededPitches(): Promise<Pitch[]> {
  if (!seededPitchesPromise) {
    seededPitchesPromise = fetch(SEEDED_PITCHES_URL)
      .then((res) => (res.ok ? res.json() : []))
      .catch(() => []);
  }
  return seededPitchesPromise;
}

export function loadUserAddedPitches(): Pitch[] {
  try {
    const raw = localStorage.getItem(USER_PITCHES_STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function saveUserAddedPitch(pitch: Pitch): void {
  const existing = loadUserAddedPitches();
  localStorage.setItem(USER_PITCHES_STORAGE_KEY, JSON.stringify([...existing, pitch]));
}

// Dedup check: is there already a pitch within `radiusM` of `point`? Used
// both before showing the "add a pitch" form (suggest the existing one
// instead of creating a near-duplicate) and could be reused server-side
// later against the same rule.
export function findNearbyPitch(point: LatLng, pitches: Pitch[], radiusM = 30): Pitch | null {
  let closest: Pitch | null = null;
  let closestDist = Infinity;
  for (const p of pitches) {
    const d = haversineMeters(point, p);
    if (d <= radiusM && d < closestDist) {
      closest = p;
      closestDist = d;
    }
  }
  return closest;
}
