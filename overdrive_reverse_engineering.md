# Overdrive — Analyse Reverse Engineering

**Source** : `yash-srivastava/Overdrive-release` (MIT License)  
**Version analysée** : alpha-v22  
**Date** : 2026-06-03

---

## 1. Vue d'ensemble

Overdrive est une application Android open-source de dashcam et mode sentinelle pour véhicules **BYD DiLink v3**. Elle tourne directement sur le système Android embarqué du véhicule (head unit) sans cloud ni compte utilisateur.

| Critère            | Valeur                              |
|--------------------|-------------------------------------|
| Package            | `com.overdrive.app`                 |
| Min SDK            | 25 (Android 7.0)                    |
| Compile SDK        | 36                                  |
| Architecture       | `arm64-v8a` uniquement              |
| Taille mémoire     | ~150 MB                             |
| CPU dashcam        | < 28%                               |
| Latence streaming  | < 100 ms                            |
| Résolution max     | 2560×1920 (H.264 / H.265)           |
| Licence            | MIT                                 |

---

## 2. Stack technologique

### Langages
| Langage     | Part   |
|-------------|--------|
| Java        | 60 %   |
| Kotlin      | 14.3 % |
| JavaScript  | 13.6 % |
| HTML        | 8.4 %  |
| CSS         | 2.1 %  |
| C++         | 1.5 %  |

### Dépendances clés

| Catégorie        | Bibliothèque                        | Version     |
|------------------|-------------------------------------|-------------|
| Réseau           | Java-WebSocket                      | 1.5.4       |
| Réseau           | OkHttp                              | 4.12.0      |
| Streaming        | RTMP Client                         | –           |
| IoT/Messaging    | Eclipse Paho MQTT v3 + v5           | 1.2.5       |
| Vision           | OpenCV Mobile (arm64)               | 4.10.0      |
| Codec vidéo      | OpenH264 (Cisco)                    | 2.6.0       |
| IA/ML            | TensorFlow Lite + GPU               | 2.14.0      |
| Base de données  | H2 Database                         | 2.2.224     |
| Sécurité         | Encrypted SharedPreferences         | alpha06     |
| QR Code          | ZXing Core                          | –           |
| ADB embarqué     | DADB                                | –           |
| Tunneling        | Cloudflare / Zrok / Tailscale       | –           |

---

## 3. Architecture de l'application

### 3.1 Composants Android (AndroidManifest)

#### Activités
| Activité                  | Rôle                                         |
|---------------------------|----------------------------------------------|
| `MainActivity`            | Point d'entrée, UI principale                |
| `BlockerActivity`         | Overlay transparent bloquant les clics (Sentry) |
| `DeterrentActivity`       | Alerte plein écran lors de détection de mouvement |
| `LocationStarterActivity` | Redémarrage silencieux du service GPS        |

#### Services
| Service                      | Rôle                                              |
|------------------------------|---------------------------------------------------|
| `LocationSidecarService`     | Partage des données GPS                           |
| `DaemonKeepaliveService`     | Maintien du processus en vie                      |
| `StatusOverlayService`       | Indicateur d'enregistrement à l'écran             |
| `KeepAliveAccessibilityService` | Protection anti-kill via Accessibility         |

#### Receivers (BroadcastReceiver)
| Receiver                 | Trigger                              |
|--------------------------|--------------------------------------|
| `BootReceiver`           | Boot système + mode ACC              |
| `ProcessRevivalReceiver` | Watchdog : ressuscite le processus   |
| `LocationBootReceiver`   | Auto-démarrage GPS                   |

### 3.2 Les 33 packages fonctionnels

```
com.overdrive.app/
├── abrp/           → Intégration ABRP (route planner EV)
├── ai/             → Composants IA
├── audio/          → Capture et traitement audio
├── auth/           → Authentification ADB
├── bridge/         → Pont inter-composants
├── byd/            → SDK véhicule BYD (voir §4)
│   ├── bodywork/   → Fenêtres, portes, climatisation
│   ├── cloud/      → API cloud BYD
│   ├── radar/      → Capteurs radar parking
│   └── routing/    → Gestion de route
├── camera/         → Pipeline caméra GPU (26 fichiers, voir §5)
├── client/         → Code client web
├── config/         → Configuration
├── daemon/         → Gestion processus background
├── geo/            → Géolocalisation
├── launcher/       → Lanceur d'app
├── logging/        → Logs
├── manager/        → Gestionnaires divers
├── monitor/        → Monitoring performances
├── mqtt/           → Protocole MQTT
├── notifications/  → Notifications système
├── overlay/        → Overlays écran
├── proximity/      → Détection proximité radar
├── receiver/       → BroadcastReceivers
├── recording/      → Gestion des enregistrements
├── server/         → Serveur HTTP embarqué (26 handlers, voir §6)
├── service/
│   └── components/ → Composants de services
├── services/       → Services Android
├── shell/          → Shell ADB intégré
├── storage/        → Gestion fichiers
├── streaming/      → Streaming WebSocket/RTMP
├── surveillance/   → Moteur sentinelle GPU (30 fichiers, voir §7)
├── telegram/       → Notifications Telegram
├── telemetry/      → Télémétrie véhicule
├── trips/          → Enregistrement des trajets
├── ui/             → Composants UI
├── updater/        → Mises à jour OTA
└── util/           → Utilitaires
```

---

## 4. Intégration BYD (package `byd/`)

Accès aux systèmes véhicule via **Android Binder IPC** (pas la camera HAL standard) :

### Permissions BYD déclarées dans le manifeste
- Climatisation (AC)
- Carrosserie : fenêtres, portes, systèmes électriques
- Moteur
- BMS (Battery Management System)
- Systèmes de charge
- Sièges et sécurité
- Multimédia et audio
- Caméra 360° panoramique (AVM)
- Diagnostics
- OTA

### Fichiers clés
| Fichier                  | Rôle                                  |
|--------------------------|---------------------------------------|
| `BydCameraCoordinator.java` | Orchestration de toutes les caméras |
| `BydDataCollector.java`  | Collecte données véhicule             |
| `BydEventDaemon.java`    | Daemon d'écoute des événements BYD    |
| `BydEventClient.kt`      | Client events (Kotlin)                |
| `BydVehicleData.java`    | Modèle données véhicule               |
| `SentryEventHandler.kt`  | Gestionnaire événements sentinelle    |
| `BydFeatureIds.java`     | IDs des fonctionnalités BYD           |
| `BydConstants.java`      | Constantes du SDK                     |

---

## 5. Pipeline caméra GPU (`camera/`)

Architecture **zero-copy** via AHardwareBuffer → OpenGL ES :

```
CameraHAL (Binder)
    ↓
BinderCameraBackend.java        ← accès bas niveau via Binder
    ↓
AvmCameraHelper.java            ← Around View Monitor (360°)
    ↓
HardwareBufferTextureBinder     ← AHardwareBuffer → texture GL (zero-copy)
    ↓ (C++)
HardwareBufferTextureBinder.cpp ← côté natif
    ↓
EGLCore.java / GlUtil.java      ← contexte OpenGL ES
    ↓
GpuVirtualView.java             ← rendu virtuel GPU
    ↓
PanoramicCameraGpu.java         ← vue panoramique 360°
```

### Fichiers notables
| Fichier                      | Rôle                                  |
|------------------------------|---------------------------------------|
| `AvcHalWarmup.java`          | Préchauffage HAL AVC                  |
| `AiLaneGl.java`              | Détection voies en GL                 |
| `CameraProfiles.java`        | Profils de configuration caméra       |
| `HighResPreviewSampler.java`  | Échantillonnage haute résolution      |
| `AvmByteCallbackProbe.java`  | Probe de callback AVM                 |
| `AvmImageReaderFpsProbe.java`| Mesure FPS du ImageReader             |
| `BydApaViewpointHelper.java` | Aide APA (parking automatique)        |

---

## 6. Serveur HTTP embarqué (`server/`)

L'app expose une **API REST complète** sur le réseau local (accessible via browser ou appli web) :

```
HttpServer.java
└── AuthMiddleware.java          ← authentification
    ├── AuthApiHandler.java
    ├── AacIngestServer.java     ← ingest audio AAC
    ├── AbrpApiHandler.java      ← ABRP route planner
    ├── AudioTestApiHandler.java
    ├── BydCloudApiHandler.java  ← proxy cloud BYD
    ├── ExternalStorageApiHandler.java
    ├── GpsApiHandler.java
    ├── ModelsApiHandler.java    ← modèles IA
    ├── MqttApiHandler.java
    ├── NotificationApiHandler.java
    ├── PerformanceApiHandler.java
    ├── QualitySettingsApiHandler.java
    ├── RecordingsApiHandler.java
    ├── SafeLocationApiHandler.java
    ├── StreamingApiHandler.java
    ├── SurveillanceApiHandler.java
    ├── SurveillanceIpcServer.java  ← IPC surveillance
    ├── TcpCommandServer.java       ← commandes TCP brutes
    ├── TelegramApiHandler.java
    ├── UpdateApiHandler.java
    └── VehicleControlApiHandler.java ← contrôle véhicule
```

Streaming vidéo via `WebSocketStreamServer.java` + `GpuStreamScaler.java`.

---

## 7. Moteur de surveillance GPU (`surveillance/`)

Pipeline complet de traitement vidéo temps réel :

```
Flux caméra GPU
    ↓
GpuDownscaler.java              ← réduction résolution GPU
    ↓
NativeMotion.java (JNI)
    ↓ (C++)
native_motion.cpp               ← détection mouvement OpenCV
motion_pipeline_v2.cpp          ← pipeline v2
texture_tracker.cpp             ← tracking texture GL
    ↓ (retour Java)
MotionPipelineV2.java
    ↓
FoveatedCropper.java            ← recadrage fovéa (zone intérêt)
    ↓
GpuSurveillancePipeline.java    ← pipeline GPU principal
    ↓
ActorTracker.java               ← suivi d'objets
SeverityClassifier.java         ← classification menace (TFLite)
DistanceEstimator.java          ← estimation distance
    ↓
CrossQuadrantTracker.java       ← tracking multi-quadrant
AdaptiveBitrateController.java  ← adaptation bitrate
    ↓
HardwareEventRecorderGpu.java   ← enregistrement événement GPU
GpuMosaicRecorder.java          ← enregistrement multi-caméras
    ↓
AacCircularBuffer.java          ← buffer circulaire audio
H264CircularBuffer.java         ← buffer circulaire vidéo
H264ByteRingBuffer.java         ← ring buffer bytes H.264
    ↓
SrtWriter.java                  ← métadonnées SRT (horodatage)
```

### Gestion zones de confiance
- `SafeLocation.java` / `SafeLocationManager.java` : zones où la sentinelle est désactivée
- `SurveillanceSchedule.java` : règles temporelles d'activation
- `DetectionBaseline.java` : calibrage de base du mouvement

### Affichage / UI surveillance
- `ScreenDeterrent.java` → `DeterrentActivity` : alerte visuelle
- `EventTimelineCollector.java` : timeline des événements
- `ThumbnailBuffer.java` : miniatures des clips

---

## 8. Module C++ natif

```
app/src/main/cpp/
├── camera/
│   └── HardwareBufferTextureBinder.cpp  ← zero-copy AHardwareBuffer
└── surveillance/
    ├── native_motion.cpp                ← détection mouvement (OpenCV + NEON)
    ├── motion_pipeline_v2.cpp           ← pipeline v2
    └── texture_tracker.cpp              ← tracking GPU texture
```

**Optimisations** :
- NEON SIMD (ARM) activé conditionnellement
- Liaison statique OpenCV Mobile (~3 MB)
- Symboles strippés (visibilité cachée)
- Sections fonction/données isolées (linker hardening)
- EGL + OpenGL ES 2 pour accélération GPU

---

## 9. Application web intégrée (`assets/web/`)

Une SPA (Single Page Application) est embarquée dans les assets et déployée par la tâche Gradle `extractWebAssets`. Elle communique avec le serveur HTTP interne et le WebSocket de streaming.

Contenu assets :
- `web/` — application frontend complète
- `server-i18n/` — internationalisation API
- `models/` — modèles TFLite (détection personnes/véhicules)
- `byd/` — ressources spécifiques BYD
- `overlay/` — éléments d'overlay
- `notifications-categories.json`

---

## 10. Sécurité et persistance

### Mécanismes anti-kill (triple watchdog)
1. `DaemonKeepaliveService` — service foreground permanent
2. `ProcessRevivalReceiver` — BroadcastReceiver watchdog
3. `KeepAliveAccessibilityService` — abus du service Accessibility pour rester actif

### Permissions élevées
- `WRITE_SECURE_SETTINGS` — modification paramètres système sécurisés
- `FORCE_STOP_PACKAGES` — arrêt forcé d'autres apps
- `SYSTEM_ALERT_WINDOW` — overlay sur toutes les apps
- `BIND_ACCESSIBILITY_SERVICE` — service d'accessibilité

### Sécurité du build
- ProGuard activé en release (+ strip des logs)
- Signing via variables d'environnement CI (`KEYSTORE_*`)
- SharedPreferences chiffrées
- `generate_safe_enc.py` pour chiffrement des secrets
- `AuthMiddleware` sur le serveur HTTP

---

## 11. Accès distant

| Méthode        | Description                              |
|----------------|------------------------------------------|
| LAN            | Accès direct réseau local                |
| Cloudflare Tunnel | Tunnel HTTPS sans port forwarding   |
| Zrok           | Tunnel P2P chiffré                       |
| Tailscale      | VPN mesh entre appareils                 |

Combiné avec le serveur HTTP embarqué + WebSocket streaming → accès complet depuis n'importe où.

---

## 12. Flux de données simplifié

```
Caméras BYD (Binder)
    ↓
BydCameraCoordinator
    ↓ (zero-copy GPU)
GpuSurveillancePipeline ←→ NativeMotion (C++/OpenCV)
    ↓                            ↓
Enregistrement H.264       Détection actors
    ↓                            ↓
H264CircularBuffer         SeverityClassifier (TFLite)
    ↓                            ↓
RecordingModeManager       Notifications (Telegram/MQTT)
    ↓
Storage local
    ↓
HttpServer (REST + WebSocket)
    ↓
Web SPA (browser/in-car)
    ↓
Accès distant (Cloudflare/Tailscale)
```

---

## 13. Points d'intérêt pour le reverse engineering

| Point d'entrée                  | Pourquoi                                                  |
|---------------------------------|-----------------------------------------------------------|
| `HttpServer.java`               | Tous les endpoints REST → surface d'attaque API          |
| `AuthMiddleware.java`           | Mécanisme d'auth à analyser                               |
| `TcpCommandServer.java`         | Serveur TCP brut → potentiellement peu sécurisé          |
| `VehicleControlApiHandler.java` | Contrôle véhicule via API → critique                     |
| `BydCameraCoordinator.java`     | Accès Binder non-standard aux caméras                     |
| `NativeMotion.java` + JNI       | Pont Java↔C++ → vecteur d'analyse mémoire               |
| `generate_safe_enc.py`          | Schéma de chiffrement des secrets                         |
| `DaemonKeepaliveService`        | Mécanisme persistance → étude anti-kill                  |
| `KeepAliveAccessibilityService` | Abus accessibility → technique connue                    |
| `BydFeatureIds.java`            | IDs propriétaires BYD → reverse du SDK véhicule         |
| `assets/models/`                | Modèles TFLite → analyse des capacités IA               |
| `proguard-rules-strip-logs.pro` | Logs supprimés → debug plus difficile                    |

---

*Analyse produite par reverse engineering statique du code source public.*
