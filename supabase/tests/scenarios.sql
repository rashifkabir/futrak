-- Exercises submit_ranked_shot against the scenarios in the Stage 4 plan's
-- Verification section. Run after local_auth_stub.sql + all migrations.
\set ON_ERROR_STOP off
\pset format aligned

-- Setup: three users + one pitch (Victoria Park, real coords from Stage 3).
-- Three users so the weekly-limit test (Alice) doesn't collide with the
-- failed-challenge test (Carol) needing her own fresh quota.
insert into auth.users (id, email) values
  ('11111111-1111-1111-1111-111111111111', 'alice@test.dev'),
  ('22222222-2222-2222-2222-222222222222', 'bob@test.dev'),
  ('33333333-3333-3333-3333-333333333333', 'carol@test.dev');

insert into pitches (id, name, area, lat, lng, source, verified)
values ('demo:victoria-park', 'Victoria Park 5-a-side', 'Hackney', 51.5361, -0.0388, 'demo', true);

\echo '=== Scenario 1: ranked shot >50m away -> rejected (geofence) ==='
select set_current_user('11111111-1111-1111-1111-111111111111');
select submit_ranked_shot('demo:victoria-park', 'laces', 'static', 70, 'Good', 60, true, 51.55, -0.0388, 10);

\echo '=== Scenario 3: practice shot from far away, no accuracy -> succeeds, no crown effect (run before Alice uses her weekly quota, order does not matter for this check) ==='
select submit_ranked_shot('demo:victoria-park', 'laces', 'static', 99, 'Elite', 90, false, 60.0, 0.0, null);
select holder_user_id, times_defended from crowns where pitch_id = 'demo:victoria-park' and shot_type = 'laces';
\echo '(expect: no row above -- practice shots never create/touch a crown)'

\echo '=== (setup) Alice uses all 3 weekly ranked attempts; claims crown with the first ==='
select submit_ranked_shot('demo:victoria-park', 'laces', 'static', 50, 'Good', 40, true, 51.5361, -0.0388, 10);
select submit_ranked_shot('demo:victoria-park', 'laces', 'static', 55, 'Good', 42, true, 51.5361, -0.0388, 10);
select submit_ranked_shot('demo:victoria-park', 'laces', 'static', 60, 'Good', 45, true, 51.5361, -0.0388, 10);

\echo '=== Scenario 2: Alice''s 4th ranked shot this week -> rejected (weekly limit) ==='
select submit_ranked_shot('demo:victoria-park', 'laces', 'static', 65, 'Good', 46, true, 51.5361, -0.0388, 10);

\echo '=== state before scenario 4: Alice holds the crown at score 60 ==='
select holder_user_id, times_defended, held_since from crowns where pitch_id = 'demo:victoria-park' and shot_type = 'laces';

\echo '=== Scenario 4: Bob beats Alice (75 > 60) -> crown transfers, times_defended resets, notification queued for Alice ==='
select set_current_user('22222222-2222-2222-2222-222222222222');
select submit_ranked_shot('demo:victoria-park', 'laces', 'static', 75, 'Very good', 65, true, 51.5361, -0.0388, 10);
select holder_user_id, times_defended, held_since from crowns where pitch_id = 'demo:victoria-park' and shot_type = 'laces';
select user_id, message, sent_at from notification_queue;
\echo '(expect notification user_id = Alice''s profile id, since she was dethroned)'

\echo '=== Scenario 5: Carol challenges Bob and fails (40 < 75) -> times_defended increments, holder unchanged ==='
select set_current_user('33333333-3333-3333-3333-333333333333');
select submit_ranked_shot('demo:victoria-park', 'laces', 'static', 40, 'Good', 35, true, 51.5361, -0.0388, 10);
select holder_user_id, times_defended from crowns where pitch_id = 'demo:victoria-park' and shot_type = 'laces';

\echo '=== Scenario 6: Bob (current holder) submits a non-improving ranked shot -> crowns row completely unchanged ==='
select set_current_user('22222222-2222-2222-2222-222222222222');
select holder_user_id, holder_shot_id, held_since, times_defended from crowns where pitch_id = 'demo:victoria-park' and shot_type = 'laces';
select submit_ranked_shot('demo:victoria-park', 'laces', 'runup', 50, 'Good', null, true, 51.5361, -0.0388, 10);
select holder_user_id, holder_shot_id, held_since, times_defended from crowns where pitch_id = 'demo:victoria-park' and shot_type = 'laces';
\echo '(expect: identical to the row printed just above -- Bob''s own non-improving shot is not a "defense")'

\echo '=== final shots + crowns state ==='
select user_id, shot_type, technique_score, is_ranked, created_at from shots order by created_at;
select * from crowns;
