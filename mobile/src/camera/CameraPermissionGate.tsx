import type { ReactNode } from 'react';
import { useEffect } from 'react';
import { StyleSheet, View } from 'react-native';
import { useCameraPermission } from 'react-native-vision-camera';
import Empty from '../components/Empty';
import { Button } from '../components/chrome';
import { colors } from '../theme';

// Gates camera-dependent screens behind the OS permission prompt. Kept
// separate from CaptureShot so the negotiation/recording logic doesn't
// have to also branch on permission state.
export default function CameraPermissionGate({ children }: { children: ReactNode }) {
  const { hasPermission, requestPermission, canRequestPermission } = useCameraPermission();

  useEffect(() => {
    if (!hasPermission && canRequestPermission) requestPermission();
  }, [hasPermission, canRequestPermission, requestPermission]);

  if (hasPermission) return <>{children}</>;

  return (
    <View style={styles.wrap}>
      <Empty
        title="Camera access needed"
        body={
          canRequestPermission
            ? 'Grant camera access to film your shot.'
            : "Camera access was denied. Enable it for ProPath FC in your phone's Settings app to film a shot."
        }
      />
      {canRequestPermission && (
        <View style={{ marginTop: 14 }}>
          <Button label="Grant camera access" onPress={requestPermission} />
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    flex: 1,
    justifyContent: 'center',
    padding: 20,
    backgroundColor: colors.turf,
  },
});
