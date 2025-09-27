#!/usr/bin/env bash
#
# Ce script convertit les fichiers .docx, .doc et .rtf en HTML
# en conservant l'arborescence des dossiers. Il peut être appelé
# sans argument (conversion de tous les fichiers) ou avec une liste
# de fichiers spécifiques (chemin absolu ou relatif à Source_documents).
#
set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$( dirname "$SCRIPT_DIR" )"

SRC="$PROJECT_ROOT/Source_documents"
DST="$PROJECT_ROOT/details"
LOG="$PROJECT_ROOT/convert_docs.log"
POSTPROCESSOR="$SCRIPT_DIR/postprocess_html.py"

SOFFICE=$(command -v soffice || true)
if [[ -z "$SOFFICE" && -x "/Applications/LibreOffice.app/Contents/MacOS/soffice" ]]; then
  SOFFICE="/Applications/LibreOffice.app/Contents/MacOS/soffice"
fi

if [[ ! -x "$SOFFICE" ]]; then
  echo "ERREUR : L'exécutable 'soffice' de LibreOffice est introuvable." >&2
  echo "Installez LibreOffice ou mettez à jour le chemin dans ce script." >&2
  exit 1
fi

mkdir -p "$SRC" "$DST"
: > "$LOG"

echo "--- Début de la conversion ---" | tee -a "$LOG"
echo "Version de LibreOffice :" | tee -a "$LOG"
"$SOFFICE" --version | tee -a "$LOG"
echo "Source : $SRC" | tee -a "$LOG"
echo "Destination : $DST" | tee -a "$LOG"
echo "---------------------------------" | tee -a "$LOG"

FILTER='html:HTML'

declare -a INPUT_FILES=()
if [[ $# -gt 0 ]]; then
  for arg in "$@"; do
    if [[ -f "$arg" ]]; then
      INPUT_FILES+=("$(cd "$(dirname "$arg")" && pwd)/$(basename "$arg")")
    elif [[ -f "$SRC/$arg" ]]; then
      INPUT_FILES+=("$SRC/$arg")
    else
      echo "AVERTISSEMENT : fichier introuvable -> $arg" | tee -a "$LOG"
    fi
  done
fi

if [[ ${#INPUT_FILES[@]} -eq 0 ]]; then
  while IFS= read -r -d '' file_path; do
    INPUT_FILES+=("$file_path")
  done < <(find "$SRC" -type f \( -iname "*.docx" -o -iname "*.doc" -o -iname "*.rtf" \) -print0)
fi

for file_path in "${INPUT_FILES[@]}"; do
  relative_path="$file_path"
  if [[ "$file_path" == $SRC/* ]]; then
    relative_path="${file_path#$SRC/}"
  else
    relative_path="$(basename "$file_path")"
  fi

  output_dir="$DST/$(dirname "$relative_path")"
  mkdir -p "$output_dir"
  base_name="$(basename "${file_path%.*}")"

  echo "CONVERSION : $relative_path -> $output_dir/$base_name.html" | tee -a "$LOG"

  if "$SOFFICE" --headless --convert-to "$FILTER" --outdir "$output_dir" "$file_path" >>"$LOG" 2>&1; then
    echo "  -> SUCCÈS" | tee -a "$LOG"
    html_file="$output_dir/$base_name.html"

    sed -i '' -e '/<\/head>/i\
<link rel="icon" type="image/png" sizes="16x16" href="../img/favicon16.png">\
<link rel="icon" type="image/png" sizes="32x32" href="../img/favicon32.png">
' "$html_file"

    if [[ -f "$POSTPROCESSOR" ]]; then
      if ! python3 "$POSTPROCESSOR" "$file_path" "$html_file" >>"$LOG" 2>&1; then
        echo "  -> AVERTISSEMENT : post-traitement échoué pour $relative_path" | tee -a "$LOG"
      fi
    fi
  else
    echo "  -> ÉCHEC : $relative_path (voir les détails dans $LOG)" | tee -a "$LOG" >&2
  fi
done

echo "--- Conversion terminée ---" | tee -a "$LOG"
echo "Le journal complet est disponible dans : $LOG" | tee -a "$LOG"
