package expo.modules.highspeedrecorder

import android.annotation.SuppressLint
import android.content.Context
import android.hardware.camera2.CameraCaptureSession
import android.hardware.camera2.CameraCharacteristics
import android.hardware.camera2.CameraConstrainedHighSpeedCaptureSession
import android.hardware.camera2.CameraDevice
import android.hardware.camera2.CameraManager
import android.hardware.camera2.CaptureRequest
import android.hardware.camera2.params.StreamConfigurationMap
import android.media.MediaCodec
import android.media.MediaRecorder
import android.os.Handler
import android.os.HandlerThread
import android.util.Log
import android.util.Range
import android.util.Size
import android.view.Surface
import android.view.SurfaceHolder
import android.view.SurfaceView
import android.view.ViewGroup
import expo.modules.kotlin.AppContext
import expo.modules.kotlin.exception.Exceptions
import expo.modules.kotlin.views.ExpoView
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeout
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

// Adapted from Google's official reference sample:
// android/camera-samples/Camera2SlowMotion/.../fragments/CameraFragment.kt
// (fetched and read in full while planning this module). Same core sequence —
// createConstrainedHighSpeedCaptureSession, createHighSpeedRequestList, a
// MediaRecorder fed via a persistent input Surface — re-hosted inside an
// Expo native View instead of a Fragment, and video-only (no audio source/
// encoder, matching this app's existing no-mic-permission decision).
class HighSpeedCameraView(context: Context, appContext: AppContext) : ExpoView(context, appContext) {
  private val cameraManager: CameraManager
    get() = context.getSystemService(Context.CAMERA_SERVICE) as CameraManager

  private val surfaceView = SurfaceView(context).also {
    addView(it, ViewGroup.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT))
  }

  private val cameraThread = HandlerThread("HighSpeedCameraThread").apply { start() }
  private val cameraHandler = Handler(cameraThread.looper)
  private val scope = CoroutineScope(Dispatchers.Main)

  private var camera: CameraDevice? = null
  private var session: CameraConstrainedHighSpeedCaptureSession? = null
  private var recordingSize: Size? = null
  private var recorderSurface: Surface? = null
  private var recorder: MediaRecorder? = null
  private var outputFile: File? = null
  private var cameraInitStarted = false
  // startRecording() awaits this instead of failing fast, since the JS side shows the
  // record button as soon as the view mounts, while opening the camera + building the
  // high-speed session (initializeCamera, below) is genuinely async and can take a
  // noticeable moment — a tap that lands before it resolves used to throw "Camera not
  // ready yet" instead of just waiting.
  private val readyDeferred = CompletableDeferred<Unit>()

  /** Set by JS via the `targetFps` prop before/around mount time — 240 or 120. */
  var targetFps: Int = 0
    set(value) {
      field = value
      computeRecordingSizeAndFixSurface()
    }

  init {
    surfaceView.holder.addCallback(object : SurfaceHolder.Callback {
      override fun surfaceCreated(holder: SurfaceHolder) = Unit
      // Only proceed once Android confirms (via these actual callback params) that the
      // surface's buffer has been resized to exactly the chosen high-speed recording
      // size — see the comment on setFixedSize below for why this matters.
      override fun surfaceChanged(holder: SurfaceHolder, format: Int, width: Int, height: Int) {
        val size = recordingSize ?: return
        if (width == size.width && height == size.height) maybeStartCameraInit()
      }
      override fun surfaceDestroyed(holder: SurfaceHolder) = Unit
    })
  }

  // Computed as soon as targetFps is known — this only needs CameraCharacteristics, not
  // the surface, so it can run regardless of whether the prop or the surface arrives
  // first. Every surface in a high-speed session (preview + recorder) must match one of
  // the device's high-speed-eligible sizes exactly, or session creation throws
  // IllegalArgumentException — a SurfaceView otherwise defaults to its laid-out pixel
  // size (e.g. full-screen 1080x2127), which is never one of those sizes.
  private fun computeRecordingSizeAndFixSurface() {
    if (recordingSize != null || targetFps == 0) return
    val cameraId = findBackCameraId()
    val configMap = cameraManager.getCameraCharacteristics(cameraId)
      .get(CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP) ?: return
    val size = pickRecordingSize(configMap, targetFps)
    recordingSize = size
    // Decouples the buffer size from the View's layout size. Triggers a
    // surfaceChanged callback once the resize actually takes effect, which is what
    // maybeStartCameraInit waits on above rather than assuming a fixed delay is enough.
    surfaceView.holder.setFixedSize(size.width, size.height)
    maybeStartCameraInit()
  }

  private fun maybeStartCameraInit() {
    val size = recordingSize ?: return
    if (cameraInitStarted) return
    val frame = surfaceView.holder.surfaceFrame
    if (frame.width() != size.width || frame.height() != size.height) return
    cameraInitStarted = true
    scope.launch { initializeCamera() }
  }

  private fun findBackCameraId(): String =
    cameraManager.cameraIdList.firstOrNull { id ->
      cameraManager.getCameraCharacteristics(id)
        .get(CameraCharacteristics.LENS_FACING) == CameraCharacteristics.LENS_FACING_BACK
    } ?: throw Exceptions.AppContextLost()

  /** Largest resolution the device can do at [fps], intersected with the high-speed-eligible sizes. */
  private fun pickRecordingSize(configMap: StreamConfigurationMap, fps: Int): Size {
    val fpsRange = Range(fps, fps)
    return configMap.getHighSpeedVideoSizesFor(fpsRange)
      .maxByOrNull { it.width.toLong() * it.height } ?: throw IllegalStateException(
      "Device reported support for ${fps}fps but no matching high-speed video size"
    )
  }

  private fun createFile(): File {
    val sdf = SimpleDateFormat("yyyy_MM_dd_HH_mm_ss_SSS", Locale.US)
    return File(context.cacheDir, "shot_${sdf.format(Date())}.mp4")
  }

  /** Video-only MediaRecorder — no audio source/encoder (matches this app's no-mic-permission setup). */
  private fun createRecorder(surface: Surface, size: Size, fps: Int) = MediaRecorder().apply {
    setVideoSource(MediaRecorder.VideoSource.SURFACE)
    setOutputFormat(MediaRecorder.OutputFormat.MPEG_4)
    setOutputFile(outputFile!!.absolutePath)
    setVideoEncodingBitRate(RECORDER_VIDEO_BITRATE)
    setVideoFrameRate(fps)
    setVideoSize(size.width, size.height)
    setVideoEncoder(MediaRecorder.VideoEncoder.H264)
    setInputSurface(surface)
  }

  private suspend fun initializeCamera() {
    try {
      val cameraId = findBackCameraId()
      val size = recordingSize ?: throw IllegalStateException("recordingSize not set")
      outputFile = createFile()

      val persistentSurface = MediaCodec.createPersistentInputSurface()
      recorderSurface = persistentSurface
      // Prepare+release a dummy recorder first to allocate a correctly sized buffer,
      // required before the surface can be used as a high-speed session output target.
      createRecorder(persistentSurface, size, targetFps).apply {
        prepare()
        release()
      }
      recorder = createRecorder(persistentSurface, size, targetFps)

      val device = openCamera(cameraId)
      camera = device

      val targets = listOf(surfaceView.holder.surface, persistentSurface)
      val newSession = createHighSpeedSession(device, targets)
      session = newSession

      val previewRequest = device.createCaptureRequest(CameraDevice.TEMPLATE_PREVIEW).apply {
        addTarget(surfaceView.holder.surface)
        set(CaptureRequest.CONTROL_AE_TARGET_FPS_RANGE, Range(FPS_PREVIEW_ONLY, targetFps))
      }.build()
      newSession.setRepeatingBurst(newSession.createHighSpeedRequestList(previewRequest), null, cameraHandler)
      readyDeferred.complete(Unit)
    } catch (e: Throwable) {
      Log.e(TAG, "Failed to initialize high-speed camera", e)
      readyDeferred.completeExceptionally(e)
    }
  }

  suspend fun startRecording() {
    withTimeout(10_000) { readyDeferred.await() }
    startRecordingInternal()
  }

  // MediaRecorder.prepare()/start()/stop() can block briefly on encoder/file I/O setup —
  // dispatched off the main thread, same as Google's reference sample does
  // (lifecycleScope.launch(Dispatchers.IO) around this exact sequence), since Expo runs
  // View AsyncFunctions on the main thread by default.
  private suspend fun startRecordingInternal() = withContext(Dispatchers.IO) {
    // readyDeferred only completes after these are all assigned in initializeCamera(),
    // so these are non-null by construction — the throw is an unreachable safety net.
    val device = camera ?: throw IllegalStateException("Camera not ready yet")
    val activeSession = session ?: throw IllegalStateException("Camera not ready yet")
    val activeRecorder = recorder ?: throw IllegalStateException("Camera not ready yet")
    val persistentSurface = recorderSurface ?: throw IllegalStateException("Camera not ready yet")

    activeSession.stopRepeating()
    val recordRequest = device.createCaptureRequest(CameraDevice.TEMPLATE_RECORD).apply {
      addTarget(surfaceView.holder.surface)
      addTarget(persistentSurface)
      set(CaptureRequest.CONTROL_AE_TARGET_FPS_RANGE, Range(targetFps, targetFps))
    }.build()
    activeSession.setRepeatingBurst(activeSession.createHighSpeedRequestList(recordRequest), null, cameraHandler)

    activeRecorder.prepare()
    activeRecorder.start()
  }

  suspend fun stopRecording(): String = withContext(Dispatchers.IO) {
    val activeRecorder = recorder ?: throw IllegalStateException("Not recording")
    activeRecorder.stop()
    outputFile?.absolutePath ?: throw IllegalStateException("No output file")
  }

  fun release() {
    try { session?.stopRepeating() } catch (e: Throwable) { Log.e(TAG, "stopRepeating failed", e) }
    session?.close()
    camera?.close()
    recorder?.release()
    recorderSurface?.release()
    cameraThread.quitSafely()
  }

  @SuppressLint("MissingPermission")
  private suspend fun openCamera(cameraId: String): CameraDevice = suspendCancellableCoroutine { cont ->
    cameraManager.openCamera(cameraId, object : CameraDevice.StateCallback() {
      override fun onOpened(device: CameraDevice) = cont.resume(device)
      override fun onDisconnected(device: CameraDevice) {
        Log.w(TAG, "Camera $cameraId disconnected")
      }
      override fun onError(device: CameraDevice, error: Int) {
        val exc = RuntimeException("Camera $cameraId error: $error")
        Log.e(TAG, exc.message, exc)
        if (cont.isActive) cont.resumeWithException(exc)
      }
    }, cameraHandler)
  }

  private suspend fun createHighSpeedSession(
    device: CameraDevice,
    targets: List<Surface>
  ): CameraConstrainedHighSpeedCaptureSession = suspendCancellableCoroutine { cont ->
    device.createConstrainedHighSpeedCaptureSession(
      targets,
      object : CameraCaptureSession.StateCallback() {
        override fun onConfigured(session: CameraCaptureSession) =
          cont.resume(session as CameraConstrainedHighSpeedCaptureSession)
        override fun onConfigureFailed(session: CameraCaptureSession) {
          val exc = RuntimeException("Camera ${device.id} session configuration failed")
          Log.e(TAG, exc.message, exc)
          cont.resumeWithException(exc)
        }
      },
      cameraHandler
    )
  }

  companion object {
    private const val TAG = "HighSpeedCameraView"
    private const val RECORDER_VIDEO_BITRATE = 10_000_000
    /** 30fps is *guaranteed* by the framework for preview-only high-speed requests. */
    private const val FPS_PREVIEW_ONLY = 30
  }
}
