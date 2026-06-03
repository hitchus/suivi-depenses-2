# Overdrive — Enregistrement caméra : analyse technique

Deux modes exclusifs. Un seul mécanisme commun : la caméra panoramique BYD (AVM) découpée en 4 vues.

---

## Architecture commune

```
Caméras BYD (4 objectifs)
        ↓  Binder IPC propriétaire
BydCameraCoordinator
        ↓  zero-copy GPU
PanoramicCameraGpu   (2560×1920 ou résolution véhicule)
        ↓  découpage GPU en 4 vues
VirtualView ×4       (VIEW_WIDTH = PANO_WIDTH/4, VIEW_HEIGHT = PANO_HEIGHT)
        ↓  encodage H.264
H264CircularBuffer   (ring buffer mémoire)
        ↓
Fichiers .mp4 → /sdcard/DCIM/BYDCam/
```

**Paramètres d'enregistrement (CameraConfiguration.kt) :**

| Paramètre         | Valeur                   |
|-------------------|--------------------------|
| FPS               | 25                       |
| Bitrate           | 4 Mbps                   |
| Keyframe interval | 2 s                      |
| Durée segment     | 2 min (= 1 fichier)      |
| Stockage          | `/sdcard/DCIM/BYDCam/`   |
| Port TCP daemon   | 19876                    |
| Port HTTP/web     | 8080                     |

---

## Mode 1 — Enregistrement en roulant

**Classe centrale : `RecordingModeManager.java`**

### Les 4 modes de conduite (mutuellement exclusifs)

```
NONE             → pipeline arrêté (économie ressources)
CONTINUOUS       → enregistre dès que ACC est ON
DRIVE_MODE       → enregistre uniquement en gear D/R/S/M
PROXIMITY_GUARD  → enregistrement déclenché par radar en gear non-Park
```

### Logique d'activation

```
ACC ON
  ↓
Lecture gear position (BYD Binder)
  ↓
  ├─ CONTINUOUS   → start pipeline immédiatement
  ├─ DRIVE_MODE   → gear ∈ {D, R, S, M} ?
  │                    oui → start pipeline
  │                    non (Park/Neutral) → stop pipeline
  └─ PROXIMITY_GUARD → radar détecte obstacle ?
                         oui + gear ≠ Park → start pipeline
                         non → stop pipeline
```

### Problème cold-start (découvert dans le code)

> *"After a hard reboot the BYD camera HAL has not been poked by com.byd.avc yet,
> so opening the camera before warmup leaves it in a wedged state."*

Solution : `AvcHalWarmup.java` est appelé avant toute ouverture du pipeline.

### Resynchronisation périodique

- Délai initial : **8 secondes** après activation
- Resync toutes les **30 secondes** (rattrape les activations silencieuses ratées)
- Champ `volatile` sur état ACC et gear → visibilité thread-safe

### Cas particulier : Neutral

Neutral est ignoré pour les transitions (pas de cycling mode) à cause du
comportement BYD Auto Hold qui provoquerait des redémarrages intempestifs du pipeline.

---

## Mode 2 — Surveillance à l'arrêt (détection de mouvement)

**Processus impliqués :**
- `AccSentryDaemon` — surveille l'état ACC, UID 2000 (shell)
- `SentryDaemon` — daemon système, UID 1000 (system), gère le WakeLock
- `RecordingController.kt` — envoie les commandes d'enregistrement
- `GpuSurveillancePipeline.java` — pipeline GPU complet
- `NativeMotion.java` + C++ — détection mouvement bas niveau

### Déclenchement : détection ACC OFF

```
BYDAutoBodyworkDevice (Binder)
    ↓  listener power level
AccSentryDaemon
    ↓  power level = 0 (OFF) ou 1 (ACC)
    ↓  ACC vient de passer OFF ?
SentryDaemon activé
    ↓  acquiert WakeLock (CPU reste actif)
    ↓  active WiFi (svc wifi enable)
GpuSurveillancePipeline démarré
```

**Niveaux de puissance BYD** (SentryConfiguration.kt) :

| Niveau | Valeur | Signification    |
|--------|--------|------------------|
| OFF    | 0      | Véhicule éteint  |
| ACC    | 1      | Accessoires seuls|
| ON     | 2      | Contact mis      |
| OK     | 3      | Moteur tournant  |

### Pipeline de détection de mouvement (NativeMotion.java → C++)

4 algorithmes disponibles, sélectionnables par config :

```
Flux caméra (frame brute 640×480)
        ↓
[Choix algorithme]
  ├─ SAD (Sum of Absolute Differences)
  │    → différence directe entre frames
  │    → < 0.5 ms sur 320×240 RGB
  │    → rapide, simple, beaucoup de faux positifs
  │
  ├─ MOG2 (Mixture of Gaussians)
  │    → apprend le fond en continu
  │    → réduit les faux positifs de 90%
  │    → plus lent, meilleur sur scènes stables
  │
  ├─ Grid Motion (blocs)
  │    → divise le frame en grille de blocs
  │    → détecte petits objets ratés par SAD/MOG2
  │    → utile pour personnes éloignées
  │
  └─ Edge Motion (Sobel/gradient)
       → filtre de bords configurable
       → flash immunity level 0-3
       → résistant aux changements de lumière
```

### Pipeline v2 (MotionPipelineV2 — 6 étapes)

Traite un mosaic 640×480 découpé en quadrants (4 caméras) :

```
Frame mosaic 640×480
    ↓ [Étape 1] Grayscale + ROI mask (zones d'intérêt configurables)
    ↓ [Étape 2] Détection mouvement par quadrant (MOG2 ou SAD)
    ↓ [Étape 3] Flash rejection (rejet changement global luminosité)
    ↓ [Étape 4] Grid refinement (localisation précise dans le quadrant)
    ↓ [Étape 5] Texture tracker NCC (suivi entre frames)
    ↓ [Étape 6] CrossQuadrantTracker (suivi cross-caméra)
    ↓
Résultat : {quadrant, bounding_box, confiance, flash_flag}
```

### Détection et classification d'objets (TFLite YOLO)

```
NativeMotion.detectObjects()
    ↓  modèle YOLO embarqué (assets/models/)
    ↓  GPU delegate TFLite
    ↓
[bounding_box, label, confiance]
    ↓
SeverityClassifier.java
    ↓  classifie : faible / moyen / élevé
    ↓
DistanceEstimator.java  → distance estimée depuis la caméra
    ↓
ActorTracker.java       → suivi de l'acteur entre les frames
```

### Déclenchement de l'enregistrement

```
SeverityClassifier → niveau ≥ seuil config
    ↓
RecordingController.sendCameraCommand()
    ↓  JSON via TCP localhost:19876 → CameraDaemon
    ↓
{"action":"start","camera":1,"viewOnly":false}
{"action":"start","camera":2,"viewOnly":false}
{"action":"start","camera":3,"viewOnly":false}
{"action":"start","camera":4,"viewOnly":false}
    ↓
Enregistrement H.264 toutes caméras simultanément
    ↓
HardwareEventRecorderGpu.java → clip pré-événement + post-événement
GpuMosaicRecorder.java        → enregistrement multi-caméras fusionné
SrtWriter.java                → fichier .srt avec horodatage et métadonnées
```

### Gestion batterie

Quand tension batterie < 12.1V :
- `AccSentryDaemon` envoie wake cycle MCU toutes les **45 secondes**
- Maintient le convertisseur DC-DC actif
- Évite que le microcontrôleur entre en veille profonde

### Anti-kill du daemon de surveillance

```
SentryDaemon (UID 1000)
    └─ WakeLock PARTIAL (CPU actif en permanence)
    └─ WiFi forcé ON (svc wifi enable)
    └─ LocationMonitor thread (vérifie GPS toutes les 15 s)
    └─ PID file → /data/local/tmp/sentry_daemon.pid
    └─ Control socket TCP:19879 (PING/STOP/STATUS)

AccSentryDaemon (UID 2000)
    └─ Keep-alive loop 10 s (injecte fake user activity)
    └─ powerManager.wakeUp() + userActivity()
    └─ IPC vers CameraDaemon (TCP:19876)
```

---

## Résumé : qui fait quoi

| Composant                    | Rôle                                              | Mode      |
|------------------------------|---------------------------------------------------|-----------|
| `RecordingModeManager.java`  | Choisit le mode, surveille ACC + gear             | Conduite  |
| `AvcHalWarmup.java`          | Débloque le HAL caméra après reboot               | Conduite  |
| `BydCameraCoordinator.java`  | Orchestre les 4 caméras BYD                       | Les deux  |
| `PanoramicCameraGpu.java`    | Capture + découpage GPU en 4 vues                 | Les deux  |
| `H264CircularBuffer.java`    | Ring buffer segments vidéo                        | Les deux  |
| `AccSentryDaemon.java`       | Détecte ACC OFF, active la surveillance           | Arrêt     |
| `SentryDaemon.java`          | WakeLock + WiFi + protection daemon               | Arrêt     |
| `NativeMotion.java` (C++)    | Détection mouvement SAD/MOG2/Grid/Edge            | Arrêt     |
| `MotionPipelineV2.java`      | Pipeline 6 étapes par quadrant                    | Arrêt     |
| `SeverityClassifier.java`    | Décide si mouvement = événement                   | Arrêt     |
| `RecordingController.kt`     | Envoie start/stop recording → CameraDaemon TCP    | Arrêt     |
| `HardwareEventRecorderGpu`   | Sauvegarde clip pré+post événement                | Arrêt     |
| `GpuMosaicRecorder.java`     | Fusionne les 4 caméras en un clip                 | Arrêt     |
| `SrtWriter.java`             | Métadonnées horodatées en .srt                    | Arrêt     |
