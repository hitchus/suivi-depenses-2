package com.bydcam.app.byd

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.Handler
import android.os.Looper
import android.util.Log
import java.lang.reflect.Method

/**
 * Surveille l'état ACC (Accessory Control Circuit) du véhicule BYD.
 *
 * Deux mécanismes combinés :
 *  1. BroadcastReceiver sur les intents ACC_ON / ACC_OFF
 *  2. Polling Binder sur BYDAutoBodyworkDevice (fallback si les intents sont manqués)
 */
class AccMonitor(private val context: Context) {

    interface Listener {
        fun onAccOn(powerLevel: Int)
        fun onAccOff()
        fun onGearChanged(gear: String)
    }

    private val tag = "AccMonitor"
    private var listener: Listener? = null
    private val handler = Handler(Looper.getMainLooper())

    @Volatile private var currentPowerLevel = BydConstants.POWER_OFF
    @Volatile private var currentGear = BydConstants.GEAR_PARK
    @Volatile private var isRunning = false

    private val accReceiver = object : BroadcastReceiver() {
        override fun onReceive(ctx: Context, intent: Intent) {
            when (intent.action) {
                BydConstants.ACTION_ACC_ON -> {
                    val level = intent.getIntExtra("power_level", BydConstants.POWER_ACC)
                    updatePowerLevel(level)
                }
                BydConstants.ACTION_ACC_OFF -> updatePowerLevel(BydConstants.POWER_OFF)
            }
        }
    }

    // Polling BYD bodywork toutes les 2 secondes (rattrape les intents manqués)
    private val pollRunnable = object : Runnable {
        override fun run() {
            if (!isRunning) return
            try {
                val level = readPowerLevelFromBinder()
                if (level != currentPowerLevel) updatePowerLevel(level)

                val gear = readGearFromBinder()
                if (gear != currentGear) {
                    currentGear = gear
                    listener?.onGearChanged(gear)
                }
            } catch (e: Exception) {
                Log.w(tag, "Binder poll failed: ${e.message}")
            }
            handler.postDelayed(this, POLL_INTERVAL_MS)
        }
    }

    fun start(listener: Listener) {
        this.listener = listener
        isRunning = true

        val filter = IntentFilter().apply {
            addAction(BydConstants.ACTION_ACC_ON)
            addAction(BydConstants.ACTION_ACC_OFF)
        }
        context.registerReceiver(accReceiver, filter)
        handler.post(pollRunnable)
        Log.i(tag, "AccMonitor started")
    }

    fun stop() {
        isRunning = false
        handler.removeCallbacks(pollRunnable)
        try { context.unregisterReceiver(accReceiver) } catch (_: Exception) {}
        listener = null
        Log.i(tag, "AccMonitor stopped")
    }

    fun isPowered() = currentPowerLevel >= BydConstants.POWER_ACC
    fun isEngineOn() = currentPowerLevel >= BydConstants.POWER_ON
    fun getCurrentGear() = currentGear

    private fun updatePowerLevel(level: Int) {
        val previous = currentPowerLevel
        currentPowerLevel = level
        Log.i(tag, "Power level: $previous -> $level")

        if (level >= BydConstants.POWER_ACC && previous < BydConstants.POWER_ACC) {
            listener?.onAccOn(level)
        } else if (level < BydConstants.POWER_ACC && previous >= BydConstants.POWER_ACC) {
            listener?.onAccOff()
        }
    }

    /**
     * Lecture du niveau de puissance via réflexion Binder BYD.
     * Équivalent à BYDAutoBodyworkDevice.getPowerLevel()
     */
    private fun readPowerLevelFromBinder(): Int = try {
        val serviceManager = Class.forName("android.os.ServiceManager")
        val getService = serviceManager.getMethod("getService", String::class.java)
        val binder = getService.invoke(null, BydConstants.SERVICE_BYD_BODYWORK) ?: return currentPowerLevel

        // Appel transact Binder : code 1 = getPowerLevel (identifié par reverse engineering)
        val parcelClass = Class.forName("android.os.Parcel")
        val obtain = parcelClass.getMethod("obtain")
        val data = obtain.invoke(null)
        val reply = obtain.invoke(null)

        val transact = binder.javaClass.getMethod(
            "transact", Int::class.java, parcelClass, parcelClass, Int::class.java
        )
        transact.invoke(binder, 1, data, reply, 0)

        val readInt = parcelClass.getMethod("readInt")
        val level = readInt.invoke(reply) as Int

        (parcelClass.getMethod("recycle")).invoke(data)
        (parcelClass.getMethod("recycle")).invoke(reply)

        level.coerceIn(BydConstants.POWER_OFF, BydConstants.POWER_OK)
    } catch (e: Exception) {
        Log.v(tag, "readPowerLevel fallback: ${e.message}")
        currentPowerLevel
    }

    /**
     * Lecture de la position de levier de vitesse via réflexion Binder BYD.
     */
    private fun readGearFromBinder(): String = try {
        val serviceManager = Class.forName("android.os.ServiceManager")
        val getService = serviceManager.getMethod("getService", String::class.java)
        val binder = getService.invoke(null, BydConstants.SERVICE_BYD_BODYWORK) ?: return currentGear

        val parcelClass = Class.forName("android.os.Parcel")
        val obtain = parcelClass.getMethod("obtain")
        val data = obtain.invoke(null)
        val reply = obtain.invoke(null)

        val transact = binder.javaClass.getMethod(
            "transact", Int::class.java, parcelClass, parcelClass, Int::class.java
        )
        // Code 3 = getGearPosition (identifié par reverse engineering)
        transact.invoke(binder, 3, data, reply, 0)

        val readString = parcelClass.getMethod("readString")
        val gear = readString.invoke(reply) as? String ?: currentGear

        (parcelClass.getMethod("recycle")).invoke(data)
        (parcelClass.getMethod("recycle")).invoke(reply)

        gear
    } catch (e: Exception) {
        currentGear
    }

    companion object {
        private const val POLL_INTERVAL_MS = 2_000L
    }
}
