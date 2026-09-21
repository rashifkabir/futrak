// Drains notification_queue and delivers via Expo Push (the mobile app is
// Expo — Expo Push works over plain HTTP regardless of backend choice, no
// FCM/APNs setup needed). Deploy with `supabase functions deploy
// drain-notifications` and schedule it (e.g. every minute) via Supabase's
// Cron for Edge Functions or a pg_cron + pg_net job calling this URL.
//
// NOT runtime-tested in this session — no Deno available in this sandbox.
// The SQL layer (submit_ranked_shot, which writes the rows this function
// reads) was verified against a real local Postgres; this function itself
// should be smoke-tested after `supabase functions deploy` against a
// staging project before relying on it.

import { createClient } from 'jsr:@supabase/supabase-js@2';

const EXPO_PUSH_URL = 'https://exp.host/--/api/v2/push/send';
const BATCH_SIZE = 100; // Expo's documented max messages per request

Deno.serve(async () => {
  const supabase = createClient(
    Deno.env.get('SUPABASE_URL')!,
    Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!, // bypasses RLS — this function is the trusted drainer
  );

  const { data: rows, error } = await supabase
    .from('notification_queue')
    .select('id, message, profiles(expo_push_token)')
    .is('sent_at', null)
    .limit(500);

  if (error) {
    return new Response(JSON.stringify({ error: error.message }), { status: 500 });
  }
  if (!rows || rows.length === 0) {
    return new Response(JSON.stringify({ sent: 0 }), { status: 200 });
  }

  const deliverable = rows.filter((r) => r.profiles?.expo_push_token);
  const undeliverable = rows.filter((r) => !r.profiles?.expo_push_token);

  let sent = 0;
  for (let i = 0; i < deliverable.length; i += BATCH_SIZE) {
    const batch = deliverable.slice(i, i + BATCH_SIZE);
    const messages = batch.map((r) => ({
      to: r.profiles.expo_push_token,
      title: 'King of the Pitch',
      body: r.message,
      sound: 'default',
    }));

    const res = await fetch(EXPO_PUSH_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(messages),
    });

    if (res.ok) {
      const ids = batch.map((r) => r.id);
      await supabase.from('notification_queue').update({ sent_at: new Date().toISOString() }).in('id', ids);
      sent += batch.length;
    }
    // On failure, rows are left unsent (sent_at still null) so the next
    // scheduled run retries them.
  }

  // No token registered at all (user never opened the app / granted
  // permission) — nothing will ever deliver this, so mark it sent rather
  // than retrying it forever every run.
  if (undeliverable.length > 0) {
    await supabase
      .from('notification_queue')
      .update({ sent_at: new Date().toISOString() })
      .in('id', undeliverable.map((r) => r.id));
  }

  return new Response(JSON.stringify({ sent, skipped_no_token: undeliverable.length }), { status: 200 });
});
