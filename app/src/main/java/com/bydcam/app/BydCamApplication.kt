package com.bydcam.app

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build

class BydCamApplication : Application() {

    companion object {
        const val CHANNEL_RECORDING = "bydcam_recording"
        const val CHANNEL_SENTRY    = "bydcam_sentry"
    }

    override fun onCreate() {
        super.onCreate()
        createNotificationChannels()
    }

    private fun createNotificationChannels() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val nm = getSystemService(NotificationManager::class.java)
            nm.createNotificationChannel(
                NotificationChannel(CHANNEL_RECORDING, "Enregistrement", NotificationManager.IMPORTANCE_LOW)
            )
            nm.createNotificationChannel(
                NotificationChannel(CHANNEL_SENTRY, "Sentinelle", NotificationManager.IMPORTANCE_DEFAULT)
            )
        }
    }
}
