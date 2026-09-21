import { useState } from 'react';
import type { Pitch } from '../lib/pitches';
import { findNearbyPitch, saveUserAddedPitch } from '../lib/pitches';
import { MAX_USABLE_ACCURACY_M } from '../lib/geo';
import type { GeoState } from '../lib/useGeolocation';
import './AddPitch.css';

interface Props {
  geo: GeoState;
  allPitches: Pitch[];
  onBack: () => void;
  onAdded: (pitch: Pitch, existing?: Pitch) => void;
}

// OSM coverage of informal cages/MUGAs is patchy by nature (crowd-mapped,
// and many are on private estates) — this is a first-class way for players
// to fill real gaps, not an afterthought. "Must be at the location" reuses
// the same honesty rule as Stage 2's geofence: a GPS fix is only usable
// once its accuracy is tight enough to trust (MAX_USABLE_ACCURACY_M) — but
// unlike PitchDetail's check, there's no separate target to measure
// distance to, since the player's own position *is* the new pitch's
// coordinates.
export default function AddPitch({ geo, allPitches, onBack, onAdded }: Props) {
  const [name, setName] = useState('');
  const [overrideDedup, setOverrideDedup] = useState(false);

  const accuratePosition =
    geo.status === 'granted' && geo.position && geo.position.accuracyM <= MAX_USABLE_ACCURACY_M ? geo.position : null;

  const nearby = accuratePosition ? findNearbyPitch(accuratePosition, allPitches, 30) : null;

  function handleSubmit() {
    if (!accuratePosition || !name.trim()) return;
    const pitch: Pitch = {
      id: `user:${crypto.randomUUID()}`,
      name: name.trim(),
      area: 'Added by a player',
      lat: accuratePosition.lat,
      lng: accuratePosition.lng,
      source: 'user',
      verified: false,
      crownState: 'unclaimed',
      king: null,
      challengers: [],
    };
    saveUserAddedPitch(pitch);
    onAdded(pitch);
  }

  return (
    <>
      <div className="screen-hd">
        <button className="pd-back" onClick={onBack}>&lsaquo; Back to Pitches</button>
        <div className="screen-eyebrow">King of the Pitch</div>
        <h1 className="screen-title">Add a pitch</h1>
      </div>
      <div className="screen-pad">
        {!accuratePosition ? (
          <div className="card">
            <div className="card-t">You need to be at the pitch</div>
            <div className="card-d">
              {locationReason(geo)}
            </div>
            {(geo.status === 'prompt' || geo.status === 'unavailable') && (
              <button className="btn" onClick={geo.requestLocation} style={{ marginTop: 10 }}>
                {geo.status === 'prompt' ? 'Enable location' : 'Retry'}
              </button>
            )}
          </div>
        ) : nearby && !overrideDedup ? (
          <div className="card">
            <div className="card-t">There's already a pitch here</div>
            <div className="card-d">
              <strong>{nearby.name}</strong> is already mapped within 30m of where you're standing.
            </div>
            <button className="btn" onClick={() => onAdded(nearby, nearby)} style={{ marginTop: 10 }}>
              View {nearby.name}
            </button>
            <button className="btn-ghost add-pitch-override" onClick={() => setOverrideDedup(true)}>
              No, this is a different pitch
            </button>
          </div>
        ) : (
          <div className="card">
            <div className="card-t">Name this pitch</div>
            <input
              className="add-pitch-input"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Whiston Road Cage"
              maxLength={60}
            />
            <div className="card-d add-pitch-coords">
              This is where you are right now: {accuratePosition.lat.toFixed(5)}, {accuratePosition.lng.toFixed(5)}
              {' '}(±{Math.round(accuratePosition.accuracyM)}m)
            </div>
            <button className="btn" disabled={!name.trim()} onClick={handleSubmit} style={{ marginTop: 10 }}>
              Add pitch
            </button>
            <p className="add-pitch-note">
              New pitches are marked unverified until confirmed by other players.
            </p>
          </div>
        )}
      </div>
    </>
  );
}

function locationReason(geo: GeoState): string {
  switch (geo.status) {
    case 'unsupported':
      return "Your browser doesn't support location, so pitches can't be added here.";
    case 'prompt':
      return 'Enable location so we can confirm the coordinates of the pitch you\'re adding.';
    case 'requesting':
      return 'Finding your location…';
    case 'denied':
      return 'Location access is off. Enable it for this site (see the Pitches screen) to add a pitch.';
    case 'unavailable':
      return geo.error ?? "Couldn't get a location fix. Try again.";
    case 'granted':
      return `GPS signal here is too weak to confirm coordinates (accuracy ±${Math.round(geo.position?.accuracyM ?? 0)}m). Move to an open area and try again.`;
  }
}
