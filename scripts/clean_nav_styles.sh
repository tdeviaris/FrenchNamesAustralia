#!/bin/bash
# Script pour supprimer tous les styles de navigation des fichiers HTML
# Ces styles sont maintenant centralisés dans css/nav.css

FILES=(
    "SourcesE.html"
    "SourcesF.html"
    "acteursE.html"
    "acteursF.html"
    "cartesE.html"
    "cartesF.html"
    "glossaryE.html"
    "glossaryF.html"
    "resources.html"
)

echo "🧹 Nettoyage des styles de navigation inline..."

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  Traitement de $file..."
        # Cette commande sera exécutée manuellement par fichier
    fi
done

echo "✅ Utilisez la commande Edit pour chaque fichier individuellement"
