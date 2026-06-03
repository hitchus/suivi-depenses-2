package com.bydcam.app.byd

object BydConstants {

    // Niveaux de puissance ACC (BYDAutoBodyworkDevice)
    const val POWER_OFF = 0
    const val POWER_ACC = 1
    const val POWER_ON  = 2
    const val POWER_OK  = 3   // Moteur tournant

    // Positions de levier de vitesse
    const val GEAR_PARK    = "P"
    const val GEAR_REVERSE = "R"
    const val GEAR_NEUTRAL = "N"
    const val GEAR_DRIVE   = "D"
    const val GEAR_SPORT   = "S"
    const val GEAR_MANUAL  = "M"

    val DRIVING_GEARS = setOf(GEAR_DRIVE, GEAR_REVERSE, GEAR_SPORT, GEAR_MANUAL)

    // Services système BYD (accès via Binder reflection)
    const val SERVICE_ACC_MODE     = "accmodemanager"
    const val SERVICE_BYD_BODYWORK = "byd_bodywork"
    const val SERVICE_BYD_DATACACHE = "byd_datacached"

    // Intents BYD
    const val ACTION_ACC_ON  = "com.byd.intent.action.ACC_ON"
    const val ACTION_ACC_OFF = "com.byd.intent.action.ACC_OFF"

    // Propriétés système pour la carte SD
    const val PROP_SD_UUID    = "persist.byd.sdcard.uuid"
    const val PROP_SD_MOUNT   = "persist.byd.sdcard.mount"

    // Feature IDs caméra AVM BYD (identifiés par reverse engineering Overdrive)
    const val FEATURE_AVM_CAMERA  = 782237711
    const val FEATURE_AVM_POWER   = 782237728
}
