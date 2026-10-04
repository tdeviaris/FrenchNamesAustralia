#!/usr/bin/env bash
# Copie en lecture, dans ce site, les données Flinders produites dans le site
# Flinders Place Names (../FlindersPlaceNames), dont ont besoin ici le serveur
# MCP (mcp/), la base de connaissance (rag/) et l'assistant.
#
# Le site Flinders est propriétaire de ces fichiers : on ne les corrige jamais
# ici, mais là-bas, puis on relance ce script. flinders.json n'est pas copié :
# le classeur Google le publie lui-même dans les deux dépôts.
#
# En retour, journaux_reperes.json -- l'index des journées qui ont un point de
# route, que scripts/reperes_journaux.py calcule ici sur les routes des deux
# sites -- part dans le site Flinders, dont l'assistant s'en sert aussi.
#
#     scripts/synchro_flinders.sh           # copie ce qui a changé
#     scripts/synchro_flinders.sh --verifie # dit seulement ce qui diffère
set -euo pipefail
ICI="$(cd "$(dirname "$0")/.." && pwd)"
FLINDERS="${FLINDERS:-$ICI/../FlindersPlaceNames}"
VERIFIE=0; [ "${1:-}" = "--verifie" ] && VERIFIE=1
[ -d "$FLINDERS/data" ] || { echo "Site Flinders introuvable : $FLINDERS" >&2; exit 1; }

DE_FLINDERS=(
  data/flinders_parcours.geojson
  data/flinders_citations_fr.json
  data/attributions_hakluyt.json
  data/visuels_flinders.json
  data/flinders_calage_manuel.json
  data/flinders_carte_releves.json
  data/journaux/flinders_fr.json
  data/journaux/flinders_en.json
)
VERS_FLINDERS=(
  data/journaux_reperes.json
)

copie() {  # source cible
  if [ -f "$2" ] && cmp -s "$1" "$2"; then return; fi
  if [ $VERIFIE = 1 ]; then echo "diffère : $2"; else cp "$1" "$2"; echo "copié : $2"; fi
}
for f in "${DE_FLINDERS[@]}"; do copie "$FLINDERS/$f" "$ICI/$f"; done
for f in "${VERS_FLINDERS[@]}"; do copie "$ICI/$f" "$FLINDERS/$f"; done
echo "Synchronisation terminée."
