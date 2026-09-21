#!/usr/bin/env node
// One-off bulk seed: OSM football pitches (leisure=pitch, sport matching
// soccer OR multi — see the Stage 3 plan for why strict sport=soccer
// undercounts informal cages) -> frontend/public/data/pitches.json.
//
// NOT a live API dependency — run this by hand when you want to refresh
// the seed, not on every app build. Chunked by UK administrative district
// (not an arbitrary grid) so every request stays a sane size and every
// chunk gets a meaningful name for free. Resumable: each district's raw
// result is cached to .cache/<id>.json and skipped on re-run, since a
// full UK run is many sequential requests against a shared free instance
// and may need to be stopped/resumed.
//
// Usage:
//   node scripts/seed-pitches/index.mjs                        # full UK
//   node scripts/seed-pitches/index.mjs --only="Hackney,Tower Hamlets"

import { mkdir, readFile, writeFile, readdir } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { overpassQuery } from './overpass.mjs';
import { getDistricts } from './districts.mjs';
import { deriveName, disambiguateNames } from './deriveName.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const CACHE_DIR = path.join(__dirname, '.cache');
const OUTPUT_PATH = path.join(__dirname, '../../public/data/pitches.json');
const POLITE_DELAY_MS = 2000; // between requests, so we don't hammer the free instance

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function bboxStr(b) {
  return `${b.minlat},${b.minlon},${b.maxlat},${b.maxlon}`;
}

async function fetchDistrict(district) {
  const bb = bboxStr(district.bounds);

  const pitchesQuery = `
    [out:json][timeout:120];
    (
      node["leisure"="pitch"]["sport"~"soccer|multi"](${bb});
      way["leisure"="pitch"]["sport"~"soccer|multi"](${bb});
      relation["leisure"="pitch"]["sport"~"soccer|multi"](${bb});
    );
    out center tags;
  `;
  const contextQuery = `
    [out:json][timeout:120];
    (
      way["leisure"~"^(park|nature_reserve|recreation_ground)$"]["name"](${bb});
      way["highway"]["name"](${bb});
    );
    out center tags;
  `;

  const pitches = await overpassQuery(pitchesQuery);
  await sleep(POLITE_DELAY_MS);
  const context = await overpassQuery(contextQuery);
  await sleep(POLITE_DELAY_MS);

  return { district, pitches: pitches.elements, context: context.elements };
}

function toLatLng(el) {
  return el.center ? { lat: el.center.lat, lng: el.center.lon } : { lat: el.lat, lng: el.lon };
}

async function main() {
  const onlyArg = process.argv.find((a) => a.startsWith('--only='));
  const only = onlyArg ? onlyArg.slice('--only='.length).split(',').map((s) => s.trim()) : null;

  await mkdir(CACHE_DIR, { recursive: true });

  console.log('Fetching UK district list...');
  let districts = await getDistricts();
  if (only) {
    districts = districts.filter((d) => only.some((name) => d.name.includes(name)));
    console.log(`Filtered to ${districts.length} district(s) matching --only=${only.join(',')}`);
  } else {
    console.log(`${districts.length} districts total (full UK run).`);
  }

  for (const [i, district] of districts.entries()) {
    const cachePath = path.join(CACHE_DIR, `${district.id}.json`);
    if (existsSync(cachePath)) {
      console.log(`[${i + 1}/${districts.length}] ${district.name} — cached, skipping`);
      continue;
    }
    console.log(`[${i + 1}/${districts.length}] ${district.name} — fetching...`);
    try {
      const result = await fetchDistrict(district);
      await writeFile(cachePath, JSON.stringify(result));
      console.log(`  -> ${result.pitches.length} pitches, ${result.context.length} context features`);
    } catch (err) {
      console.error(`  FAILED: ${err.message} — will retry on next run`);
    }
  }

  console.log('Merging cached districts...');
  const cacheFiles = (await readdir(CACHE_DIR)).filter((f) => f.endsWith('.json'));

  const byOsmKey = new Map(); // dedupe across district boundary overlaps
  for (const file of cacheFiles) {
    const { district, pitches, context } = JSON.parse(await readFile(path.join(CACHE_DIR, file), 'utf-8'));
    const parks = context
      .filter((e) => e.tags?.leisure && e.tags?.name)
      .map((e) => ({ ...toLatLng(e), name: e.tags.name }));
    const streets = context
      .filter((e) => e.tags?.highway && e.tags?.name)
      .map((e) => ({ ...toLatLng(e), name: e.tags.name }));

    for (const el of pitches) {
      const key = `${el.type}:${el.id}`;
      if (byOsmKey.has(key)) continue; // already captured from another district's overlap

      const { lat, lng } = toLatLng(el);
      const existingName = el.tags?.name;
      const name = existingName ?? deriveName({ lat, lng }, { parks, streets }, district.name);

      byOsmKey.set(key, {
        id: `osm:${key}`,
        name,
        nameWasDerived: !existingName,
        area: district.name,
        lat,
        lng,
        source: 'osm',
        verified: true,
        crownState: 'unclaimed',
        king: null,
        challengers: [],
      });
    }
  }

  const pitches = disambiguateNames([...byOsmKey.values()]).map(({ nameWasDerived, ...rest }) => rest);

  await mkdir(path.dirname(OUTPUT_PATH), { recursive: true });
  await writeFile(OUTPUT_PATH, JSON.stringify(pitches));
  console.log(`Wrote ${pitches.length} pitches to ${OUTPUT_PATH}`);
  const namedCount = pitches.filter((p) => !p.name.startsWith('Pitch in')).length;
  console.log(`(${pitches.length - namedCount} used the district-name fallback)`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
