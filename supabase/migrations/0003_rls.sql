-- RLS is the structural enforcement of "clients cannot write shots/crowns
-- directly" — the whole point of putting submit_ranked_shot in the way.
-- That function is `security definer`, so it can write regardless of the
-- calling user's own restrictions below; nothing else can.

alter table profiles enable row level security;
alter table pitches enable row level security;
alter table shots enable row level security;
alter table crowns enable row level security;
alter table notification_queue enable row level security;

-- profiles: names need to be visible to everyone (crown/challenger lists
-- show other players' names) — only the owner can edit their own row.
create policy "profiles are publicly readable"
  on profiles for select
  using (true);

create policy "users can update their own profile"
  on profiles for update
  using (auth_user_id = auth.uid());

-- pitches: browsing doesn't require login. Authenticated users may add
-- their own (Stage 3's "user-added pitch" feature) but only as
-- unverified, source='user' — never claiming osm/demo provenance or
-- pre-verified status for themselves.
create policy "pitches are publicly readable"
  on pitches for select
  using (true);

create policy "authenticated users can add unverified pitches"
  on pitches for insert
  to authenticated
  with check (source = 'user' and verified = false);

-- shots: users can read their own shot history. No insert/update/delete
-- policy at all — the only write path is submit_ranked_shot.
create policy "users can read their own shots"
  on shots for select
  using (user_id in (select id from profiles where auth_user_id = auth.uid()));

-- crowns: public read (map + detail views need holder/unclaimed state for
-- everyone). No write policy — only submit_ranked_shot writes here.
create policy "crowns are publicly readable"
  on crowns for select
  using (true);

-- notification_queue: no client policies at all (deny by default). Only
-- the drain-notifications Edge Function touches this, using the service
-- role key, which bypasses RLS entirely.
