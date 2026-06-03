#!/usr/bin/env bash
# =============================================================
# install_and_diag.sh — Installe l'APK et lance le diagnostic
#
# Usage :
#   ./tools/install_and_diag.sh [IP_HEAD_UNIT]
#
# Exemple :
#   ./tools/install_and_diag.sh 192.168.1.100
# =============================================================

set -euo pipefail

IP="${1:-}"
ADB="adb"

# Connexion wireless ADB si IP fournie
if [ -n "$IP" ]; then
  echo "Connexion ADB wireless → $IP:5555"
  $ADB connect "$IP:5555"
  sleep 1
fi

if ! $ADB get-state &>/dev/null; then
  echo "ERREUR: pas de device ADB"
  echo "Activer Wireless ADB sur la head unit, puis :"
  echo "  adb connect <IP>:5555"
  exit 1
fi

MODEL=$($ADB shell getprop ro.product.model 2>/dev/null || echo "unknown")
echo "Device: $MODEL"

# Build debug APK si nécessaire
APK_PATH="app/build/outputs/apk/debug/app-debug.apk"
if [ ! -f "$APK_PATH" ]; then
  echo "Build de l'APK debug..."
  ./gradlew assembleDebug
fi

# Installer
echo "Installation APK..."
$ADB install -r "$APK_PATH"

# Accorder les permissions système nécessaires
PKG="com.bydcam.app"
echo "Configuration permissions..."
$ADB shell pm grant "$PKG" android.permission.WRITE_SECURE_SETTINGS 2>/dev/null || true
$ADB shell pm grant "$PKG" android.permission.CAMERA 2>/dev/null || true
$ADB shell pm grant "$PKG" android.permission.RECORD_AUDIO 2>/dev/null || true
$ADB shell pm grant "$PKG" android.permission.ACCESS_FINE_LOCATION 2>/dev/null || true
$ADB shell pm grant "$PKG" android.permission.ACCESS_BACKGROUND_LOCATION 2>/dev/null || true
$ADB shell appops set "$PKG" MANAGE_EXTERNAL_STORAGE allow 2>/dev/null || true

# Whitelist batterie
$ADB shell dumpsys deviceidle whitelist "+$PKG" 2>/dev/null || true

# Lancer l'activité de diagnostic
echo ""
echo "Lancement DiagnosticActivity..."
$ADB shell am start -n "$PKG/.diag.DiagnosticActivity"

echo ""
echo "Pour voir les logs en temps réel :"
echo "  adb logcat -s BydServiceProbe:V BydCameraBackend:V AccMonitor:V"
echo ""
echo "Pour récupérer le rapport après le sondage :"
echo "  adb pull /sdcard/BydCam/diag/ ./tools/probe_results/"
