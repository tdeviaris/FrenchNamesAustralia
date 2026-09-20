#!/usr/bin/env bash
# Fait basculer le chatbot en production sur un autre Vector Store.
#
#   ./rag/basculer_magasin.sh                 # bascule sur VECTOR_STORE_ID_V2
#   ./rag/basculer_magasin.sh vs_xxxxxxxx     # bascule sur un magasin nommé
#   ./rag/basculer_magasin.sh --retour        # revient à la valeur précédente
#
# Il faut être connecté : `vercel login`. Vercel ne sait pas modifier une
# variable en place, il faut la retirer puis la reposer — et un déploiement
# neuf, sans quoi la nouvelle valeur ne sert à rien.
set -euo pipefail

RACINE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RACINE"
MEMOIRE="rag/.magasin_precedent"

if ! vercel whoami >/dev/null 2>&1; then
  echo "❌ Pas de session Vercel. Lance d'abord : vercel login" >&2
  exit 1
fi

if [ "${1:-}" = "--retour" ]; then
  [ -f "$MEMOIRE" ] || { echo "❌ Aucune valeur précédente notée dans $MEMOIRE" >&2; exit 1; }
  CIBLE="$(cat "$MEMOIRE")"
  echo "↩️  Retour au magasin $CIBLE"
else
  CIBLE="${1:-$(grep '^VECTOR_STORE_ID_V2=' .env | cut -d= -f2)}"
  [ -n "$CIBLE" ] || { echo "❌ Aucun magasin cible." >&2; exit 1; }
fi

ACTUEL="$(grep '^VECTOR_STORE_ID=' .env | cut -d= -f2 || true)"
echo "   actuel en local : ${ACTUEL:-inconnu}"
echo "   cible           : $CIBLE"
echo

# On garde de quoi revenir en arrière avant de toucher à quoi que ce soit.
[ -n "$ACTUEL" ] && [ "${1:-}" != "--retour" ] && printf '%s' "$ACTUEL" > "$MEMOIRE"

echo "🗑  Retrait de l'ancienne variable (production)…"
vercel env rm VECTOR_STORE_ID production --yes 2>/dev/null || echo "   (elle n'existait pas)"

echo "➕ Pose de la nouvelle valeur…"
printf '%s' "$CIBLE" | vercel env add VECTOR_STORE_ID production

echo "🚀 Redéploiement en production…"
vercel --prod

# Le fichier local suit, pour que les scripts d'à côté voient la même chose.
if [ -n "$ACTUEL" ]; then
  sed -i '' "s|^VECTOR_STORE_ID=.*|VECTOR_STORE_ID=$CIBLE|" .env
fi

echo
echo "✅ Bascule faite. Pour revenir : ./rag/basculer_magasin.sh --retour"
echo "   Éprouve la production avec une question dont la réponse n'existe"
echo "   que dans le nouveau corpus, par exemple :"
echo "   « Que raconte le journal de Flinders le 31 juillet 1801 ? »"
