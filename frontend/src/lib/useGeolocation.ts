import { useCallback, useEffect, useRef, useState } from 'react';

export type GeoStatus = 'unsupported' | 'prompt' | 'requesting' | 'granted' | 'denied' | 'unavailable';

export interface GeoPosition {
  lat: number;
  lng: number;
  accuracyM: number;
}

export interface GeoState {
  status: GeoStatus;
  position: GeoPosition | null;
  error: string | null;
  requestLocation: () => void;
}

const SUPPORTED = typeof navigator !== 'undefined' && 'geolocation' in navigator;

// Permission + live position for King of the Pitch's geofence check.
// Never auto-prompts on mount — requestLocation() must be triggered by an
// explicit user action so the "why" explanation is always seen first. Once
// granted, watches position continuously (not a one-shot read) so the
// geofence re-evaluates live as the user actually walks to the pitch.
export function useGeolocation(): GeoState {
  const [status, setStatus] = useState<GeoStatus>(SUPPORTED ? 'prompt' : 'unsupported');
  const [position, setPosition] = useState<GeoPosition | null>(null);
  const [error, setError] = useState<string | null>(null);
  const watchId = useRef<number | null>(null);

  const requestLocation = useCallback(() => {
    if (!SUPPORTED) return;
    setStatus('requesting');
    setError(null);
    if (watchId.current !== null) navigator.geolocation.clearWatch(watchId.current);
    watchId.current = navigator.geolocation.watchPosition(
      (pos) => {
        setStatus('granted');
        setPosition({ lat: pos.coords.latitude, lng: pos.coords.longitude, accuracyM: pos.coords.accuracy });
      },
      (err) => {
        if (err.code === err.PERMISSION_DENIED) {
          setStatus('denied');
          setError('Location access was denied.');
        } else if (err.code === err.TIMEOUT) {
          setStatus('unavailable');
          setError('Location request timed out.');
        } else {
          setStatus('unavailable');
          setError('Location is currently unavailable.');
        }
      },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 5000 },
    );
  }, []);

  // Progressive enhancement: if the Permissions API is available, detect an
  // already-decided permission without prompting. Safari lacks this — it
  // just stays in 'prompt' until the user clicks the button, and denial
  // surfaces via requestLocation's own error callback instead.
  useEffect(() => {
    if (!SUPPORTED || !navigator.permissions?.query) return;
    let cancelled = false;
    navigator.permissions
      .query({ name: 'geolocation' })
      .then((result) => {
        if (cancelled) return;
        if (result.state === 'denied') setStatus('denied');
        else if (result.state === 'granted') requestLocation();
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [requestLocation]);

  useEffect(
    () => () => {
      if (watchId.current !== null) navigator.geolocation.clearWatch(watchId.current);
    },
    [],
  );

  return { status, position, error, requestLocation };
}
