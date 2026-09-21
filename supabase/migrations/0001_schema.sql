-- King of the Pitch — Stage 4 schema.
-- profiles/shots/crowns/pitches/notification_queue. See the Stage 4 plan
-- for the reasoning behind each design choice referenced in comments below.

create extension if not exists "pgcrypto"; -- gen_random_uuid()

-- Every user gets OUR OWN stable uuid here, separate from auth.users' id,
-- even though today they're 1:1 — so migrating auth providers later means
-- remapping this one column, not every table with a user reference.
create table profiles (
  id              uuid primary key default gen_random_uuid(),
  auth_user_id    uuid not null unique references auth.users(id) on delete cascade,
  display_name    text not null,
  expo_push_token text,
  created_at      timestamptz not null default now()
);

-- id reuses Stage 3's scheme verbatim: 'osm:way:123' / 'user:<uuid>' / 'demo:...'
-- (frontend/src/lib/pitches.ts's Pitch['id']) so client ids never need remapping.
create table pitches (
  id         text primary key,
  name       text not null,
  area       text not null,
  lat        double precision not null,
  lng        double precision not null,
  source     text not null check (source in ('demo', 'osm', 'user')),
  verified   boolean not null default false,
  created_at timestamptz not null default now()
);

create type shot_type as enum ('laces', 'finesse', 'trivela');
create type shot_condition as enum ('static', 'runup');

create table shots (
  id                 uuid primary key default gen_random_uuid(),
  user_id            uuid not null references profiles(id) on delete cascade,
  pitch_id           text not null references pitches(id) on delete cascade,
  shot_type          shot_type not null,
  condition          shot_condition not null,
  technique_score    double precision not null,
  -- Free text, not a fixed enum — the calibration policy is explicit that banding/
  -- calibration is unresolved and subject to recalibration between
  -- seasons; a fixed enum would force a migration every time that changes.
  technique_band     text,
  power              double precision,
  is_ranked          boolean not null,
  gps_lat            double precision,
  gps_lng            double precision,
  gps_accuracy_m     double precision,
  created_at         timestamptz not null default now()
);

create index shots_user_ranked_week_idx on shots (user_id, is_ranked, created_at);
create index shots_pitch_type_idx on shots (pitch_id, shot_type);

-- PRIMARY KEY(pitch_id, shot_type) enforces "one crown per pitch per shot
-- type, no divisions" at the schema level, not just in application logic.
create table crowns (
  pitch_id        text not null references pitches(id) on delete cascade,
  shot_type       shot_type not null,
  holder_user_id  uuid references profiles(id) on delete set null,
  holder_shot_id  uuid references shots(id) on delete set null,
  held_since      timestamptz,
  times_defended  int not null default 0,
  primary key (pitch_id, shot_type)
);

-- Postgres functions can't make outbound HTTP calls without extra
-- extensions, so a crown transfer just writes here; a scheduled Edge
-- Function (supabase/functions/drain-notifications) drains it via Expo's
-- push HTTP API.
create table notification_queue (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references profiles(id) on delete cascade,
  pitch_id   text not null references pitches(id) on delete cascade,
  message    text not null,
  sent_at    timestamptz,
  created_at timestamptz not null default now()
);
