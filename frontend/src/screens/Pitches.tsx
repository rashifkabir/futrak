import { useEffect, useMemo, useState } from 'react';
import { MapContainer, TileLayer, Marker, Tooltip, Popup, Circle, CircleMarker } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { MOCK_PITCHES } from '../lib/pitchesMock';
import {
  loadSeededPitches,
  loadUserAddedPitches,
  type CrownState,
  type Pitch,
} from '../lib/pitches';
import { haversineMeters, formatDistance } from '../lib/geo';
import { useGeolocation } from '../lib/useGeolocation';
import Empty from '../components/Empty';
import PitchDetail from './PitchDetail';
import AddPitch from './AddPitch';
import './Pitches.css';

const HOLDER_LABEL: Record<CrownState, (name: string) => string> = {
  mine: () => 'You hold this crown',
  lost: (name) => `${name} holds this crown`,
  other: (name) => `${name} holds this crown`,
  unclaimed: () => 'Unclaimed',
};

// Real map now (Leaflet + CARTO's Positron — a free, no-API-key, light/
// greyscale basemap) so pitches are the only thing that pops off the page,
// per the "realistic map, pitches highlighted, everything else greyish"
// request. Replaces Stage 1's abstract illustrated backdrop, which looked
// sparse once real, dense pitch data was actually flowing through it.
const TILE_URL = 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png';
const TILE_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>';

const CROWN_PATH = 'M4 18L5.5 9 9 13 12 7 15 13 18.5 9 20 18Z';
const CROWN_COLOR: Record<CrownState, string> = {
  mine: 'var(--paint)',
  lost: 'var(--clay)',
  other: 'var(--muted)',
  unclaimed: 'var(--muted2)',
};
// Built once per crown state, not per pin — divIcon objects are cheap to
// reuse and there are only ever 4 states.
const CROWN_ICONS: Record<CrownState, L.DivIcon> = Object.fromEntries(
  (Object.keys(CROWN_COLOR) as CrownState[]).map((state) => [
    state,
    L.divIcon({
      className: 'leaflet-crown-icon',
      html: `<svg width="26" height="26" viewBox="0 0 24 24" style="color:${CROWN_COLOR[state]};filter:drop-shadow(0 1px 2px rgba(0,0,0,.5))"><path d="${CROWN_PATH}" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" ${state === 'unclaimed' ? 'stroke-dasharray="2 2"' : ''}/></svg>`,
      iconSize: [26, 26],
      iconAnchor: [13, 22],
    }),
  ]),
) as Record<CrownState, L.DivIcon>;

// Real seeded data is dense — a London borough alone can have 900+ real
// pitches within 10km of any given point (Hackney Marshes is 50+ pitches
// on its own). No fixed pin cap can both stay small and reliably include
// "the next nearest" real pitch a user might expect (e.g. Mile End Field
// was rank 64 from one test point) — so instead of hiding pins behind a
// cap, only demo pitches + the single nearest pitch get an always-visible
// label; every other pin shows its name/holder/distance in a tap-to-open
// popup instead of a permanent one. That's what actually lets a much
// larger radius stay legible on a real, zoomable map.
const NEARBY_RADIUS_M = 10000;
const MAX_REAL_PINS = 150;

const DEMO_CENTER = {
  lat: MOCK_PITCHES.reduce((sum, p) => sum + p.lat, 0) / MOCK_PITCHES.length,
  lng: MOCK_PITCHES.reduce((sum, p) => sum + p.lng, 0) / MOCK_PITCHES.length,
};

type View = { type: 'map' } | { type: 'detail'; id: string } | { type: 'add' };

// King of the Pitch — map shell. Combines Stage 1/2's demo fixtures (kept
// for crown-state UI), the real OSM seed (lib/pitches.ts, Stage 3), and
// any pitches the player has added themselves (localStorage, no backend
// yet). Positions are real lat/lng on a real map; distances are real,
// computed against the browser's actual geolocation.
export default function Pitches() {
  const [view, setView] = useState<View>({ type: 'map' });
  const [seeded, setSeeded] = useState<Pitch[]>([]);
  const [userAdded, setUserAdded] = useState<Pitch[]>(() => loadUserAddedPitches());
  const geo = useGeolocation();

  useEffect(() => {
    loadSeededPitches().then(setSeeded);
  }, []);

  const allPitches = useMemo(() => [...MOCK_PITCHES, ...seeded, ...userAdded], [seeded, userAdded]);

  const center = geo.position ?? DEMO_CENTER;
  const withDistance = useMemo(
    () => allPitches.map((p) => ({ pitch: p, distanceM: haversineMeters(center, p) })),
    [allPitches, center],
  );
  const sorted = useMemo(() => [...withDistance].sort((a, b) => a.distanceM - b.distanceM), [withDistance]);

  const demoEntries = sorted.filter((e) => e.pitch.source === 'demo');
  const nearbyReal = sorted.filter((e) => e.pitch.source !== 'demo' && e.distanceM <= NEARBY_RADIUS_M);
  const shownReal = nearbyReal.slice(0, MAX_REAL_PINS);
  const visible = [...demoEntries, ...shownReal];
  const hiddenRealCount = nearbyReal.length - shownReal.length;

  const nearestId = geo.position ? sorted[0]?.pitch.id : null;

  // A fixed, reasonably zoomed-in starting view centred on the user (or the
  // demo cluster before location is known) — not auto-fit to every visible
  // pin. With up to 60+ real pins now in range, fitting bounds to all of
  // them would zoom out far enough to cram their permanent labels together
  // on first load. Starting zoomed in and letting the map be zoomed/panned
  // out manually reads much better.
  const initialCenter: [number, number] = [center.lat, center.lng];

  if (view.type === 'detail') {
    const selected = allPitches.find((p) => p.id === view.id);
    if (selected) {
      return <PitchDetail pitch={selected} onBack={() => setView({ type: 'map' })} geo={geo} />;
    }
  }
  if (view.type === 'add') {
    return (
      <AddPitch
        geo={geo}
        allPitches={allPitches}
        onBack={() => setView({ type: 'map' })}
        onAdded={(pitch, existing) => {
          if (!existing) setUserAdded(loadUserAddedPitches());
          setView({ type: 'detail', id: (existing ?? pitch).id });
        }}
      />
    );
  }

  return (
    <>
      <div className="screen-hd">
        <div className="screen-eyebrow">King of the Pitch</div>
        <h1 className="screen-title">Pitches</h1>
      </div>
      <div className="screen-pad">
        <GeoBanner geo={geo} />

        {visible.length === 0 ? (
          <Empty
            title="No pitches nearby"
            body="We haven't mapped any pitches near you yet. Add one yourself, or check back once King of the Pitch launches in your area."
          />
        ) : (
          <>
            <div className="pmap">
              <MapContainer
                center={initialCenter}
                zoom={15}
                style={{ height: '100%', width: '100%' }}
                zoomControl
                scrollWheelZoom
                doubleClickZoom
                touchZoom
                dragging
                minZoom={11}
                maxZoom={19}
              >
                <TileLayer url={TILE_URL} attribution={TILE_ATTRIBUTION} />

                {visible.map(({ pitch: p, distanceM }) => {
                  // Demo pitches (the crown-state showcase, only 4 of them)
                  // and the single nearest pitch stay glanceable with an
                  // always-visible label. Everything else — potentially
                  // dozens on a real map — shows its details in a
                  // tap-to-open popup instead, so the map doesn't drown in
                  // permanent labels the way it would with hundreds of
                  // real pitches in range.
                  const alwaysLabeled = p.source === 'demo' || p.id === nearestId;
                  const labelContent = (
                    <>
                      <div className="pin-name">
                        {p.id === nearestId && <span className="pin-nearest-badge-inline">Nearest</span>}
                        {p.name}
                        {!p.verified && <span className="pin-unverified-badge">Unverified</span>}
                      </div>
                      <div className="pin-holder">
                        {HOLDER_LABEL[p.crownState](p.king?.name ?? '')} · {formatDistance(distanceM)}
                      </div>
                    </>
                  );

                  return (
                    <Marker
                      key={p.id}
                      position={[p.lat, p.lng]}
                      icon={CROWN_ICONS[p.crownState]}
                      eventHandlers={alwaysLabeled ? { click: () => setView({ type: 'detail', id: p.id }) } : {}}
                    >
                      {alwaysLabeled ? (
                        <Tooltip permanent direction="top" offset={[0, -20]} className={`pin-tooltip pin-tooltip-${p.crownState}`}>
                          {labelContent}
                        </Tooltip>
                      ) : (
                        <Popup className={`pin-popup pin-tooltip-${p.crownState}`}>
                          {labelContent}
                          <button className="pin-popup-view" onClick={() => setView({ type: 'detail', id: p.id })}>
                            View pitch →
                          </button>
                        </Popup>
                      )}
                    </Marker>
                  );
                })}

                {geo.position && (
                  <>
                    <Circle
                      center={[geo.position.lat, geo.position.lng]}
                      radius={geo.position.accuracyM}
                      pathOptions={{ color: 'var(--paint)', weight: 1, fillOpacity: 0.08 }}
                    />
                    <CircleMarker
                      center={[geo.position.lat, geo.position.lng]}
                      radius={7}
                      pathOptions={{ color: 'var(--paint)', weight: 2.5, fillColor: 'var(--chalk)', fillOpacity: 1 }}
                    />
                  </>
                )}
              </MapContainer>
            </div>

            <div className="pmap-legend">
              <div className="pmap-legend-item"><span className="pmap-swatch pmap-swatch-mine" />Your crown</div>
              <div className="pmap-legend-item"><span className="pmap-swatch pmap-swatch-lost" />Crown lost</div>
              <div className="pmap-legend-item"><span className="pmap-swatch pmap-swatch-other" />Held by another</div>
              <div className="pmap-legend-item"><span className="pmap-swatch pmap-swatch-unclaimed" />Unclaimed</div>
              {geo.position && <div className="pmap-legend-item"><span className="pmap-swatch pmap-swatch-you" />You</div>}
            </div>

            <p className="pmap-note">
              {hiddenRealCount > 0
                ? `Showing the nearest ${shownReal.length} of ${nearbyReal.length} real pitches within ${NEARBY_RADIUS_M / 1000}km, plus demo pitches. `
                : ''}
              {geo.position ? `Your location accuracy is ±${Math.round(geo.position.accuracyM)}m.` : ''}
            </p>

            <button className="btn btn-ghost add-pitch-btn" onClick={() => setView({ type: 'add' })}>
              + Add a pitch
            </button>
          </>
        )}
      </div>
    </>
  );
}

function GeoBanner({ geo }: { geo: ReturnType<typeof useGeolocation> }) {
  if (geo.status === 'granted') return null;

  if (geo.status === 'prompt') {
    return (
      <div className="card geo-banner">
        <div className="card-t">Enable location</div>
        <div className="card-d">
          We use your location to verify you're at the pitch you're claiming — it's only checked when you try to
          take or defend a crown, or add a new pitch.
        </div>
        <button className="btn" onClick={geo.requestLocation} style={{ marginTop: 10 }}>
          Enable location
        </button>
      </div>
    );
  }

  if (geo.status === 'requesting') {
    return (
      <div className="card geo-banner">
        <div className="card-d">Finding your location…</div>
      </div>
    );
  }

  if (geo.status === 'denied') {
    return (
      <div className="card geo-banner geo-banner-alert">
        <div className="card-t">Location is off</div>
        <div className="card-d">
          You can still browse pitches, but you won't be able to make ranked attempts (Take/Defend the crown) or add
          a new pitch until you allow location for this site in your browser settings.
        </div>
        <button className="btn-ghost geo-retry" onClick={geo.requestLocation}>
          Try again
        </button>
      </div>
    );
  }

  if (geo.status === 'unavailable') {
    return (
      <div className="card geo-banner geo-banner-alert">
        <div className="card-t">Couldn't get your location</div>
        <div className="card-d">{geo.error ?? 'Location is currently unavailable.'}</div>
        <button className="btn" onClick={geo.requestLocation} style={{ marginTop: 10 }}>
          Retry
        </button>
      </div>
    );
  }

  // unsupported
  return (
    <div className="card geo-banner geo-banner-alert">
      <div className="card-t">Location isn't supported here</div>
      <div className="card-d">This browser can't provide location, so ranked attempts aren't available here.</div>
    </div>
  );
}
