package com.bydcam.app.storage

import android.content.Context
import android.os.StatFs
import android.util.Log
import com.bydcam.app.byd.BydConstants
import java.io.File
import java.text.SimpleDateFormat
import java.util.*
import java.util.concurrent.Executors

/**
 * Gestion du stockage : interne + carte SD BYD.
 *
 * Stratégie :
 *  - Détecte la carte SD via propriétés système BYD ou scan des volumes Android
 *  - Préfère la carte SD si disponible et assez libre
 *  - Nettoyage automatique : supprime les plus anciens fichiers en 1er
 *  - Quotas séparés : recordings / surveillance / proximity
 */
class StorageManager(private val context: Context) {

    private val tag = "StorageManager"
    private val cleanerExecutor = Executors.newSingleThreadExecutor()

    // Répertoires de base
    private val baseDir: File by lazy { resolveBaseDir() }
    val recordingsDir  get() = File(baseDir, "recordings").also { it.mkdirs() }
    val surveillanceDir get() = File(baseDir, "surveillance").also { it.mkdirs() }
    val proximityDir   get() = File(baseDir, "proximity").also { it.mkdirs() }

    // Quotas max par catégorie
    var maxRecordingBytes    = 4_000L * 1024 * 1024   // 4 GB
    var maxSurveillanceBytes = 2_000L * 1024 * 1024   // 2 GB
    var reservedFreeBytes    = 500L * 1024 * 1024      // 500 MB toujours libre

    // Fichier UUID persistant (survie aux cycles d'alimentation BYD)
    private val learnedUuidFile = File(context.filesDir, "sdcard_uuid.txt")

    fun setup() {
        recordingsDir; surveillanceDir; proximityDir
        Log.i(tag, "Storage base: ${baseDir.absolutePath}")
        Log.i(tag, "Free: ${getFreeSpaceGB()} GB")
    }

    fun newRecordingFile(cameraId: Int): File {
        val ts = timestamp()
        return File(recordingsDir, "rec_cam${cameraId}_${ts}.mp4")
    }

    fun newSurveillanceFile(cameraId: Int, severity: String): File {
        val ts = timestamp()
        return File(surveillanceDir, "sentry_cam${cameraId}_${severity}_${ts}.mp4")
    }

    fun newProximityFile(cameraId: Int): File {
        val ts = timestamp()
        return File(proximityDir, "prox_cam${cameraId}_${ts}.mp4")
    }

    /**
     * Vérifie et réserve de l'espace avant un enregistrement.
     * Lance un nettoyage si nécessaire.
     */
    fun reserveSpace(neededBytes: Long) {
        val free = getFreeBytes()
        if (free < neededBytes + reservedFreeBytes) {
            Log.w(tag, "Low space (${free / 1024 / 1024} MB), running cleanup")
            runCleanup()
        }
    }

    fun runCleanupIfNeeded() {
        cleanerExecutor.submit {
            if (getFreeBytes() < reservedFreeBytes * 2) runCleanup()
        }
    }

    /**
     * Nettoyage par catégorie : supprime les plus anciens fichiers.
     * Protection : les fichiers de moins de 24h ne sont jamais supprimés.
     */
    private fun runCleanup() {
        cleanCategory(recordingsDir, maxRecordingBytes)
        cleanCategory(surveillanceDir, maxSurveillanceBytes)
        cleanOrphanedTempFiles()
    }

    private fun cleanCategory(dir: File, maxBytes: Long) {
        val files = dir.listFiles { f -> f.extension == "mp4" }
            ?.sortedBy { it.lastModified() }
            ?: return

        var totalSize = files.sumOf { it.length() }
        val protectedTime = System.currentTimeMillis() - PROTECTION_WINDOW_MS

        for (file in files) {
            if (totalSize <= maxBytes) break
            if (file.lastModified() > protectedTime) continue  // fichier récent protégé
            val size = file.length()
            if (file.delete()) {
                totalSize -= size
                Log.d(tag, "Deleted: ${file.name} (freed ${size / 1024} KB)")
            }
        }
    }

    /** Supprime les .mp4.tmp laissés par des daemons crashés (après 10 min). */
    private fun cleanOrphanedTempFiles() {
        val graceMs = 10L * 60 * 1000
        val cutoff = System.currentTimeMillis() - graceMs
        listOf(recordingsDir, surveillanceDir).forEach { dir ->
            dir.listFiles { f -> f.name.endsWith(".tmp") && f.lastModified() < cutoff }
                ?.forEach { it.delete() }
        }
    }

    fun getFreeBytes(): Long {
        val stat = StatFs(baseDir.absolutePath)
        return stat.availableBytes
    }

    fun getFreeSpaceGB(): Float = getFreeBytes() / 1024f / 1024f / 1024f

    fun getTotalUsageBytes(): Map<String, Long> = mapOf(
        "recordings"  to dirSize(recordingsDir),
        "surveillance" to dirSize(surveillanceDir),
        "proximity"   to dirSize(proximityDir)
    )

    /**
     * Résolution du répertoire de base.
     * Préfère la carte SD si disponible et lisible.
     */
    private fun resolveBaseDir(): File {
        val sdCard = findSdCard()
        return if (sdCard != null && sdCard.canWrite()) {
            Log.i(tag, "Using SD card: ${sdCard.absolutePath}")
            File(sdCard, "BydCam")
        } else {
            Log.i(tag, "Using internal storage")
            File(context.getExternalFilesDir(null), "BydCam")
                ?: File(context.filesDir, "BydCam")
        }
    }

    /**
     * Détection carte SD via 3 méthodes en cascade :
     *  1. Propriété système BYD (PROP_SD_MOUNT)
     *  2. UUID appris et persisté
     *  3. Scan volumes Android classique
     */
    private fun findSdCard(): File? {
        // Méthode 1 : propriété BYD
        runCatching {
            val sysProp = Class.forName("android.os.SystemProperties")
            val get = sysProp.getMethod("get", String::class.java, String::class.java)
            val mount = get.invoke(null, BydConstants.PROP_SD_MOUNT, "") as String
            if (mount.isNotBlank()) {
                val f = File(mount)
                if (f.exists() && f.canWrite()) {
                    learnedUuidFile.writeText(mount)  // Persiste pour les reboots
                    return f
                }
            }
        }

        // Méthode 2 : UUID persisté
        runCatching {
            val learned = learnedUuidFile.readText().trim()
            if (learned.isNotBlank()) {
                val f = File(learned)
                if (f.exists() && f.canWrite()) return f
            }
        }

        // Méthode 3 : scan volumes Android
        context.getExternalFilesDirs(null).forEach { dir ->
            if (dir != null && !dir.absolutePath.contains("emulated")) {
                val root = dir.absolutePath.substringBefore("/Android")
                val f = File(root)
                if (f.canWrite()) return f
            }
        }

        return null
    }

    fun getSdCardStatus(): Map<String, Any> {
        val sdCard = findSdCard()
        return if (sdCard != null) {
            val stat = StatFs(sdCard.absolutePath)
            mapOf(
                "available" to true,
                "path" to sdCard.absolutePath,
                "freeGB" to "%.1f".format(stat.availableBytes / 1024f / 1024f / 1024f),
                "totalGB" to "%.1f".format(stat.totalBytes / 1024f / 1024f / 1024f)
            )
        } else {
            mapOf("available" to false)
        }
    }

    private fun dirSize(dir: File): Long =
        dir.walkTopDown().filter { it.isFile }.sumOf { it.length() }

    private fun timestamp(): String =
        SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date())

    companion object {
        private const val PROTECTION_WINDOW_MS = 24L * 60 * 60 * 1000  // 24h
    }
}
