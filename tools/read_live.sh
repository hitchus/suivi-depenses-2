#!/usr/bin/env bash
# =============================================================
# read_live.sh — Lecture en temps réel des valeurs BYD confirmées
#
# À utiliser APRÈS avoir identifié les bons codes transact
# via probe_binder.sh ou DiagnosticActivity.
#
# Mettre à jour les variables CODE_* avec les codes trouvés.
# =============================================================

ADB="${ADB:-adb}"
INTERVAL="${INTERVAL:-1}"  # secondes

# ── Codes transact à valider / renseigner après probe ────────
# Valeurs par défaut = hypothèse à confirmer sur le vrai véhicule
SVC_BODYWORK="byd_bodywork"
CODE_POWER_LEVEL=1        # à confirmer
CODE_GEAR=3               # à confirmer
CODE_SPEED=5              # à confirmer
CODE_BATTERY_VOLTAGE=7    # à confirmer

decode_int() {
  echo "$1" | grep -oP '0x[0-9a-fA-F]{8}' | head -1 \
    | xargs -I{} python3 -c "print(int('{}', 16))" 2>/dev/null || echo "?"
}

decode_str() {
  # Extrait la chaîne UTF-16 du Parcel BYD
  echo "$1" | grep -oP "\"[A-Za-z]{1,3}\"" | tr -d '"' | head -1 || echo "?"
}

power_to_label() {
  case "$1" in
    0) echo "OFF" ;; 1) echo "ACC" ;; 2) echo "ON" ;; 3) echo "RUN" ;; *) echo "?" ;;
  esac
}

echo "Lecture live BYD (Ctrl+C pour arrêter)"
echo "SVC=$SVC_BODYWORK | INTERVAL=${INTERVAL}s"
echo "──────────────────────────────────────────"

while true; do
  raw_power=$(adb shell service call "$SVC_BODYWORK" "$CODE_POWER_LEVEL" 2>/dev/null || echo "")
  raw_gear=$(adb shell service call "$SVC_BODYWORK" "$CODE_GEAR" 2>/dev/null || echo "")

  power_int=$(decode_int "$raw_power")
  power_label=$(power_to_label "$power_int")
  gear=$(decode_str "$raw_gear")
  [ -z "$gear" ] && gear=$(decode_int "$raw_gear")

  printf "\r[%s]  ACC=%-3s (%s)  Gear=%-2s     " \
    "$(date +%H:%M:%S)" "$power_label" "$power_int" "$gear"

  sleep "$INTERVAL"
done
