import type { ViewProps } from 'react-native';

export interface HighSpeedCameraViewProps extends ViewProps {
  /** 240 or 120 — the fps negotiated by getMaxSupportedFps(). */
  targetFps: number;
}

/** Imperative methods exposed on a HighSpeedCameraView ref. */
export interface HighSpeedCameraViewRef {
  startRecording(): Promise<void>;
  /** Resolves with the local filesystem path of the recorded .mp4. */
  stopRecording(): Promise<string>;
}
