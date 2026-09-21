import { useState } from 'react';
import type { Pitch } from '../lib/pitches';
import { haversineMeters, formatDistance, getGeofenceStatus } from '../lib/geo';
import type { GeoState } from '../lib/useGeolocation';
import { Crown } from '../components/icons';
import Empty from '../components/Empty';
import './PitchDetail.css';

// Detail + challenge view for one pitch. `geo` is lifted from Pitches.tsx
// (one location fix/watch for the whole screen, not one per pitch). The
// Take/Defend button is gated by a real 50m geofence check against that
// fix — see lib/geo.ts's getGeofenceStatus for how accuracy is honestly
// accounted for rather than the position being treated as exact.
export default function PitchDetail({ pitch, onBack, geo }: { pitch: Pitch; onBack: () => void; geo: GeoState }) {
  const [claimed, setClaimed] = useState(false);

  const isMine = pitch.crownState === 'mine';
  const buttonLabel = isMine ? 'Defend the crown' : 'Take the crown';

  const distanceM = geo.position ? haversineMeters(geo.position, pitch) : null;

  let enabled = false;
  let message: string;

  switch (geo.status) {
    case 'unsupported':
      message = "Your browser doesn't support location, so ranked attempts aren't available here.";
      break;
    case 'prompt':
      message = 'Enable location on the Pitches screen to make a ranked attempt here.';
      break;
    case 'requesting':
      message = 'Finding your location…';
      break;
    case 'denied':
      message = 'Location access is off. Enable it for this site (see the Pitches screen) to make ranked attempts.';
      break;
    case 'unavailable':
      message = geo.error ?? "Couldn't get a location fix. Try again from the Pitches screen.";
      break;
    case 'granted': {
      const gf = getGeofenceStatus(distanceM, geo.position?.accuracyM ?? null);
      switch (gf.kind) {
        case 'in':
          enabled = true;
          message = `You're at ${pitch.name} — ranked attempts are available.`;
          break;
        case 'out':
          message = `You need to be at ${pitch.name} to make a ranked attempt — you're ${formatDistance(gf.distanceM)} away.`;
          break;
        case 'uncertain-boundary':
          message = `You're close, but GPS can't confirm you're within ${formatDistance(50)} here (accuracy ±${Math.round(gf.accuracyM)}m). Move closer to the pitch centre and try again.`;
          break;
        case 'uncertain-weak-signal':
          message = `GPS signal here is too weak to verify your location (accuracy ±${Math.round(gf.accuracyM)}m). Move to an open area and try again.`;
          break;
        case 'no-fix':
          message = 'Waiting for a location fix…';
          break;
      }
      break;
    }
  }

  return (
    <>
      <div className="screen-hd">
        <button className="pd-back" onClick={onBack}>&lsaquo; Back to Pitches</button>
        <div className="screen-eyebrow">
          {pitch.area}
          {!pitch.verified && <span className="unverified-tag">Unverified</span>}
        </div>
        <h1 className="screen-title">{pitch.name}</h1>
      </div>
      <div className="screen-pad">
        <div className="sect-label">Current king</div>
        {pitch.king ? (
          <div className="card king-card">
            <div className="king-card-hd">
              <Crown className={`king-crown king-crown-${pitch.crownState}`} />
              <div>
                <div className="card-t">{pitch.king.name}</div>
                <div className="card-d">{pitch.king.band ?? 'Unbanded'}{pitch.king.power !== null ? ` · Power ${pitch.king.power}` : ''}</div>
              </div>
            </div>
            <div className="king-stats">
              <div className="king-stat">
                <div className="card-k">Held for</div>
                <div className="card-t tabnum">{pitch.king.heldSinceDays} day{pitch.king.heldSinceDays === 1 ? '' : 's'}</div>
              </div>
              <div className="king-stat">
                <div className="card-k">Defended</div>
                <div className="card-t tabnum">{pitch.king.timesDefended} time{pitch.king.timesDefended === 1 ? '' : 's'}</div>
              </div>
            </div>
          </div>
        ) : (
          <Empty title="No one holds this crown yet" body="This pitch hasn't been claimed. Be the first to take it." />
        )}

        <div className="sect-label">Challengers</div>
        {pitch.challengers.length === 0 ? (
          <p className="chal-empty">No challengers yet.</p>
        ) : (
          <div className="card chal-list">
            {pitch.challengers.map(c => (
              <div key={c.rank} className="chal-row">
                <span className="chal-rank tabnum">#{c.rank}</span>
                <span className="chal-name">{c.name}</span>
                <span className="chal-band">{c.band ?? 'Unbanded'}</span>
                <span className="chal-power tabnum">{c.power ?? '—'}</span>
              </div>
            ))}
          </div>
        )}

        <div className="sect-label">Challenge</div>
        <div className="card">
          <p className={`geofence-msg ${enabled ? 'geofence-msg-ok' : ''}`}>{message}</p>

          <button className="btn" disabled={!enabled || claimed} onClick={() => setClaimed(true)} style={{ marginTop: 4 }}>
            {buttonLabel}
          </button>

          {claimed && (
            <p className="claim-confirm">
              Challenge recorded (mock) — real submission lands once the backend is built.
            </p>
          )}
        </div>
      </div>
    </>
  );
}
