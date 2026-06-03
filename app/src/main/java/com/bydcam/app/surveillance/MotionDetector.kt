package com.bydcam.app.surveillance

import android.graphics.Bitmap
import android.graphics.Color
import android.util.Log
import com.bydcam.app.camera.CameraBackend
import kotlin.math.abs
import kotlin.math.sqrt

/**
 * Détecteur de mouvement par différence de frames (SAD simplifié).
 *
 * MVP : implémentation pure Kotlin (pas de C++ / OpenCV).
 * Prêt à être remplacé par NativeMotion JNI + OpenCV MOG2 pour la prod.
 *
 * Algorithme :
 *  1. Conversion frame en niveaux de gris (luma)
 *  2. Découpage en grille de blocs (8×6 = 48 blocs)
 *  3. SAD par bloc entre frame courante et frame de référence (background)
 *  4. Mise à jour adaptative du background (moyenne pondérée)
 *  5. Seuillage global + rejet des changements de luminosité globale (flash)
 */
class MotionDetector {

    interface Listener {
        /** Appelé quand un mouvement dépasse le seuil. cameraId = 1..4. */
        fun onMotionDetected(cameraId: Int, severity: Severity, region: Region)
    }

    enum class Severity { LOW, MEDIUM, HIGH }

    data class Region(
        val blockRow: Int,
        val blockCol: Int,
        val gridRows: Int = GRID_ROWS,
        val gridCols: Int = GRID_COLS
    )

    private val tag = "MotionDetector"

    // Background par caméra (tableau de luma en niveaux de gris)
    private val backgrounds = mutableMapOf<Int, FloatArray>()
    private val frameCount = mutableMapOf<Int, Int>()

    @Volatile var listener: Listener? = null
    @Volatile var sensitivityThreshold = DEFAULT_THRESHOLD
    @Volatile var isEnabled = false

    val frameCallback = object : CameraBackend.FrameCallback {
        override fun onFrame(frame: CameraBackend.CameraFrame) {
            if (!isEnabled) return
            processFrame(frame)
        }
    }

    private fun processFrame(frame: CameraBackend.CameraFrame) {
        val luma = bitmapToLuma(frame.bitmap)
        val width = frame.bitmap.width
        val height = frame.bitmap.height

        val bg = backgrounds.getOrPut(frame.cameraId) { luma.copyOf() }
        val count = (frameCount[frame.cameraId] ?: 0) + 1
        frameCount[frame.cameraId] = count

        // Attendre 10 frames avant de commencer (background learning)
        if (count < WARMUP_FRAMES) {
            updateBackground(bg, luma)
            backgrounds[frame.cameraId] = bg
            return
        }

        // Calcul SAD global pour détecter les changements de lumière (flash)
        val globalSad = sadGlobal(luma, bg)
        if (globalSad > FLASH_REJECTION_THRESHOLD) {
            updateBackground(bg, luma, alpha = 0.3f)
            return
        }

        // SAD par bloc
        val blockWidth = width / GRID_COLS
        val blockHeight = height / GRID_ROWS
        var maxSad = 0f
        var maxRow = 0; var maxCol = 0

        for (row in 0 until GRID_ROWS) {
            for (col in 0 until GRID_COLS) {
                val sad = sadBlock(luma, bg, width, row, col, blockWidth, blockHeight)
                if (sad > maxSad) { maxSad = sad; maxRow = row; maxCol = col }
            }
        }

        if (maxSad > sensitivityThreshold) {
            val severity = when {
                maxSad > sensitivityThreshold * 3 -> Severity.HIGH
                maxSad > sensitivityThreshold * 1.5 -> Severity.MEDIUM
                else -> Severity.LOW
            }
            listener?.onMotionDetected(frame.cameraId, severity, Region(maxRow, maxCol))
        }

        // Mise à jour background adaptative
        updateBackground(bg, luma, alpha = BACKGROUND_ALPHA)
        backgrounds[frame.cameraId] = bg
    }

    fun reset() {
        backgrounds.clear()
        frameCount.clear()
    }

    private fun bitmapToLuma(bitmap: Bitmap): FloatArray {
        val pixels = IntArray(bitmap.width * bitmap.height)
        bitmap.getPixels(pixels, 0, bitmap.width, 0, 0, bitmap.width, bitmap.height)
        return FloatArray(pixels.size) { i ->
            val c = pixels[i]
            // Formule ITU-R BT.601 luma
            0.299f * Color.red(c) + 0.587f * Color.green(c) + 0.114f * Color.blue(c)
        }
    }

    private fun sadGlobal(a: FloatArray, b: FloatArray): Float {
        var sum = 0f
        for (i in a.indices) sum += abs(a[i] - b[i])
        return sum / a.size
    }

    private fun sadBlock(
        current: FloatArray, bg: FloatArray, width: Int,
        row: Int, col: Int, bw: Int, bh: Int
    ): Float {
        var sum = 0f; var count = 0
        val startX = col * bw; val startY = row * bh
        for (y in startY until startY + bh) {
            for (x in startX until startX + bw) {
                val idx = y * width + x
                if (idx < current.size) {
                    sum += abs(current[idx] - bg[idx])
                    count++
                }
            }
        }
        return if (count > 0) sum / count else 0f
    }

    private fun updateBackground(bg: FloatArray, frame: FloatArray, alpha: Float = BACKGROUND_ALPHA) {
        for (i in bg.indices) {
            bg[i] = bg[i] * (1f - alpha) + frame[i] * alpha
        }
    }

    companion object {
        private const val GRID_ROWS = 6
        private const val GRID_COLS = 8
        private const val DEFAULT_THRESHOLD = 15f        // 0–255 (luma)
        private const val FLASH_REJECTION_THRESHOLD = 40f
        private const val BACKGROUND_ALPHA = 0.05f       // Vitesse d'apprentissage du background
        private const val WARMUP_FRAMES = 10
    }
}
