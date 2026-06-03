#!/usr/bin/env bash
# =============================================================
# probe_binder.sh — Sondage des services Binder BYD via ADB
#
# Usage :
#   ./tools/probe_binder.sh                  # sonde tous les services cibles
#   ./tools/probe_binder.sh byd_bodywork     # sonde un service spécifique
#   ./tools/probe_binder.sh --list           # liste les services BYD dispo
#
# Prérequis : adb connecté (wireless ou USB), ADB autorisé sur la head unit
# =============================================================

set -euo pipefail

ADB="${ADB:-adb}"
MAX_CODE="${MAX_CODE:-25}"
OUTDIR="./tools/probe_results"
mkdir -p "$OUTDIR"

TARGETS=(
  byd_bodywork
  byd_avm
  byd_avc
  accmodemanager
  byd_datacached
  bg_datacache
  byd_vehicle
  byd_engine
  byd_bms
  CarService
)

# ── Helpers ──────────────────────────────────────────────────

log()  { echo "[$(date +%H:%M:%S)] $*"; }
shell(){ $ADB shell "$@" 2>/dev/null || true; }

# ── Listing services ─────────────────────────────────────────

list_services() {
  log "Services BYD disponibles sur la head unit :"
  shell service list | grep -iE "byd|acc|avm|avc|vehicle|car|engine|bms" | sort
}

# ── Sondage d'un service (codes 1..MAX_CODE) ─────────────────

probe_service() {
  local svc="$1"
  local outfile="$OUTDIR/${svc}_$(date +%Y%m%d_%H%M%S).txt"

  log "Sondage : $svc (codes 1..$MAX_CODE)"
  echo "=== Service: $svc ===" > "$outfile"
  echo "Date: $(date)" >> "$outfile"
  echo "" >> "$outfile"

  local found=0
  for code in $(seq 1 "$MAX_CODE"); do
    # service call <svc> <code> — sans argument (lecture seule)
    result=$(shell service call "$svc" "$code" 2>&1 || true)

    if echo "$result" | grep -q "Result:"; then
      raw=$(echo "$result" | grep "Result:" | head -1)
      echo "code=$code : $raw" >> "$outfile"

      # Décode les valeurs int32 (format BYD : "Result: Parcel(0x00000001 ...)")
      hex_val=$(echo "$raw" | grep -oP '0x[0-9a-fA-F]{8}' | head -1 || true)
      if [ -n "$hex_val" ]; then
        dec_val=$((16#${hex_val#0x}))
        echo "  → int32 = $dec_val (0=OFF 1=ACC 2=ON 3=OK si power_level)" >> "$outfile"
        log "  code=$code → $raw | dec=$dec_val"
        found=$((found + 1))
      fi

    elif echo "$result" | grep -qi "exception\|security\|denied"; then
      echo "code=$code : SECURITY_EXCEPTION" >> "$outfile"
    fi
  done

  echo "" >> "$outfile"
  echo "Candidats trouvés : $found" >> "$outfile"
  log "Résultats → $outfile ($found codes avec réponse)"
}

# ── Lecture directe des valeurs connues ──────────────────────

read_known_values() {
  log "=== Lecture valeurs directes ==="

  log "ACC state (byd_bodywork code=1) :"
  shell service call byd_bodywork 1 | grep -oP '0x[0-9a-fA-F]+' | head -1 | xargs -I{} printf "  hex=%s dec=%d\n" {} "$((16#{}))" 2>/dev/null || log "  échec"

  log "ACC state (accmodemanager code=1) :"
  shell service call accmodemanager 1 | grep "Result:" || log "  échec"

  log "BYD vehicle data (codes 1..5) :"
  for c in 1 2 3 4 5; do
    r=$(shell service call byd_bodywork "$c" 2>/dev/null || true)
    [ -n "$r" ] && log "  code=$c → $r"
  done
}

# ── Dump complet AIDL ────────────────────────────────────────

dump_service() {
  local svc="$1"
  log "Dump service $svc :"
  shell dumpsys "$svc" 2>/dev/null | head -50 || log "  dumpsys indisponible"
}

# ── Main ─────────────────────────────────────────────────────

if ! $ADB get-state &>/dev/null; then
  echo "ERREUR: aucun device ADB connecté"
  echo "Lancer: adb connect <IP_HEAD_UNIT>:5555"
  exit 1
fi

log "Device: $($ADB get-serialno 2>/dev/null || echo 'inconnu')"
log "Model:  $(shell getprop ro.product.model)"
log "Build:  $(shell getprop ro.build.version.release)"
echo ""

case "${1:-all}" in
  --list)
    list_services
    ;;
  --read)
    read_known_values
    ;;
  --dump)
    dump_service "${2:-byd_bodywork}"
    ;;
  all)
    list_services
    echo ""
    for svc in "${TARGETS[@]}"; do
      probe_service "$svc" || log "WARN: $svc skipped"
      echo ""
    done
    read_known_values
    ;;
  *)
    # Sonde un service spécifique passé en argument
    probe_service "$1"
    ;;
esac

log "Rapport complet dans $OUTDIR/"
