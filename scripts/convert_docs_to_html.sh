#!/usr/bin/env bash
#
# Ce script convertit les fichiers .docx, .doc, et .rtf en HTML.
# Il préserve la structure des sous-dossiers.
#
set -euo pipefail

# --- Configuration ---

# Répertoire racine du projet (détecté automatiquement)
# On suppose que ce script est dans un sous-dossier 'scripts' du projet.
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$( dirname "$SCRIPT_DIR" )"

# Dossier source contenant les documents .docx, .rtf, etc.
# À créer s'il n'existe pas.
SRC="$PROJECT_ROOT/source_documents"

# Dossier de destination pour les fichiers HTML générés.
# Correspond au dossier 'details' de votre site.
DST="$PROJECT_ROOT/details"

# Détection automatique de LibreOffice (soffice)
# D'abord dans le PATH, puis à l'emplacement standard sur macOS.
SOFFICE=$(command -v soffice || true)
if [[ -z "$SOFFICE" && -x "/Applications/LibreOffice.app/Contents/MacOS/soffice" ]]; then
  SOFFICE="/Applications/LibreOffice.app/Contents/MacOS/soffice"
fi

# Fichier de log pour tracer les opérations et les erreurs.
LOG="$PROJECT_ROOT/convert_docs.log"

# --- Logique du script ---

# Vérification de soffice
if [[ ! -x "$SOFFICE" ]]; then
  echo "ERREUR : L'exécutable 'soffice' de LibreOffice est introuvable." >&2
  echo "Veuillez vérifier que LibreOffice est installé et que le chemin est correct." >&2
  exit 1
fi

# Création des dossiers si nécessaire
mkdir -p "$SRC"
mkdir -p "$DST"

# Nettoyage du fichier de log précédent
: > "$LOG"

echo "--- Début de la conversion ---" | tee -a "$LOG"
echo "Version de LibreOffice :" | tee -a "$LOG"
"$SOFFICE" --version | tee -a "$LOG"
echo "Source : $SRC" | tee -a "$LOG"
echo "Destination : $DST" | tee -a "$LOG"
echo "---------------------------------" | tee -a "$LOG"

# Le filtre de conversion. Les images ne sont pas intégrées (elles seront dans un sous-dossier).
# Pour intégrer les images en base64, utilisez "html:HTML:EmbedImages"
FILTER='html:HTML'

# Recherche des fichiers et conversion
# L'utilisation de -print0 et read -d '' permet de gérer les noms de fichiers avec des espaces.
find "$SRC" -type f \( -iname "*.docx" -o -iname "*.doc" -o -iname "*.rtf" \) -print0 |
while IFS= read -r -d '' file_path; do
  relative_path="${file_path#$SRC/}"
  output_dir="$DST/$(dirname "$relative_path")"
  mkdir -p "$output_dir"
  base_name="$(basename "${file_path%.*}")"
  
  echo "CONVERSION : $relative_path -> $output_dir/$base_name.html" | tee -a "$LOG"
  
  if "$SOFFICE" --headless --convert-to "$FILTER" --outdir "$output_dir" "$file_path" >>"$LOG" 2>&1; then
    echo "  -> SUCCÈS" | tee -a "$LOG"
    html_file="$output_dir/$(basename "${file_path%.*}").html"
    # Ajout des favicons
    sed -i '' -e '/<\/head>/i\
<link rel="icon" type="image/png" sizes="16x16" href="../img/favicon16.png">\
<link rel="icon" type="image/png" sizes="32x32" href="../img/favicon32.png">
' "$html_file"
  else
    echo "  -> ÉCHEC : $relative_path (voir les détails dans $LOG)" | tee -a "$LOG" >&2
  fi
done

echo "--- Conversion terminée ---" | tee -a "$LOG"
echo "Le journal complet est disponible dans : $LOG" | tee -a "$LOG"