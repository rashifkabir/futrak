#!/usr/bin/env node
// One-off import: frontend/public/data/pitches.json (Stage 3's Overpass
// seed) -> the `pitches` table. Uses PostgREST's bulk upsert directly
// (no @supabase/supabase-js dependency needed for a one-shot script) with
// the service role key, since RLS only allows authenticated users to
// insert their own unverified pitches — this needs to write verified OSM
// rows, which requires bypassing RLS the same way the drain-notifications
// function does.
//
// Usage:
//   SUPABASE_URL=https://xxx.supabase.co \
//   SUPABASE_SERVICE_ROLE_KEY=eyJ... \
//   node supabase/seed/import-pitches.mjs [path/to/pitches.json]

import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const BATCH_SIZE = 500;

async function main() {
  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) {
    console.error('SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set.');
    process.exit(1);
  }

  const inputPath = process.argv[2] ?? path.join(__dirname, '../../frontend/public/data/pitches.json');
  const pitches = JSON.parse(await readFile(inputPath, 'utf-8'));
  console.log(`Loaded ${pitches.length} pitches from ${inputPath}`);

  // pitches.json's Pitch shape (frontend/src/lib/pitches.ts) carries
  // crownState/king/challengers fields that belong to Stage 1-3's
  // client-only demo model — the real crowns table (this stage) is the
  // source of truth for that now, so only the location/identity fields
  // are imported here.
  const rows = pitches.map((p) => ({
    id: p.id,
    name: p.name,
    area: p.area,
    lat: p.lat,
    lng: p.lng,
    source: p.source,
    verified: p.verified,
  }));

  let imported = 0;
  for (let i = 0; i < rows.length; i += BATCH_SIZE) {
    const batch = rows.slice(i, i + BATCH_SIZE);
    const res = await fetch(`${url}/rest/v1/pitches`, {
      method: 'POST',
      headers: {
        apikey: key,
        Authorization: `Bearer ${key}`,
        'Content-Type': 'application/json',
        Prefer: 'resolution=merge-duplicates,return=minimal',
      },
      body: JSON.stringify(batch),
    });
    if (!res.ok) {
      console.error(`Batch ${i / BATCH_SIZE} failed: HTTP ${res.status} — ${await res.text()}`);
      process.exit(1);
    }
    imported += batch.length;
    console.log(`  imported ${imported}/${rows.length}`);
  }

  console.log('Done.');
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
