package com.bydcam.app.recording

enum class RecordingMode {
    /** Pipeline coupé (économie ressources). */
    NONE,

    /** Enregistre dès que ACC ≥ POWER_ACC. */
    CONTINUOUS,

    /** Enregistre uniquement en gear D/R/S/M. */
    DRIVE_MODE,

    /** Déclenché par radar proximité quand gear ≠ Park. */
    PROXIMITY_GUARD;

    fun requiresDrivingGear() = this == DRIVE_MODE
    fun isActive()           = this != NONE
}
