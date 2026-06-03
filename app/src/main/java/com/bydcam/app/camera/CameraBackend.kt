package com.bydcam.app.camera

import android.graphics.Bitmap
import android.view.Surface

/**
 * Interface commune pour les backends caméra.
 *
 * Deux implémentations :
 *  - BydCameraBackend  : accès AVM BYD via Binder (production)
 *  - Camera2Backend    : Camera2 API standard (développement/test)
 */
interface CameraBackend {

    enum class State { CLOSED, OPENING, OPEN, ERROR }

    data class CameraFrame(
        val cameraId: Int,      // 1=avant, 2=arrière, 3=gauche, 4=droite
        val bitmap: Bitmap,
        val timestampMs: Long
    )

    interface FrameCallback {
        fun onFrame(frame: CameraFrame)
    }

    /** Ouvre le backend (warm-up HAL inclus). */
    fun open()

    /** Ferme proprement le backend. */
    fun close()

    /** Fournit une Surface de rendu pour l'encodeur MediaCodec. */
    fun getEncoderSurface(cameraId: Int): Surface?

    /** Abonne un callback aux frames décodées (pour la détection de mouvement). */
    fun setFrameCallback(callback: FrameCallback?)

    fun getState(): State

    /** Nombre de caméras disponibles sur ce véhicule. */
    fun getCameraCount(): Int
}
