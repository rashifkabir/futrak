// Pure geo math for King of the Pitch — no React, no mock data here.
//
// HONESTY RULE (see project design notes): a GPS fix is never treated as an exact
// point. Every distance check folds in the reported accuracy radius rather
// than trusting it to the metre.

export interface LatLng {
  lat: number;
  lng: number;
}

const EARTH_RADIUS_M = 6371000;

function toRad(deg: number): number {
  return (deg * Math.PI) / 180;
}

export function haversineMeters(a: LatLng, b: LatLng): number {
  const dLat = toRad(b.lat - a.lat);
  const dLng = toRad(b.lng - a.lng);
  const s = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(a.lat)) * Math.cos(toRad(b.lat)) * Math.sin(dLng / 2) ** 2;
  return 2 * EARTH_RADIUS_M * Math.atan2(Math.sqrt(s), Math.sqrt(1 - s));
}

export function formatDistance(m: number): string {
  return m < 1000 ? `${Math.round(m)}m` : `${(m / 1000).toFixed(1)}km`;
}

export const GEOFENCE_RADIUS_M = 50;
export const MAX_USABLE_ACCURACY_M = 100;

// Tri-state (really five-state) rather than a boolean: accuracy is only
// ever a radius of uncertainty, so "in range" must survive the worst case
// and "out of range" must survive the best case. Anything in between is
// an honest "can't confirm", not a coin-flip pass/fail.
export type GeofenceStatus =
  | { kind: 'in' }
  | { kind: 'out'; distanceM: number }
  | { kind: 'uncertain-boundary'; distanceM: number; accuracyM: number }
  | { kind: 'uncertain-weak-signal'; accuracyM: number }
  | { kind: 'no-fix' };

export function getGeofenceStatus(distanceM: number | null, accuracyM: number | null): GeofenceStatus {
  if (distanceM === null || accuracyM === null) return { kind: 'no-fix' };
  if (accuracyM > MAX_USABLE_ACCURACY_M) return { kind: 'uncertain-weak-signal', accuracyM };
  const best = distanceM - accuracyM;
  const worst = distanceM + accuracyM;
  if (worst <= GEOFENCE_RADIUS_M) return { kind: 'in' };
  if (best > GEOFENCE_RADIUS_M) return { kind: 'out', distanceM };
  return { kind: 'uncertain-boundary', distanceM, accuracyM };
}
