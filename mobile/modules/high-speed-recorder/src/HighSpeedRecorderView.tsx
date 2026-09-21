import { requireNativeViewManager } from 'expo-modules-core';
import { forwardRef, useImperativeHandle, useRef } from 'react';
import type { HighSpeedCameraViewProps, HighSpeedCameraViewRef } from './HighSpeedRecorder.types';

// The native view manager exposes startRecording/stopRecording directly as
// callable methods on its ref instance (same pattern expo-camera's CameraView
// uses for recordAsync/stopRecording) — no manual findNodeHandle plumbing.
type NativeRef = HighSpeedCameraViewRef;

const NativeHighSpeedCameraView = requireNativeViewManager<HighSpeedCameraViewProps & { ref?: unknown }>(
  'HighSpeedRecorder',
  'HighSpeedCameraView',
);

export const HighSpeedCameraView = forwardRef<HighSpeedCameraViewRef, HighSpeedCameraViewProps>(
  function HighSpeedCameraView(props, ref) {
    const nativeRef = useRef<NativeRef>(null);

    useImperativeHandle(ref, () => ({
      startRecording: () => nativeRef.current!.startRecording(),
      stopRecording: () => nativeRef.current!.stopRecording(),
    }));

    return <NativeHighSpeedCameraView {...props} ref={nativeRef as never} />;
  },
);
