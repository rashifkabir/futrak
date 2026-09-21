-- Server-side port of frontend/src/lib/geo.ts's haversineMeters and
-- getGeofenceStatus — same formula, same honesty rule (accuracy folded in
-- rather than treating the fix as an exact point). This is what actually
-- closes the gap Stage 2 left open: that version only ever ran client-side.

create function haversine_meters(
  lat1 double precision, lng1 double precision,
  lat2 double precision, lng2 double precision
) returns double precision
language sql immutable
as $$
  select 2 * 6371000 * asin(sqrt(
    sin(radians(lat2 - lat1) / 2) ^ 2 +
    cos(radians(lat1)) * cos(radians(lat2)) * sin(radians(lng2 - lng1) / 2) ^ 2
  ));
$$;

-- Mirrors GeofenceStatus['kind'] in lib/geo.ts exactly: 'in' | 'out' |
-- 'uncertain-boundary' | 'uncertain-weak-signal' | 'no-fix'.
create function geofence_status(
  p_distance_m double precision,
  p_accuracy_m double precision,
  p_radius_m double precision default 50,
  p_max_accuracy_m double precision default 100
) returns text
language sql immutable
as $$
  select case
    when p_distance_m is null or p_accuracy_m is null then 'no-fix'
    when p_accuracy_m > p_max_accuracy_m then 'uncertain-weak-signal'
    when p_distance_m + p_accuracy_m <= p_radius_m then 'in'
    when p_distance_m - p_accuracy_m > p_radius_m then 'out'
    else 'uncertain-boundary'
  end;
$$;
