-- FOR LOCAL TESTING ONLY — never run this against a real Supabase project,
-- which already provides a real `auth` schema and `auth.uid()`. This is a
-- minimal stand-in so the migrations in supabase/migrations/ can be
-- exercised against a plain local Postgres (this sandbox has no Docker,
-- so the real `supabase start` local stack isn't available).

do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'authenticated') then
    create role authenticated;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'anon') then
    create role anon;
  end if;
end
$$;

create schema if not exists auth;

create table auth.users (
  id                 uuid primary key default gen_random_uuid(),
  email              text,
  raw_user_meta_data jsonb not null default '{}'::jsonb
);

-- Session-local "current user", settable per-connection to simulate
-- different logged-in users across test scenarios.
create function auth.uid() returns uuid
language sql stable
as $$
  select nullif(current_setting('app.current_uid', true), '')::uuid;
$$;

create function set_current_user(p_auth_user_id uuid) returns void
language sql
as $$
  select set_config('app.current_uid', p_auth_user_id::text, false);
$$;
