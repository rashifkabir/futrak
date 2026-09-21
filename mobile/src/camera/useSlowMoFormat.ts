import { useState } from 'react';
import { Platform } from 'react-native';
import { useCameraDevice, type CameraDevice, type Constraint } from 'react-native-vision-camera';
import { HighSpeedRecorderModule } from '../../modules/high-speed-recorder/src';

export type SlowMoResult =
  | { status: 'checking' }
  | { status: 'unsupported' }
  | {
      status: 'ready';
      targetFps: 240 | 120;
      // Only populated on iOS, where vision-camera's Constraint model still
      // works (AVFoundation exposes real high-fps ranges there). On Android
      // this is null — CaptureShot renders the custom HighSpeedCameraView
      // instead, which only needs targetFps.
      visionCamera: { device: CameraDevice; constraints: Constraint[] } | null;
    };

// Per spec: 240fps, else 120fps, else a hard reject — no silent fallback to
// whatever default fps the device offers.
//
// iOS: react-native-vision-camera v5 has no `device.formats` array /
// useCameraFormat hook (that's the older v3/v4 API) — it replaced format
// selection with a declarative Constraint model. `device.supportsFPS(n)`
// tells us upfront whether a fixed frame rate is achievable at all, and
// AVFoundation genuinely exposes 240fps/120fps ranges there.
//
// Android: vision-camera is built on CameraX, which has never implemented
// Camera2's constrained high-speed capture session (verified against the
// library's own source across v2/v4/v5, and the maintainer's GitHub issue
// #76) — so `device.supportsFPS(240/120)` would always report false here,
// regardless of what the hardware can actually do. The custom
// HighSpeedRecorder native module (modules/high-speed-recorder) queries
// Camera2 directly instead.
export function useSlowMoFormat(): SlowMoResult {
  // Platform.OS is fixed for the app's entire lifetime (never toggles between
  // renders), so branching hook calls on it is safe despite looking like a
  // conditional-hooks violation.
  if (Platform.OS === 'android') {
    return useAndroidSlowMoFormat();
  }
  return useIosSlowMoFormat();
}

function useAndroidSlowMoFormat(): SlowMoResult {
  const [maxFps] = useState(() => HighSpeedRecorderModule.getMaxSupportedFps());
  if (maxFps === null) return { status: 'unsupported' };
  return { status: 'ready', targetFps: maxFps, visionCamera: null };
}

function useIosSlowMoFormat(): SlowMoResult {
  const device = useCameraDevice('back');

  if (!device) return { status: 'checking' };

  if (device.supportsFPS(240)) {
    return { status: 'ready', targetFps: 240, visionCamera: { device, constraints: [{ fps: 240 }] } };
  }
  if (device.supportsFPS(120)) {
    return { status: 'ready', targetFps: 120, visionCamera: { device, constraints: [{ fps: 120 }] } };
  }
  return { status: 'unsupported' };
}
