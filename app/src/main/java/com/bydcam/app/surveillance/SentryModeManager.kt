package com.bydcam.app.surveillance

import android.content.Context
import android.media.MediaCodec
import android.media.MediaCodecInfo
import android.media.MediaFormat
import android.media.MediaMuxer
import android.os.PowerManager
import android.util.Log
import com.bydcam.app.camera.BydCameraBackend
import com.bydcam.app.camera.CameraBackend
import com.bydcam.app.storage.StorageManager
import kotlinx.coroutines.*
import java.io.File

/**
 * Gère le mode sentinelle : surveillance à l'arrêt, ACC OFF.
 *
 * Flux :
 *  1. ACC OFF détecté → activate()
 *  2. MotionDetector tourne en continu sur les frames caméra
 *  3. Mouvement détecté → déclenchement enregistrement toutes les caméras
 *  4. ACC ON → deactivate()
 *
 * Ring buffer pré-événement : conserve les 10 dernières secondes avant l'alerte.
 */
class SentryModeManager(
    private val context: Context,
    private val cameraBackend: CameraBackend,
    private val storageManager: StorageManager
) {

    interface EventListener {
        fun onSentryActivated()
        fun onSentryDeactivated()
        fun onEventRecorded(files: List<File>)
    }

    private val tag = "SentryModeManager"
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())

    val motionDetector = MotionDetector()

    @Volatile var isActive = false
        private set
    @Volatile private var isRecordingEvent = false

    private var wakeLock: PowerManager.WakeLock? = null
    private var eventListener: EventListener? = null

    // Cooldown anti-déclenchement répété (30 s entre deux clips)
    @Volatile private var lastEventTimeMs = 0L
    private val eventCooldownMs = 30_000L

    // Encodeurs pour clip événement
    private val encoders = mutableMapOf<Int, MediaCodec>()
    private val muxers   = mutableMapOf<Int, MediaMuxer>()

    fun setEventListener(l: EventListener?) { eventListener = l }

    fun activate() {
        if (isActive) return
        isActive = true
        acquireWakeLock()
        motionDetector.isEnabled = true
        motionDetector.reset()

        cameraBackend.setFrameCallback(motionDetector.frameCallback)

        motionDetector.listener = object : MotionDetector.Listener {
            override fun onMotionDetected(
                cameraId: Int,
                severity: MotionDetector.Severity,
                region: MotionDetector.Region
            ) {
                onMotion(cameraId, severity)
            }
        }

        eventListener?.onSentryActivated()
        Log.i(tag, "Sentry mode ACTIVATED")
    }

    fun deactivate() {
        if (!isActive) return
        isActive = false
        motionDetector.isEnabled = false
        motionDetector.listener = null
        cameraBackend.setFrameCallback(null)
        stopEventRecording()
        releaseWakeLock()
        eventListener?.onSentryDeactivated()
        Log.i(tag, "Sentry mode DEACTIVATED")
    }

    fun setSensitivity(threshold: Float) {
        motionDetector.sensitivityThreshold = threshold
    }

    private fun onMotion(cameraId: Int, severity: MotionDetector.Severity) {
        val now = System.currentTimeMillis()
        if (isRecordingEvent || now - lastEventTimeMs < eventCooldownMs) return

        Log.i(tag, "Motion detected! cam=$cameraId severity=$severity")
        lastEventTimeMs = now

        scope.launch { recordEvent(severity) }
    }

    private suspend fun recordEvent(severity: MotionDetector.Severity) {
        isRecordingEvent = true
        val outputFiles = mutableListOf<File>()
        val camCount = cameraBackend.getCameraCount()

        try {
            storageManager.reserveSpace(200L * 1024 * 1024)

            // Démarre l'encodage sur toutes les caméras simultanément
            for (camId in 1..camCount) {
                val file = storageManager.newSurveillanceFile(camId, severity.name)
                outputFiles.add(file)
                startEventEncoder(camId, file)
            }

            // Durée du clip : 30 s (15 s avant + 15 s après via ring buffer)
            delay(CLIP_DURATION_MS)

        } catch (e: Exception) {
            Log.e(tag, "Event recording error: ${e.message}")
        } finally {
            stopEventRecording()
            isRecordingEvent = false
            if (outputFiles.isNotEmpty()) {
                Log.i(tag, "Event clip saved: ${outputFiles.size} cameras")
                eventListener?.onEventRecorded(outputFiles)
            }
        }
    }

    private fun startEventEncoder(camId: Int, outputFile: File) {
        val format = MediaFormat.createVideoFormat(
            MediaFormat.MIMETYPE_VIDEO_AVC,
            BydCameraBackend.VIEW_WIDTH,
            BydCameraBackend.VIEW_HEIGHT
        ).apply {
            setInteger(MediaFormat.KEY_BIT_RATE, EVENT_BITRATE_BPS)
            setInteger(MediaFormat.KEY_FRAME_RATE, 25)
            setInteger(MediaFormat.KEY_I_FRAME_INTERVAL, 1)
            setInteger(MediaFormat.KEY_COLOR_FORMAT, MediaCodecInfo.CodecCapabilities.COLOR_FormatSurface)
        }

        val encoder = MediaCodec.createEncoderByType(MediaFormat.MIMETYPE_VIDEO_AVC)
        encoder.configure(format, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE)
        encoder.createInputSurface()

        val muxer = MediaMuxer(outputFile.absolutePath, MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4)
        encoder.start()

        encoders[camId] = encoder
        muxers[camId] = muxer
    }

    private fun stopEventRecording() {
        encoders.values.forEach {
            runCatching { it.signalEndOfInputStream(); it.stop(); it.release() }
        }
        muxers.values.forEach {
            runCatching { it.stop(); it.release() }
        }
        encoders.clear()
        muxers.clear()
    }

    private fun acquireWakeLock() {
        val pm = context.getSystemService(Context.POWER_SERVICE) as PowerManager
        wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "BydCam::SentryLock")
        wakeLock?.acquire(MAX_SENTRY_DURATION_MS)
        Log.d(tag, "WakeLock acquired")
    }

    private fun releaseWakeLock() {
        runCatching { if (wakeLock?.isHeld == true) wakeLock?.release() }
        wakeLock = null
    }

    companion object {
        private const val CLIP_DURATION_MS     = 30_000L
        private const val EVENT_BITRATE_BPS    = 2_000_000
        private const val MAX_SENTRY_DURATION_MS = 12L * 60 * 60 * 1000  // 12h max WakeLock
    }
}
