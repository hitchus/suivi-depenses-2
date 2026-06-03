package com.bydcam.app.diag

import android.os.IBinder
import android.os.Parcel
import android.util.Log

/**
 * Sonde systématiquement les services Binder BYD.
 *
 * Pour chaque service cible, itère sur les codes transact 1..MAX_CODE
 * et log la réponse brute. Les codes qui retournent des données cohérentes
 * sont les candidats pour getPowerLevel(), getGear(), etc.
 *
 * Usage : lancer depuis DiagnosticActivity sur la head unit BYD.
 */
object BydServiceProbe {

    private const val TAG = "BydServiceProbe"
    private const val MAX_CODE = 30

    // Services BYD à sonder
    val TARGET_SERVICES = listOf(
        "byd_bodywork",
        "byd_avm",
        "byd_datacached",
        "bg_datacache",
        "accmodemanager",
        "byd_avc",
        "byd_vehicle",
        "byd_engine",
        "byd_bms",
        "CarService",
    )

    data class ProbeResult(
        val service: String,
        val code: Int,
        val status: Status,
        val intValues: List<Int>,
        val stringValues: List<String>,
        val rawHex: String,
        val errorMsg: String = ""
    )

    enum class Status { OK, SECURITY_EXCEPTION, REMOTE_EXCEPTION, EMPTY, ERROR }

    // ── Entrée principale ─────────────────────────────────────────────────

    fun probeAll(onResult: (ProbeResult) -> Unit) {
        Log.i(TAG, "=== BYD Binder Probe START ===")

        val available = listAvailableServices()
        Log.i(TAG, "Services disponibles sur ce système :")
        available.forEach { Log.i(TAG, "  → $it") }

        for (serviceName in TARGET_SERVICES) {
            if (!available.contains(serviceName)) {
                Log.w(TAG, "[$serviceName] NON TROUVÉ dans ServiceManager")
                continue
            }
            probeService(serviceName, onResult)
        }

        Log.i(TAG, "=== BYD Binder Probe END ===")
    }

    /**
     * Liste tous les services enregistrés dans ServiceManager.
     * Utile pour découvrir des services BYD non documentés.
     */
    fun listAvailableServices(): List<String> = try {
        val sm = Class.forName("android.os.ServiceManager")
        val listServices = sm.getMethod("listServices")
        @Suppress("UNCHECKED_CAST")
        (listServices.invoke(null) as? Array<String>)
            ?.filter { it.contains("byd", ignoreCase = true) ||
                       it.contains("acc", ignoreCase = true) ||
                       it.contains("avm", ignoreCase = true) ||
                       it.contains("car", ignoreCase = true) ||
                       it.contains("vehicle", ignoreCase = true) }
            ?.sorted() ?: emptyList()
    } catch (e: Exception) {
        Log.e(TAG, "listServices failed: ${e.message}")
        emptyList()
    }

    fun probeService(serviceName: String, onResult: (ProbeResult) -> Unit) {
        val binder = getService(serviceName)
        if (binder == null) {
            Log.w(TAG, "[$serviceName] binder null")
            return
        }

        Log.i(TAG, "[$serviceName] Sonding codes 1..$MAX_CODE ...")

        for (code in 1..MAX_CODE) {
            val result = transact(binder, serviceName, code)
            onResult(result)

            // Log uniquement les résultats intéressants
            when (result.status) {
                Status.OK -> Log.i(TAG,
                    "[$serviceName] code=$code ✓ ints=${result.intValues} " +
                    "strings=${result.stringValues} hex=${result.rawHex}")
                Status.SECURITY_EXCEPTION -> Log.w(TAG,
                    "[$serviceName] code=$code ⛔ SECURITY: ${result.errorMsg}")
                Status.EMPTY -> Log.d(TAG,
                    "[$serviceName] code=$code — vide")
                else -> Log.v(TAG,
                    "[$serviceName] code=$code ✗ ${result.errorMsg}")
            }
        }
    }

    // ── Transact bas niveau ───────────────────────────────────────────────

    private fun transact(binder: IBinder, service: String, code: Int): ProbeResult {
        val data  = Parcel.obtain()
        val reply = Parcel.obtain()
        return try {
            // writeInterfaceToken vide — certains services BYD n'en ont pas besoin
            // On essaie d'abord sans token, puis avec si erreur
            val ok = binder.transact(code, data, reply, 0)

            if (!ok) {
                return ProbeResult(service, code, Status.ERROR, emptyList(), emptyList(), "", "transact returned false")
            }

            // Lit toutes les données disponibles dans reply
            reply.setDataPosition(0)
            val raw = reply.marshall()
            if (raw.isEmpty()) {
                return ProbeResult(service, code, Status.EMPTY, emptyList(), emptyList(), "")
            }

            val hex = raw.take(32).joinToString(" ") { "%02X".format(it) }
            val ints = mutableListOf<Int>()
            val strings = mutableListOf<String>()

            // Tente de lire des int
            reply.setDataPosition(0)
            runCatching {
                repeat(8) {
                    if (reply.dataAvail() >= 4) ints.add(reply.readInt())
                }
            }

            // Tente de lire des String (position variable)
            reply.setDataPosition(0)
            runCatching {
                val s = reply.readString()
                if (!s.isNullOrBlank() && s.length < 128) strings.add(s)
            }

            ProbeResult(service, code, Status.OK, ints, strings, hex)

        } catch (e: SecurityException) {
            ProbeResult(service, code, Status.SECURITY_EXCEPTION, emptyList(), emptyList(), "", e.message ?: "")
        } catch (e: android.os.RemoteException) {
            ProbeResult(service, code, Status.REMOTE_EXCEPTION, emptyList(), emptyList(), "", e.message ?: "")
        } catch (e: Exception) {
            ProbeResult(service, code, Status.ERROR, emptyList(), emptyList(), "", e.message ?: "")
        } finally {
            data.recycle()
            reply.recycle()
        }
    }

    /**
     * Transact avec writeInterfaceToken — nécessaire pour certains services AIDL stricts.
     */
    fun transactWithToken(serviceName: String, interfaceToken: String, code: Int): ProbeResult {
        val binder = getService(serviceName) ?: return ProbeResult(
            serviceName, code, Status.ERROR, emptyList(), emptyList(), "", "service not found"
        )
        val data  = Parcel.obtain()
        val reply = Parcel.obtain()
        return try {
            data.writeInterfaceToken(interfaceToken)
            binder.transact(code, data, reply, 0)
            val raw = reply.marshall()
            val hex = raw.take(32).joinToString(" ") { "%02X".format(it) }
            reply.setDataPosition(0)
            val ints = mutableListOf<Int>()
            runCatching { repeat(8) { if (reply.dataAvail() >= 4) ints.add(reply.readInt()) } }
            ProbeResult(serviceName, code, Status.OK, ints, emptyList(), hex)
        } catch (e: Exception) {
            ProbeResult(serviceName, code, Status.ERROR, emptyList(), emptyList(), "", e.message ?: "")
        } finally {
            data.recycle(); reply.recycle()
        }
    }

    private fun getService(name: String): IBinder? = try {
        val sm = Class.forName("android.os.ServiceManager")
        sm.getMethod("getService", String::class.java).invoke(null, name) as? IBinder
    } catch (e: Exception) { null }

    // ── Interprétation des résultats ──────────────────────────────────────

    /**
     * Analyse les résultats bruts pour identifier les codes candidats.
     * Cherche les patterns connus :
     *  - Power level : int dans [0,3]
     *  - Gear : string dans {"P","R","N","D","S","M"}
     *  - Tension batterie : int dans [100..145] (×0.1V → 10.0V..14.5V)
     */
    fun interpret(results: List<ProbeResult>): List<Interpretation> {
        val out = mutableListOf<Interpretation>()
        val gears = setOf("P", "R", "N", "D", "S", "M", "B")

        for (r in results.filter { it.status == Status.OK }) {
            // Candidat power level
            if (r.intValues.firstOrNull() in 0..3 && r.intValues.size <= 4) {
                out += Interpretation(r.service, r.code, "POWER_LEVEL_CANDIDATE",
                    "int[0]=${r.intValues.firstOrNull()} → 0=OFF 1=ACC 2=ON 3=OK")
            }
            // Candidat gear
            if (r.stringValues.any { it.uppercase() in gears }) {
                out += Interpretation(r.service, r.code, "GEAR_CANDIDATE",
                    "string='${r.stringValues.firstOrNull()}'")
            }
            // Candidat tension batterie (en dixièmes de volt)
            val v = r.intValues.firstOrNull()
            if (v != null && v in 100..150) {
                out += Interpretation(r.service, r.code, "BATTERY_VOLTAGE_CANDIDATE",
                    "${v / 10}.${v % 10}V")
            }
            // Candidat vitesse (km/h, 0..250)
            if (v != null && v in 0..250 && r.intValues.size == 1) {
                out += Interpretation(r.service, r.code, "SPEED_CANDIDATE", "${v} km/h")
            }
        }
        return out
    }

    data class Interpretation(
        val service: String,
        val code: Int,
        val type: String,
        val description: String
    )
}
