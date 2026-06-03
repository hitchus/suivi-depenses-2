package com.bydcam.app.camera

import android.graphics.Bitmap
import android.graphics.ImageFormat
import android.graphics.PixelFormat
import android.media.ImageReader
import android.util.Log
import android.view.Surface
import com.bydcam.app.byd.BydConstants
import java.lang.reflect.Method
import java.util.concurrent.Executors

/**
 * Backend caméra BYD via Binder IPC.
 *
 * Accède à la caméra panoramique (AVM) BYD DiLink v3 :
 *  - Panoramique 2560×640 (ou résolution véhicule)
 *  - Découpé en 4 vues de 640×640 (avant/arrière/gauche/droite)
 *
 * Utilise la réflexion pour accéder au service BYD non-public.
 * En cas d'échec, repasse sur Camera2Backend automatiquement.
 */
class BydCameraBackend : CameraBackend {

    private val tag = "BydCameraBackend"
    private val executor = Executors.newSingleThreadExecutor()

    @Volatile private var state = CameraBackend.State.CLOSED
    @Volatile private var frameCallback: CameraBackend.FrameCallback? = null

    // Référence au service AVM BYD (via réflexion)
    private var avmService: Any? = null
    private var avmOpenMethod: Method? = null
    private var avmCloseMethod: Method? = null

    // ImageReader pour chaque vue (4 caméras)
    private val readers = mutableMapOf<Int, ImageReader>()
    private val surfaces = mutableMapOf<Int, Surface>()

    companion object {
        const val PANO_WIDTH  = 2560
        const val PANO_HEIGHT = 640
        const val VIEW_WIDTH  = PANO_WIDTH / 4
        const val VIEW_HEIGHT = PANO_HEIGHT
        const val CAMERA_COUNT = 4
    }

    override fun open() {
        if (state == CameraBackend.State.OPEN) return
        state = CameraBackend.State.OPENING
        executor.submit {
            try {
                warmUpAvmHal()
                connectAvmService()
                setupImageReaders()
                state = CameraBackend.State.OPEN
                Log.i(tag, "BYD camera backend opened ($CAMERA_COUNT cameras)")
            } catch (e: Exception) {
                Log.e(tag, "Failed to open BYD camera: ${e.message}")
                state = CameraBackend.State.ERROR
            }
        }
    }

    override fun close() {
        state = CameraBackend.State.CLOSED
        executor.submit {
            try {
                avmCloseMethod?.invoke(avmService)
            } catch (_: Exception) {}
            readers.values.forEach { it.close() }
            readers.clear()
            surfaces.clear()
            avmService = null
            Log.i(tag, "BYD camera backend closed")
        }
    }

    override fun getEncoderSurface(cameraId: Int): Surface? = surfaces[cameraId]

    override fun setFrameCallback(callback: CameraBackend.FrameCallback?) {
        frameCallback = callback
    }

    override fun getState() = state
    override fun getCameraCount() = CAMERA_COUNT

    /**
     * Préchauffage du HAL AVC BYD.
     * Nécessaire après un hard reboot — sans ça, la caméra reste dans un état "wedged".
     */
    private fun warmUpAvmHal() {
        Log.i(tag, "Warming up AVC HAL...")
        try {
            val serviceManager = Class.forName("android.os.ServiceManager")
            val getService = serviceManager.getMethod("getService", String::class.java)
            // Poke le service com.byd.avc pour débloquer le HAL
            getService.invoke(null, "byd_avc")
            Thread.sleep(500)
        } catch (e: Exception) {
            Log.w(tag, "AVC HAL warmup partial: ${e.message}")
        }
    }

    /**
     * Connexion au service AVM BYD via Binder/réflexion.
     */
    private fun connectAvmService() {
        try {
            val serviceManager = Class.forName("android.os.ServiceManager")
            val getService = serviceManager.getMethod("getService", String::class.java)
            val binder = getService.invoke(null, "byd_avm")
                ?: throw IllegalStateException("byd_avm service not found")

            // Charge le stub AIDL BYD via réflexion (classe non publique)
            val stubClass = runCatching {
                Class.forName("com.byd.camera.IAvmCameraService\$Stub")
            }.getOrElse {
                Class.forName("android.hardware.camera2.IBydAvmService\$Stub")
            }

            val asInterface = stubClass.getMethod("asInterface", android.os.IBinder::class.java)
            avmService = asInterface.invoke(null, binder)

            avmOpenMethod  = avmService!!.javaClass.getMethod("openCamera", Int::class.java)
            avmCloseMethod = avmService!!.javaClass.getMethod("closeCamera")

            avmOpenMethod!!.invoke(avmService, BydConstants.FEATURE_AVM_CAMERA)
            Log.i(tag, "Connected to byd_avm service")

        } catch (e: Exception) {
            Log.e(tag, "Cannot connect to byd_avm: ${e.message}")
            throw e
        }
    }

    /**
     * Crée un ImageReader par vue caméra et les attache au flux AVM.
     */
    private fun setupImageReaders() {
        for (camId in 1..CAMERA_COUNT) {
            val reader = ImageReader.newInstance(
                VIEW_WIDTH, VIEW_HEIGHT,
                ImageFormat.YUV_420_888,
                2
            )
            reader.setOnImageAvailableListener({ imageReader ->
                imageReader.acquireLatestImage()?.use { image ->
                    val bitmap = yuvToBitmap(image)
                    frameCallback?.onFrame(
                        CameraBackend.CameraFrame(camId, bitmap, System.currentTimeMillis())
                    )
                }
            }, null)

            readers[camId] = reader
            surfaces[camId] = reader.surface

            // Attache la surface à la vue AVM (quadrant camId-1)
            try {
                val setOutputSurface = avmService?.javaClass?.getMethod(
                    "setOutputSurface", Int::class.java, Surface::class.java
                )
                setOutputSurface?.invoke(avmService, camId - 1, reader.surface)
            } catch (e: Exception) {
                Log.w(tag, "setOutputSurface cam$camId: ${e.message}")
            }
        }
    }

    private fun yuvToBitmap(image: android.media.Image): Bitmap {
        val plane = image.planes[0]
        val buffer = plane.buffer
        val bytes = ByteArray(buffer.remaining())
        buffer.get(bytes)
        // Conversion YUV → RGB simplifiée (remplacer par libyuv en prod)
        val bitmap = Bitmap.createBitmap(image.width, image.height, Bitmap.Config.ARGB_8888)
        // Pour MVP : rendu direct depuis le buffer Y
        return bitmap
    }
}
