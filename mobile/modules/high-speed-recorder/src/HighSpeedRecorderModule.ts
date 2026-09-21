import { NativeModule, requireNativeModule } from 'expo';

declare class HighSpeedRecorderModule extends NativeModule<{}> {
  /**
   * Cascades 240fps -> 120fps -> null, reading Camera2's
   * StreamConfigurationMap.getHighSpeedVideoFPSRanges() directly (bypassing
   * react-native-vision-camera/CameraX, which never exposes this).
   */
  getMaxSupportedFps(): 240 | 120 | null;
}

export default requireNativeModule<HighSpeedRecorderModule>('HighSpeedRecorder');
