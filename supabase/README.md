# King of the Pitch — backend (Stage 4)

Supabase (Postgres). See the Stage 4 plan for the full reasoning; this is
just setup + what's been verified.

## What's here
- `migrations/` — schema, RLS, and the `submit_ranked_shot` function (the
  one trusted entry point for recording a shot and transferring a crown —
  see its comments for the full flow).
- `seed/import-pitches.mjs` — one-off import of Stage 3's
  `frontend/public/data/pitches.json` into the `pitches` table.
- `functions/drain-notifications/` — Edge Function that delivers queued
  crown-loss notifications via Expo Push (mobile only, see plan).
- `tests/` — `local_auth_stub.sql` + `scenarios.sql`. The stub exists
  because this sandbox has no Docker (`supabase start`'s local stack needs
  it) — it's a minimal stand-in for the `auth` schema real Supabase
  already provides. **Never run `local_auth_stub.sql` against a real
  Supabase project.**

## What's actually been verified
- All of `migrations/` was run against a real local Postgres 16 (via
  Homebrew, since no Docker was available) with `tests/local_auth_stub.sql`
  standing in for Supabase's `auth` schema, then exercised against all 7
  scenarios in the plan's Verification section — including a genuine
  concurrency race (5 repeated runs of two simultaneous first-claims on
  the same crown, launched as parallel background `psql` processes). That
  race caught and fixed a real bug: the initial "unclaimed pitch" path
  used a plain `INSERT`, which raised a raw duplicate-key error under
  concurrent first claims (`SELECT ... FOR UPDATE` can't lock a row that
  doesn't exist yet) — fixed with `INSERT ... ON CONFLICT DO NOTHING` +
  re-fetch-and-fall-through, so the loser's shot is fairly judged as a
  challenge against whoever actually landed first, not dropped or errored.
- **Not verified**: `functions/drain-notifications` (no Deno in this
  sandbox) and real Supabase Auth/RLS behavior end-to-end (no Docker, so
  `supabase start`'s real `auth.uid()`/JWT flow was never exercised — only
  the stubbed equivalent). Smoke-test both against a real (or `supabase
  start`, once Docker is available) project before relying on them.

## To actually deploy
```
npx supabase login
npx supabase link --project-ref <your-project-ref>
npx supabase db push                      # applies migrations/
SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... \
  node supabase/seed/import-pitches.mjs
npx supabase functions deploy drain-notifications
# then schedule it (Cron for Edge Functions, or pg_cron + pg_net) to run
# every minute or so.
```
