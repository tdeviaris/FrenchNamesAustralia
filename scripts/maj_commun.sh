#!/usr/bin/env bash
# Ramène le moteur commun (sous-module commun/, dépôt toponymes-commun) à sa
# dernière version, puis l'enregistre dans ce site. Voir commun/README.md.
set -euo pipefail
cd "$(dirname "$0")/.."
git submodule update --init --remote commun
if git diff --quiet -- commun; then
    echo "Le moteur commun est déjà à jour."
else
    git add commun
    git commit -m "Met à jour le moteur commun ($(git -C commun log -1 --format=%h))"
    echo "Moteur commun mis à jour : git push pour publier."
fi
