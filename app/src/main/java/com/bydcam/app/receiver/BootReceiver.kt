package com.bydcam.app.receiver

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log
import com.bydcam.app.byd.BydConstants
import com.bydcam.app.services.CameraService

/**
 * Démarre CameraService au boot système et sur les événements ACC BYD.
 */
class BootReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        Log.i("BootReceiver", "Received: ${intent.action}")
        when (intent.action) {
            Intent.ACTION_BOOT_COMPLETED,
            Intent.ACTION_LOCKED_BOOT_COMPLETED,
            BydConstants.ACTION_ACC_ON -> startService(context)
        }
    }

    private fun startService(context: Context) {
        val intent = Intent(context, CameraService::class.java)
        context.startForegroundService(intent)
    }
}
