package com.bydcam.app.recording

import android.content.Context
import android.content.SharedPreferences
import android.media.MediaCodec
import android.media.MediaCodecInfo
import android.media.MediaFormat
import android.media.MediaMuxer
import android.util.Log
import com.bydcam.app.byd.AccMonitor
import com.bydcam.app.byd.BydConstants
import com.bydcam.app.camera.BydCameraBackend
import com.bydcam.app.camera.CameraBackend
import com.bydcam.app.storage.StorageManager
import kotlinx.coroutines.*
import java.io.File

/**
 * Gère les 4 modes d'enregistrement en conduite.
 *
 * Machine d'états : ACC + gear → décide si le pipeline tourne.
 * Résynchronisation périodique toutes les 30 s pour rattraper les états manqués.
 */
class RecordingModeManager(
    private val context: Context,
    private val cameraBackend: CameraBackend,
    private val storageManager: StorageManager
) {

    private val tag = "RecordingModeManager"
    private val prefs: SharedPreferences =
        context.getSharedPreferences("bydcam_config", Context.MODE_PRIVATE)

    @Volatile var currentMode: RecordingMode = loadMode()
        private set

    @Volatile private var isRecording = false
    @Volatile private var accPowered = false
    @Volatile private var currentGear = BydConstants.GEAR_PARK

    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private val encoders = mutableMapOf<Int, MediaCodec>()
    private val muxers = mutableMapOf<Int, MediaMuxer>()

    // Resync périodique (rattrape les activations silencieuses ratées)
    private var resyncJob: Job? = null

    val accListener = object : AccMonitor.Listener {
        override fun onAccOn(powerLevel: Int) {
            Log.i(tag, "ACC ON (level=$powerLevel)")
            accPowered = true
            evaluateState()
        }

        override fun onAccOff() {
            Log.i(tag, "ACC OFF")
            accPowered = false
            stopRecording()
        }

        override fun onGearChanged(gear: String) {
            // Neutral ignoré pour éviter les cycles intempestifs (BYD Auto Hold)
            if (gear == BydConstants.GEAR_NEUTRAL) return
            Log.i(tag, "Gear: $currentGear -> $gear")
            currentGear = gear
            if (accPowered) evaluateState()
        }
    }

    fun setMode(mode: RecordingMode) {
        currentMode = mode
        prefs.edit().putString(PREF_MODE, mode.name).apply()
        Log.i(tag, "Mode set to $mode")
        if (accPowered) evaluateState()
    }

    fun start() {
        startResyncJob()
        Log.i(tag, "RecordingModeManager started (mode=$currentMode)")
    }

    fun stop() {
        resyncJob?.cancel()
        stopRecording()
    }

    fun isRecording() = isRecording

    /**
     * Évalue si l'enregistrement doit être actif selon le mode + état courant.
     */
    private fun evaluateState() {
        val shouldRecord = when (currentMode) {
            RecordingMode.NONE            -> false
            RecordingMode.CONTINUOUS      -> accPowered
            RecordingMode.DRIVE_MODE      -> accPowered && currentGear in BydConstants.DRIVING_GEARS
            RecordingMode.PROXIMITY_GUARD -> accPowered && currentGear != BydConstants.GEAR_PARK
        }

        if (shouldRecord && !isRecording) startRecording()
        else if (!shouldRecord && isRecording) stopRecording()
    }

    private fun startRecording() {
        if (isRecording || currentMode == RecordingMode.NONE) return
        scope.launch {
            try {
                storageManager.reserveSpace(MIN_FREE_BYTES)
                val camCount = cameraBackend.getCameraCount()
                for (camId in 1..camCount) {
                    startEncoderForCamera(camId)
                }
                isRecording = true
                Log.i(tag, "Recording STARTED (mode=$currentMode, gear=$currentGear)")
                scheduleSegmentRotation()
            } catch (e: Exception) {
                Log.e(tag, "Failed to start recording: ${e.message}")
                isRecording = false
            }
        }
    }

    private fun stopRecording() {
        if (!isRecording) return
        scope.launch {
            isRecording = false
            encoders.values.forEach { codec ->
                runCatching { codec.signalEndOfInputStream() }
                runCatching { codec.stop(); codec.release() }
            }
            muxers.values.forEach { muxer ->
                runCatching { muxer.stop(); muxer.release() }
            }
            encoders.clear()
            muxers.clear()
            Log.i(tag, "Recording STOPPED")
            storageManager.runCleanupIfNeeded()
        }
    }

    private fun startEncoderForCamera(camId: Int) {
        val outputFile = storageManager.newRecordingFile(camId)
        val format = MediaFormat.createVideoFormat(
            MediaFormat.MIMETYPE_VIDEO_AVC,
            BydCameraBackend.VIEW_WIDTH,
            BydCameraBackend.VIEW_HEIGHT
        ).apply {
            setInteger(MediaFormat.KEY_BIT_RATE, BITRATE_BPS)
            setInteger(MediaFormat.KEY_FRAME_RATE, FRAME_RATE)
            setInteger(MediaFormat.KEY_I_FRAME_INTERVAL, KEYFRAME_INTERVAL_S)
            setInteger(MediaFormat.KEY_COLOR_FORMAT, MediaCodecInfo.CodecCapabilities.COLOR_FormatSurface)
        }

        val encoder = MediaCodec.createEncoderByType(MediaFormat.MIMETYPE_VIDEO_AVC)
        encoder.configure(format, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE)

        val inputSurface = encoder.createInputSurface()
        // Connecte la surface de l'encodeur au backend caméra
        cameraBackend.getEncoderSurface(camId)

        val muxer = MediaMuxer(outputFile.absolutePath, MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4)
        encoder.start()

        encoders[camId] = encoder
        muxers[camId] = muxer
        Log.d(tag, "Encoder started: cam$camId → ${outputFile.name}")
    }

    /** Rotation de segment toutes les SEGMENT_DURATION_MS. */
    private fun scheduleSegmentRotation() {
        scope.launch {
            while (isRecording) {
                delay(SEGMENT_DURATION_MS)
                if (isRecording) {
                    Log.d(tag, "Segment rotation")
                    stopRecording()
                    startRecording()
                }
            }
        }
    }

    private fun startResyncJob() {
        resyncJob = scope.launch {
            delay(INITIAL_RESYNC_DELAY_MS)
            while (isActive) {
                evaluateState()
                delay(RESYNC_INTERVAL_MS)
            }
        }
    }

    private fun loadMode(): RecordingMode = runCatching {
        RecordingMode.valueOf(prefs.getString(PREF_MODE, RecordingMode.CONTINUOUS.name)!!)
    }.getOrDefault(RecordingMode.CONTINUOUS)

    companion object {
        private const val PREF_MODE              = "recording_mode"
        private const val BITRATE_BPS            = 4_000_000
        private const val FRAME_RATE             = 25
        private const val KEYFRAME_INTERVAL_S    = 2
        private const val SEGMENT_DURATION_MS    = 2L * 60 * 1000   // 2 min
        private const val INITIAL_RESYNC_DELAY_MS = 8_000L
        private const val RESYNC_INTERVAL_MS     = 30_000L
        private const val MIN_FREE_BYTES         = 500L * 1024 * 1024  // 500 MB
    }
}
