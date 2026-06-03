package com.bydcam.app.services

import android.app.Notification
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.os.IBinder
import android.util.Log
import androidx.core.app.NotificationCompat
import com.bydcam.app.BydCamApplication
import com.bydcam.app.R
import com.bydcam.app.byd.AccMonitor
import com.bydcam.app.camera.BydCameraBackend
import com.bydcam.app.recording.RecordingModeManager
import com.bydcam.app.server.HttpServer
import com.bydcam.app.storage.StorageManager
import com.bydcam.app.surveillance.SentryModeManager
import com.bydcam.app.ui.MainActivity

/**
 * Service foreground principal.
 *
 * Cycle de vie :
 *  onStartCommand → ouvre caméra → démarre AccMonitor → démarre HttpServer
 *  AccMonitor.onAccOff → active SentryModeManager
 *  AccMonitor.onAccOn  → désactive SentryMode, reprend RecordingModeManager
 */
class CameraService : Service() {

    private val tag = "CameraService"

    private lateinit var storageManager: StorageManager
    private lateinit var cameraBackend: BydCameraBackend
    private lateinit var recordingManager: RecordingModeManager
    private lateinit var sentryManager: SentryModeManager
    private lateinit var accMonitor: AccMonitor
    private lateinit var httpServer: HttpServer

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        startForeground(NOTIF_ID, buildNotification("BydCam démarré"))
        initComponents()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        Log.i(tag, "CameraService started")
        startComponents()
        return START_STICKY
    }

    override fun onDestroy() {
        super.onDestroy()
        stopComponents()
        Log.i(tag, "CameraService destroyed")
    }

    private fun initComponents() {
        storageManager  = StorageManager(this).also { it.setup() }
        cameraBackend   = BydCameraBackend()
        recordingManager = RecordingModeManager(this, cameraBackend, storageManager)
        sentryManager   = SentryModeManager(this, cameraBackend, storageManager)
        accMonitor      = AccMonitor(this)

        httpServer = HttpServer(
            recordingManager = recordingManager,
            sentryManager    = sentryManager,
            storageManager   = storageManager,
            assetLoader      = { path ->
                runCatching { assets.open(path).readBytes() }.getOrNull()
            }
        )
    }

    private fun startComponents() {
        cameraBackend.open()
        recordingManager.start()

        accMonitor.start(object : AccMonitor.Listener {
            override fun onAccOn(powerLevel: Int) {
                updateNotification("Enregistrement en cours")
                sentryManager.deactivate()
                recordingManager.accListener.onAccOn(powerLevel)
            }
            override fun onAccOff() {
                updateNotification("Sentinelle active")
                recordingManager.accListener.onAccOff()
                sentryManager.activate()
            }
            override fun onGearChanged(gear: String) {
                recordingManager.accListener.onGearChanged(gear)
            }
        })

        runCatching { httpServer.start() }
            .onSuccess { Log.i(tag, "HTTP server on port ${HttpServer.PORT}") }
            .onFailure { Log.e(tag, "HTTP server failed: ${it.message}") }
    }

    private fun stopComponents() {
        runCatching { httpServer.stop() }
        accMonitor.stop()
        recordingManager.stop()
        sentryManager.deactivate()
        cameraBackend.close()
    }

    private fun buildNotification(text: String): Notification {
        val pi = PendingIntent.getActivity(
            this, 0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE
        )
        return NotificationCompat.Builder(this, BydCamApplication.CHANNEL_RECORDING)
            .setContentTitle("BydCam")
            .setContentText(text)
            .setSmallIcon(R.drawable.ic_camera)
            .setContentIntent(pi)
            .setOngoing(true)
            .build()
    }

    private fun updateNotification(text: String) {
        val nm = getSystemService(NOTIFICATION_SERVICE) as android.app.NotificationManager
        nm.notify(NOTIF_ID, buildNotification(text))
    }

    companion object {
        private const val NOTIF_ID = 1001
    }
}
