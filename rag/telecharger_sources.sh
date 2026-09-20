#!/usr/bin/env bash
# Rapatrie dans rag/sources/ les journaux que le site ne porte pas lui-même.
#
#   ./rag/telecharger_sources.sh sydney      transcriptions du Baudin Legacy Project
#   ./rag/telecharger_sources.sh gutenberg   le récit publié de Flinders
#   ./rag/telecharger_sources.sh hamelin     les transcriptions de Dany Bréelle
#   ./rag/telecharger_sources.sh tout
#
# Le volet « hamelin » tape dans un dossier OneDrive partagé. Le partage est
# ouvert, mais SharePoint refuse curl tant qu'on ne lui présente pas le cookie
# FedAuth qu'il pose lors d'une visite du lien. Voir le mode d'emploi dans
# rag/README.md, section Hamelin. Le cookie ne vit que quelques heures.
set -euo pipefail

RACINE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCES="$RACINE/rag/sources"

telecharge_sydney() {
  echo "📘 Baudin Legacy Project — transcriptions en français"
  mkdir -p "$SOURCES/sydney"
  cd "$SOURCES/sydney"
  # La page liste les journaux ; on ne garde que les PDF dont le nom ne dit pas
  # « english », c'est-à-dire les transcriptions en langue d'origine.
  curl -sfL https://baudin.sydney.edu.au/journals/ \
    | grep -oE 'href="[^"]+\.pdf"' | sed 's/href="//;s/"$//' \
    | sed 's|^/|https://baudin.sydney.edu.au/|' | sort -u \
    | grep -vi english > /tmp/journaux_fr.txt
  echo "   $(wc -l < /tmp/journaux_fr.txt) fichiers"
  xargs -n1 -P6 curl -sfL -O < /tmp/journaux_fr.txt
  ls -1 *.pdf | wc -l
}

telecharge_gutenberg() {
  echo "📕 Project Gutenberg Australia — A Voyage to Terra Australis"
  mkdir -p "$SOURCES/gutenberg"
  cd "$SOURCES/gutenberg"
  # Le serveur débite lentement et coupe au bout d'un moment : il faut lui
  # laisser plusieurs minutes par volume, et vérifier la taille obtenue.
  for couple in "1 e00049" "2 e00050"; do
    set -- $couple
    curl -s --http1.1 --max-time 900 --retry 3 \
      -o "flinders_voyage_vol$1_$2.html" "https://gutenberg.net.au/ebooks/$2.html"
    echo "   vol. $1 : $(wc -c < "flinders_voyage_vol$1_$2.html") octets"
  done
  # Le fichier complet se termine par </html> ; tronqué, il s'arrête en pleine
  # phrase sans qu'aucune erreur ne soit levée.
  for f in flinders_voyage_vol*.html; do
    tail -c 30 "$f" | grep -q "</html>" || echo "   ⚠️  $f est tronqué : relancer."
  done
}

telecharge_hamelin() {
  echo "📗 Journal de Hamelin — transcriptions Dany Bréelle (OneDrive)"
  if [ -z "${FEDAUTH:-}" ]; then
    echo "   ❌ FEDAUTH n'est pas définie. Voir rag/README.md, section Hamelin." >&2
    exit 1
  fi
  local api="https://onedrive.live.com/personal/c0e71b1d688d80f9/_api/web/GetFileByServerRelativePath(decodedurl="
  local dossier="/personal/c0e71b1d688d80f9/Documents/Documents/WORK/researchwork/Hamelin"
  mkdir -p "$SOURCES/hamelin/cahier1_transcription"

  prends() { # $1 = chemin serveur url-encodé, $2 = destination
    local code
    code=$(curl -s -o "$2" -w "%{http_code}" -H "Cookie: FedAuth=$FEDAUTH" "$api'$1')/\$value")
    printf "   %s  %-45s %s octets\n" "$code" "$(basename "$2")" "$(wc -c < "$2")"
  }

  cd "$SOURCES/hamelin"
  prends "$dossier/Hamelin%20%20vol%201%20.doc"    "Hamelin_vol1_2023.doc"
  prends "$dossier/Hamelin_vol1_d1.doc"            "Hamelin_vol1_d1.doc"
  prends "$dossier/Hamelin_vol1_d1-index.doc"      "Hamelin_vol1_d1-index.doc"
  prends "$dossier/Hamelinvol1pp1-15.doc"          "Hamelin_vol1_pp1-15.doc"
  prends "$dossier/journalHamreprise1.doc"         "Hamelin_journal_reprise1.doc"
  prends "$dossier/Hamelinetsamission.doc"         "Hamelin_et_sa_mission.doc"
  prends "$dossier/Naturalisteau%20Port%20Jackson%20le%20temoignagedu%20capitaineHamelin.pdf" \
         "Hamelin_Naturaliste_Port_Jackson.pdf"

  cd "$SOURCES/hamelin/cahier1_transcription"
  local sous="$dossier/transciptcahier1%20oct05"
  for f in "1-du6thermidorau30vendemiairean9.doc" "2-du 1 au 30 brumaire an9.doc" \
           "3-frimaire an9.doc" "4- nivôse an9.doc" "5- pluviôse an9.doc" \
           "6- ventôse an9.doc" "7- germinal an9.doc" "8- floréal an9.doc" \
           "9- prairial an9.doc" "10- messidoran9.doc" "11- thermidor an9.doc" \
           "protocole.doc" "ProjetBaudinprotocoletransc.doc"; do
    enc=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "$f")
    prends "$sous/$enc" "$(printf '%s' "$f" | tr ' ' '_')"
  done
}

case "${1:-tout}" in
  sydney)    telecharge_sydney ;;
  gutenberg) telecharge_gutenberg ;;
  hamelin)   telecharge_hamelin ;;
  tout)      telecharge_sydney; telecharge_gutenberg; telecharge_hamelin ;;
  *) echo "Usage : $0 [sydney|gutenberg|hamelin|tout]" >&2; exit 2 ;;
esac
