-- The one trusted entry point for recording a shot and (for ranked
-- attempts) transferring a crown. security definer so it can write to
-- shots/crowns despite RLS blocking direct client writes to both — see
-- 0003_rls.sql. Every check below is something a modified client could
-- otherwise lie about, which is exactly why it lives here and not in the
-- app.
create function submit_ranked_shot(
  p_pitch_id        text,
  p_shot_type       shot_type,
  p_condition       shot_condition,
  p_technique_score double precision,
  p_technique_band  text,
  p_power           double precision,
  p_is_ranked       boolean,
  p_gps_lat         double precision default null,
  p_gps_lng         double precision default null,
  p_gps_accuracy_m  double precision default null
) returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  v_user_id        uuid;
  v_pitch          pitches;
  v_distance       double precision;
  v_geofence       text;
  v_week_start     timestamptz;
  v_ranked_count   int;
  v_shot_id        uuid;
  v_crown          crowns;
  v_holder_score   double precision;
  v_old_holder     uuid;
  v_holder_changed boolean := false;
  v_rows_inserted  int;
begin
  select id into v_user_id from profiles where auth_user_id = auth.uid();
  if v_user_id is null then
    raise exception 'no profile for current user' using errcode = 'P0000';
  end if;

  select * into v_pitch from pitches where id = p_pitch_id;
  if not found then
    raise exception 'unknown pitch %', p_pitch_id using errcode = 'P0003';
  end if;

  if p_is_ranked then
    if p_gps_lat is null or p_gps_lng is null or p_gps_accuracy_m is null then
      raise exception 'gps fix required for a ranked attempt' using errcode = 'P0001';
    end if;

    v_distance := haversine_meters(p_gps_lat, p_gps_lng, v_pitch.lat, v_pitch.lng);
    v_geofence := geofence_status(v_distance, p_gps_accuracy_m);
    if v_geofence <> 'in' then
      raise exception 'geofence check failed: %', v_geofence using errcode = 'P0001';
    end if;

    -- Week boundary: Monday 00:00 UTC. Counted from shots directly rather
    -- than a separate counter table — one less thing that can drift out
    -- of sync with reality.
    v_week_start := date_trunc('week', now() at time zone 'utc') at time zone 'utc';
    select count(*) into v_ranked_count
    from shots
    where user_id = v_user_id and is_ranked and created_at >= v_week_start;

    if v_ranked_count >= 3 then
      raise exception 'weekly ranked attempt limit reached' using errcode = 'P0002';
    end if;
  end if;

  insert into shots (
    user_id, pitch_id, shot_type, condition, technique_score, technique_band,
    power, is_ranked, gps_lat, gps_lng, gps_accuracy_m
  ) values (
    v_user_id, p_pitch_id, p_shot_type, p_condition, p_technique_score, p_technique_band,
    p_power, p_is_ranked, p_gps_lat, p_gps_lng, p_gps_accuracy_m
  ) returning id into v_shot_id;

  if not p_is_ranked then
    return jsonb_build_object('shot_id', v_shot_id, 'crown_changed', false);
  end if;

  -- Lock the crown row for this pitch+shot_type for the rest of the
  -- transaction, so two near-simultaneous challengers can't both "win" —
  -- the second to arrive here blocks until the first commits, then sees
  -- its result.
  select * into v_crown from crowns
    where pitch_id = p_pitch_id and shot_type = p_shot_type
    for update;

  if not found then
    -- Unclaimed pitch+shot_type: try to be the first claim. ON CONFLICT
    -- matters here — SELECT ... FOR UPDATE only locks rows that already
    -- exist, so it can't serialize two transactions racing for the very
    -- first claim the way it can for an already-claimed crown. Without
    -- this, the loser gets a raw duplicate-key error instead of a fair
    -- result (empirically reproduced while testing this function: two
    -- concurrent first claims, one got a bare
    -- "duplicate key value violates unique constraint" error).
    insert into crowns (pitch_id, shot_type, holder_user_id, holder_shot_id, held_since, times_defended)
    values (p_pitch_id, p_shot_type, v_user_id, v_shot_id, now(), 0)
    on conflict (pitch_id, shot_type) do nothing;

    get diagnostics v_rows_inserted = row_count;

    if v_rows_inserted = 0 then
      -- Lost the race: someone else's claim committed between our SELECT
      -- above and this INSERT. Re-fetch (now guaranteed to exist) with a
      -- lock and fall through to the normal compare-and-update logic
      -- below, so our shot is fairly judged as a challenge against
      -- whichever claim actually landed first — not silently dropped.
      select * into v_crown from crowns
        where pitch_id = p_pitch_id and shot_type = p_shot_type
        for update;
    end if;
    -- else: our claim won outright, v_crown stays null (from the failed
    -- SELECT above) so the comparison block below is correctly skipped.
  end if;

  if v_crown.pitch_id is not null then
    select technique_score into v_holder_score from shots where id = v_crown.holder_shot_id;

    if v_crown.holder_user_id is distinct from v_user_id and p_technique_score > v_holder_score then
      -- Real takeover from a different holder.
      v_old_holder := v_crown.holder_user_id;
      update crowns
        set holder_user_id = v_user_id, holder_shot_id = v_shot_id, held_since = now(), times_defended = 0
        where pitch_id = p_pitch_id and shot_type = p_shot_type;
      v_holder_changed := true;
    elsif v_crown.holder_user_id = v_user_id and p_technique_score > v_holder_score then
      -- Self-improvement: still the same reign, just a new personal best.
      -- held_since/times_defended are untouched on purpose — they didn't
      -- lose and regain the crown, so resetting either would misrepresent
      -- how long the reign has actually lasted.
      update crowns set holder_shot_id = v_shot_id
        where pitch_id = p_pitch_id and shot_type = p_shot_type;
    elsif v_crown.holder_user_id is distinct from v_user_id then
      -- Failed challenge: score didn't beat the holder.
      update crowns set times_defended = times_defended + 1
        where pitch_id = p_pitch_id and shot_type = p_shot_type;
    end if;
    -- else: the holder submitted a non-improving ranked shot on their own
    -- crown — no one challenged them, nothing changes.
  end if;

  if v_holder_changed and v_old_holder is not null then
    insert into notification_queue (user_id, pitch_id, message)
    values (v_old_holder, p_pitch_id, format('Your crown at %s has been taken.', v_pitch.name));
  end if;

  return jsonb_build_object(
    'shot_id', v_shot_id,
    'crown_changed', v_holder_changed,
    'crown', (select row_to_json(c) from crowns c where pitch_id = p_pitch_id and shot_type = p_shot_type)
  );
end;
$$;
