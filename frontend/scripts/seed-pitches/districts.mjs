import { overpassQuery } from './overpass.mjs';

// UK local authority districts (England admin_level=8; Scotland/Wales
// council areas/unitary authorities are admin_level=6) — chunking by real
// administrative boundary rather than an arbitrary lat/lng grid means each
// query is a sensible size (validated: a Greater-London-sized bbox query
// completes in seconds) AND gives every chunk a meaningful name for free,
// used as the last-resort "Pitch in <district>" fallback name and as the
// `area` field on seeded pitches.
//
// Scoped to GB via an Overpass area filter (not just a bounding box) so a
// loose UK bbox doesn't pull in neighbouring French departments.
export async function getDistricts() {
  const query = `
    [out:json][timeout:180];
    area["ISO3166-1"="GB"][admin_level=2]->.gb;
    relation(area.gb)["boundary"="administrative"]["admin_level"~"^(6|8)$"];
    out tags bb;
  `;
  const data = await overpassQuery(query, { retries: 4, backoffMs: 8000 });
  return data.elements
    .filter((e) => e.tags?.name && e.bounds)
    .map((e) => ({
      id: e.id,
      name: e.tags.name,
      bounds: e.bounds, // { minlat, minlon, maxlat, maxlon }
    }));
}
