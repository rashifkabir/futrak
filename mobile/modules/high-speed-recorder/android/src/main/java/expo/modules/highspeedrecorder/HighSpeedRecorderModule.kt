package expo.modules.highspeedrecorder

import android.content.Context
import android.hardware.camera2.CameraCharacteristics
import android.hardware.camera2.CameraManager
import expo.modules.kotlin.exception.Exceptions
import expo.modules.kotlin.functions.Coroutine
import expo.modules.kotlin.modules.Module
import expo.modules.kotlin.modules.ModuleDefinition

// react-native-vision-camera (all versions checked: v2, v4, v5) is built on CameraX on
// Android, and CameraX has never implemented Camera2's constrained high-speed capture
// session — confirmed via the library's own source and maintainer GitHub issue #76. This
// module bypasses it entirely on Android, talking to Camera2 directly, adapted from
// Google's own reference sample (android/camera-samples/Camera2SlowMotion).
class HighSpeedRecorderModule : Module() {
  private val cameraManager: CameraManager
    get() {
      val context = appContext.reactContext ?: throw Exceptions.AppContextLost()
      return context.getSystemService(Context.CAMERA_SERVICE) as CameraManager
    }

  override fun definition() = ModuleDefinition {
    Name("HighSpeedRecorder")

    // Cascades 240fps -> 120fps -> null (no hard-coded fallback), mirroring the
    // JS-side useSlowMoFormat contract exactly. Only reads CameraCharacteristics,
    // no camera device needs to be opened for this check.
    Function("getMaxSupportedFps") {
      findBackCameraId()?.let { cameraId ->
        val map = cameraManager.getCameraCharacteristics(cameraId)
          .get(CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP)
        val ranges = map?.highSpeedVideoFpsRanges ?: emptyArray()
        when {
          ranges.any { it.contains(240) } -> 240
          ranges.any { it.contains(120) } -> 120
          else -> null
        }
      }
    }

    View(HighSpeedCameraView::class) {
      Prop("targetFps") { view: HighSpeedCameraView, fps: Int ->
        view.targetFps = fps
      }

      AsyncFunction("startRecording") Coroutine { view: HighSpeedCameraView ->
        view.startRecording()
      }

      AsyncFunction("stopRecording") Coroutine { view: HighSpeedCameraView ->
        view.stopRecording()
      }

      OnViewDestroys { view: HighSpeedCameraView ->
        view.release()
      }
    }
  }

  private fun findBackCameraId(): String? =
    cameraManager.cameraIdList.firstOrNull { id ->
      cameraManager.getCameraCharacteristics(id)
        .get(CameraCharacteristics.LENS_FACING) == CameraCharacteristics.LENS_FACING_BACK
    }
}
