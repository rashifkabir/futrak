// Name derivation for the ~93% of pitches OSM has no name for (see the
// investigation numbers in the Stage 3 plan). Matching happens in-process
// against context features already fetched for the same district — no
// extra per-pitch API calls, which would be impractical at UK scale.
//
// Duplicated haversine (not imported from src/lib/geo.ts) on purpose: this
// is a standalone Node script with no TS build step, and the formula is a
// few stable lines — not worth wiring up ts-node for.
function haversineMeters(a, b) {
  const R = 6371000;
  const toRad = (d) => (d * Math.PI) / 180;
  const dLat = toRad(b.lat - a.lat);
  const dLng = toRad(b.lng - a.lng);
  const s = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(a.lat)) * Math.cos(toRad(b.lat)) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.atan2(Math.sqrt(s), Math.sqrt(1 - s));
}

const PARK_RADIUS_M = 250;
const STREET_RADIUS_M = 150;

// `context` is { parks: [{lat,lng,name}], streets: [{lat,lng,name}] } for
// the same district the pitch is in.
export function deriveName(pitch, context, districtName) {
  const nearestPark = nearest(pitch, context.parks, PARK_RADIUS_M);
  if (nearestPark) return nearestPark.name;

  const nearestStreet = nearest(pitch, context.streets, STREET_RADIUS_M);
  if (nearestStreet) return nearestStreet.name;

  return `Pitch in ${districtName}`;
}

function nearest(point, candidates, maxRadiusM) {
  let best = null;
  let bestDist = maxRadiusM;
  for (const c of candidates) {
    const d = haversineMeters(point, c);
    if (d <= bestDist) {
      best = c;
      bestDist = d;
    }
  }
  return best;
}

// Given the full list of seeded pitches (already name-derived), disambiguate
// duplicate derived names by appending the last 4 hex chars of the OSM id —
// only when a collision actually happens (common: 50+ Hackney Marshes
// pitches all nearest the same park), so most names stay clean.
export function disambiguateNames(pitches) {
  const counts = new Map();
  for (const p of pitches) {
    if (!p.nameWasDerived) continue;
    counts.set(p.name, (counts.get(p.name) ?? 0) + 1);
  }
  for (const p of pitches) {
    if (p.nameWasDerived && counts.get(p.name) > 1) {
      const suffix = p.id.replace(/[^a-zA-Z0-9]/g, '').slice(-4);
      p.name = `${p.name} (${suffix})`;
    }
  }
  return pitches;
}
