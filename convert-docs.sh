cat > ~/convert-docs.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

# Réglages -> adapter ces chemins
SRC="/Users/tdeviaris/Desktop/Toponymes/OneDrive_26_22-09-2025"
DST="/Users/tdeviaris/Desktop/Toponymes/HTML"
SOFFICE="/Applications/LibreOffice.app/Contents/MacOS/soffice"
EMBED_IMAGES=0          # 1 = intégrer images en base64, 0 = images externes
LOG="$HOME/convert-docs.log"

mkdir -p "$DST"
: > "$LOG"

# Vérifier soffice
if [ ! -x "$SOFFICE" ]; then
  echo "ERREUR: soffice introuvable à $SOFFICE" | tee -a "$LOG" >&2
  exit 2
fi
"$SOFFICE" --version | tee -a "$LOG"

if [ "$EMBED_IMAGES" -eq 1 ]; then
  FILTER='html:HTML:EmbedImages'
else
  FILTER='html:HTML'
fi

find "$SRC" -type f \( -iname "*.docx" -o -iname "*.doc" -o -iname "*.rtf" \) -print0 |
while IFS= read -r -d '' f; do
  rel="${f#$SRC/}"
  outdir="$DST/$(dirname "$rel")"
  mkdir -p "$outdir"
  base="$(basename "${f%.*}")"
  echo "CONVERT: $f -> $outdir/$base.html" | tee -a "$LOG"
  if "$SOFFICE" --headless --convert-to "$FILTER" --outdir "$outdir" "$f" >>"$LOG" 2>&1; then
    echo "OK: $f" | tee -a "$LOG"
  else
    echo "FAIL: $f (voir détails dans $LOG)" | tee -a "$LOG" >&2
  fi
done
EOF

chmod +x ~/convert-docs.sh
~/convert-docs.sh
