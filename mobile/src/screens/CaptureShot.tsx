import { useRef, useState } from 'react';
import { Platform, Pressable, StyleSheet, Text, View } from 'react-native';
import {
  Camera,
  CommonResolutions,
  type CameraRef,
  type Recorder,
} from 'react-native-vision-camera';
import { useVideoOutput } from 'react-native-vision-camera';
import Empty from '../components/Empty';
import { Button } from '../components/chrome';
import CameraPermissionGate from '../camera/CameraPermissionGate';
import { useSlowMoFormat } from '../camera/useSlowMoFormat';
import { HighSpeedCameraView, type HighSpeedCameraViewRef } from '../../modules/high-speed-recorder/src';
import { uploadShotForAnalysis, type ShootingAnalysisResponse } from '../lib/api';
import type { Condition, ShotType } from '../lib/data';
import { colors, fonts } from '../theme';

type Phase = 'idle' | 'recording' | 'uploading' | 'error' | { done: ShootingAnalysisResponse };

function CaptureInner({
  onBack,
  shotType,
  condition,
}: {
  onBack: () => void;
  shotType: ShotType;
  condition: Condition;
}) {
  const slowMo = useSlowMoFormat();
  const iosCameraRef = useRef<CameraRef>(null);
  const iosRecorderRef = useRef<Recorder | null>(null);
  const androidCameraRef = useRef<HighSpeedCameraViewRef>(null);
  const [phase, setPhase] = useState<Phase>('idle');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // useVideoOutput is a vision-camera hook — harmless to call unconditionally
  // even on Android where it ends up unused, since Android renders
  // HighSpeedCameraView instead and never reads `videoOutput`.
  const videoOutput = useVideoOutput({
    targetResolution: CommonResolutions.FHD_16_9,
    enableAudio: false,
  });

  if (slowMo.status === 'checking') {
    return (
      <View style={styles.center}>
        <Text style={styles.centerText}>Checking camera capabilities…</Text>
      </View>
    );
  }

  // Hard reject per spec: 240fps, else 120fps, else no filming — never a
  // silent fallback to whatever default fps the device offers, since the
  // kinetic-chain timing this analysis relies on assumes a slow-mo capture.
  if (slowMo.status === 'unsupported') {
    return (
      <View style={styles.center}>
        <Empty
          title="Slow-motion capture not supported"
          body="This device can't record at 240fps or 120fps, which this analysis needs to measure contact-frame timing accurately. Try a different device, or check for an iOS/Android update that adds slow-mo support."
        />
        <View style={{ marginTop: 14 }}>
          <Button label="Back" onPress={onBack} ghost />
        </View>
      </View>
    );
  }

  const { targetFps } = slowMo;

  async function handleRecordPress() {
    if (phase === 'idle') {
      setPhase('recording');
      if (Platform.OS === 'android') {
        await androidCameraRef.current?.startRecording();
        return;
      }
      const recorder = await videoOutput.createRecorder({});
      iosRecorderRef.current = recorder;
      await recorder.startRecording(
        async (filePath) => {
          setPhase('uploading');
          try {
            const result = await uploadShotForAnalysis(`file://${filePath}`, shotType, condition);
            setPhase({ done: result });
          } catch (err) {
            setErrorMessage(err instanceof Error ? err.message : 'Upload failed');
            setPhase('error');
          }
        },
        (error) => {
          setErrorMessage(error.message);
          setPhase('error');
        },
      );
    } else if (phase === 'recording') {
      if (Platform.OS === 'android') {
        setPhase('uploading');
        try {
          const filePath = await androidCameraRef.current!.stopRecording();
          const result = await uploadShotForAnalysis(`file://${filePath}`, shotType, condition);
          setPhase({ done: result });
        } catch (err) {
          setErrorMessage(err instanceof Error ? err.message : 'Upload failed');
          setPhase('error');
        }
        return;
      }
      await iosRecorderRef.current?.stopRecording();
    }
  }

  if (typeof phase === 'object' && 'done' in phase) {
    return (
      <View style={styles.center}>
        <Empty
          title={phase.done.success ? 'Clip uploaded' : 'Analysis failed'}
          body={
            phase.done.success
              ? `Technique score: ${phase.done.technique_score ?? '—'}${
                  phase.done.power_grade != null ? ` · Power: ${phase.done.power_grade}` : ''
                }`
              : (phase.done.error ?? 'Unknown error')
          }
        />
        <View style={{ marginTop: 14 }}>
          <Button label="Done" onPress={onBack} />
        </View>
      </View>
    );
  }

  if (phase === 'error') {
    return (
      <View style={styles.center}>
        <Empty title="Something went wrong" body={errorMessage ?? 'Unknown error'} />
        <View style={{ marginTop: 14 }}>
          <Button label="Back" onPress={onBack} ghost />
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {Platform.OS === 'android' ? (
        <HighSpeedCameraView
          ref={androidCameraRef}
          targetFps={targetFps}
          style={StyleSheet.absoluteFill}
        />
      ) : (
        <Camera
          ref={iosCameraRef}
          style={StyleSheet.absoluteFill}
          device={slowMo.visionCamera!.device}
          isActive={true}
          outputs={[videoOutput]}
          constraints={slowMo.visionCamera!.constraints}
        />
      )}
      <View style={styles.overlay}>
        <Text style={styles.fpsTag}>{targetFps}fps slow-mo</Text>
        {phase === 'uploading' ? (
          <Text style={styles.fpsTag}>Uploading…</Text>
        ) : (
          <Pressable
            onPress={handleRecordPress}
            style={[styles.recordBtn, phase === 'recording' && styles.recordBtnActive]}
          />
        )}
        <Pressable onPress={onBack}><Text style={styles.backLink}>Back to guide</Text></Pressable>
      </View>
    </View>
  );
}

// CameraPermissionGate wraps the whole capture flow — negotiation and
// recording both assume permission is already granted.
export default function CaptureShot({
  onBack,
  shotType,
  condition,
}: {
  onBack: () => void;
  shotType: ShotType;
  condition: Condition;
}) {
  return (
    <CameraPermissionGate>
      <CaptureInner onBack={onBack} shotType={shotType} condition={condition} />
    </CameraPermissionGate>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#000' },
  center: {
    flex: 1,
    justifyContent: 'center',
    padding: 20,
    backgroundColor: colors.turf,
  },
  centerText: { fontFamily: fonts.body, color: colors.chalk, textAlign: 'center' },
  overlay: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    alignItems: 'center',
    paddingBottom: 40,
    paddingTop: 20,
    gap: 14,
  },
  fpsTag: {
    fontFamily: fonts.displayBold,
    color: colors.paint,
    fontSize: 12,
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  recordBtn: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: colors.clay,
    borderWidth: 4,
    borderColor: colors.chalk,
  },
  recordBtnActive: {
    borderRadius: 12,
    backgroundColor: '#c0392b',
  },
  backLink: {
    fontFamily: fonts.displayBold,
    color: colors.chalk,
    fontSize: 12,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
});
