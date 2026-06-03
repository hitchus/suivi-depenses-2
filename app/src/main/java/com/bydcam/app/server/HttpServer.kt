package com.bydcam.app.server

import android.util.Log
import com.bydcam.app.recording.RecordingMode
import com.bydcam.app.recording.RecordingModeManager
import com.bydcam.app.storage.StorageManager
import com.bydcam.app.surveillance.SentryModeManager
import com.google.gson.Gson
import fi.iki.elonen.NanoHTTPD
import java.io.File
import java.io.FileInputStream

/**
 * Serveur HTTP embarqué (NanoHTTPD).
 *
 * Routes :
 *  GET  /              → SPA web (assets/web/index.html)
 *  GET  /api/status    → état global (recording, sentry, storage)
 *  POST /api/recording → changer le mode d'enregistrement
 *  GET  /api/storage   → état stockage + carte SD
 *  POST /api/storage/cleanup → nettoyage manuel
 *  GET  /api/clips     → liste des clips
 *  GET  /clips/<file>  → téléchargement d'un clip
 */
class HttpServer(
    port: Int = PORT,
    private val recordingManager: RecordingModeManager,
    private val sentryManager: SentryModeManager,
    private val storageManager: StorageManager,
    private val assetLoader: (String) -> ByteArray?
) : NanoHTTPD(port) {

    private val tag = "HttpServer"
    private val gson = Gson()

    override fun serve(session: IHTTPSession): Response {
        val uri = session.uri.trimEnd('/')
        val method = session.method

        return try {
            when {
                // SPA web : racine ou assets statiques
                uri == "" || uri == "/" -> serveAsset("web/index.html", "text/html")
                uri.startsWith("/web/")  -> {
                    val path = "web/" + uri.removePrefix("/web/")
                    val mime = mimeFor(path)
                    serveAsset(path, mime)
                }

                // API REST
                uri == "/api/status"   && method == Method.GET  -> apiStatus()
                uri == "/api/recording" && method == Method.POST -> apiSetRecordingMode(session)
                uri == "/api/sentry"   && method == Method.POST  -> apiSetSentry(session)
                uri == "/api/storage"  && method == Method.GET  -> apiStorage()
                uri == "/api/storage/cleanup" && method == Method.POST -> apiCleanup()
                uri == "/api/clips"    && method == Method.GET  -> apiListClips()
                uri.startsWith("/clips/") -> serveClip(uri.removePrefix("/clips/"))

                else -> jsonError(404, "Not found: $uri")
            }
        } catch (e: Exception) {
            Log.e(tag, "Server error on $uri: ${e.message}")
            jsonError(500, e.message ?: "Internal error")
        }
    }

    private fun apiStatus(): Response {
        val body = mapOf(
            "recording" to mapOf(
                "active" to recordingManager.isRecording(),
                "mode"   to recordingManager.currentMode.name
            ),
            "sentry" to mapOf(
                "active" to sentryManager.isActive
            ),
            "storage" to mapOf(
                "freeGB" to "%.1f".format(storageManager.getFreeSpaceGB()),
                "usage"  to storageManager.getTotalUsageBytes()
                    .mapValues { (_, v) -> "${v / 1024 / 1024} MB" }
            )
        )
        return jsonOk(body)
    }

    private fun apiSetRecordingMode(session: IHTTPSession): Response {
        val body = parseBody(session)
        val modeName = body["mode"] as? String
            ?: return jsonError(400, "Missing 'mode' field")
        val mode = runCatching { RecordingMode.valueOf(modeName) }.getOrNull()
            ?: return jsonError(400, "Invalid mode. Use: ${RecordingMode.values().joinToString()}")
        recordingManager.setMode(mode)
        return jsonOk(mapOf("mode" to mode.name))
    }

    private fun apiSetSentry(session: IHTTPSession): Response {
        val body = parseBody(session)
        val enabled = body["enabled"] as? Boolean
            ?: return jsonError(400, "Missing 'enabled' boolean")
        val sensitivity = (body["sensitivity"] as? Double)?.toFloat()

        if (sensitivity != null) sentryManager.setSensitivity(sensitivity)
        if (enabled) sentryManager.activate() else sentryManager.deactivate()

        return jsonOk(mapOf("sentry" to enabled, "sensitivity" to sentryManager.motionDetector.sensitivityThreshold))
    }

    private fun apiStorage(): Response = jsonOk(storageManager.getSdCardStatus() +
            mapOf("usage" to storageManager.getTotalUsageBytes().mapValues { "${it.value / 1024 / 1024} MB" }))

    private fun apiCleanup(): Response {
        storageManager.runCleanupIfNeeded()
        return jsonOk(mapOf("ok" to true))
    }

    private fun apiListClips(): Response {
        val clips = (storageManager.recordingsDir.listFiles { f -> f.extension == "mp4" } ?: emptyArray())
            .sortedByDescending { it.lastModified() }
            .take(100)
            .map { mapOf("name" to it.name, "sizeKB" to it.length() / 1024, "ts" to it.lastModified()) }
        return jsonOk(mapOf("clips" to clips))
    }

    private fun serveClip(fileName: String): Response {
        val file = File(storageManager.recordingsDir, fileName.replace("..", ""))
        if (!file.exists()) return jsonError(404, "Clip not found")
        return newChunkedResponse(Response.Status.OK, "video/mp4", FileInputStream(file))
    }

    private fun serveAsset(path: String, mime: String): Response {
        val bytes = assetLoader(path) ?: return jsonError(404, "Asset not found: $path")
        return newFixedLengthResponse(Response.Status.OK, mime, bytes.inputStream(), bytes.size.toLong())
    }

    private fun parseBody(session: IHTTPSession): Map<String, Any> {
        val files = mutableMapOf<String, String>()
        session.parseBody(files)
        val raw = files["postData"] ?: "{}"
        @Suppress("UNCHECKED_CAST")
        return runCatching { gson.fromJson(raw, Map::class.java) as Map<String, Any> }.getOrDefault(emptyMap())
    }

    private fun jsonOk(body: Any) = newFixedLengthResponse(
        Response.Status.OK, "application/json", gson.toJson(body)
    )

    private fun jsonError(code: Int, msg: String) = newFixedLengthResponse(
        Response.Status.lookup(code) ?: Response.Status.INTERNAL_ERROR,
        "application/json",
        gson.toJson(mapOf("error" to msg))
    )

    private fun mimeFor(path: String) = when (path.substringAfterLast('.')) {
        "html" -> "text/html"
        "js"   -> "application/javascript"
        "css"  -> "text/css"
        "json" -> "application/json"
        "png"  -> "image/png"
        "ico"  -> "image/x-icon"
        else   -> "application/octet-stream"
    }

    companion object {
        const val PORT = 8080
    }
}
