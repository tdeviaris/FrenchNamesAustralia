#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/map.html"
DEST="$ROOT/mapWA.html"
cp "$SRC" "$DEST"
python - <<'PY'
from pathlib import Path
import re
root = Path(__file__).resolve().parent.parent
path = root / "mapWA.html"
text = path.read_text()
if "STATE_FILTER" in text:
    # Already filtered
    exit()
# Update title
text = re.sub(r"(<title>)([^<]*)(</title>)", r"\\1Baudin Map (WA) - French Names Along the Australian Coastline\\3", text, count=1)
pattern = re.compile(r"(const baudinPlaces = await loadExpedition\(expeditionConfigs\.baudin\);\s+const entrePlaces = await loadExpedition\(expeditionConfigs\.entre\);\s+)(allPlaces = \[\.\.\.baudinPlaces, \.\.\.entrePlaces\];)", re.DOTALL)
replacement = r"\1const STATE_FILTER = 'WA';\n                const filteredBaudin = baudinPlaces.filter(p => (p.state || '').toUpperCase() === STATE_FILTER);\n                const filteredEntre = entrePlaces.filter(p => (p.state || '').toUpperCase() === STATE_FILTER);\n                allPlaces = [...filteredBaudin, ...filteredEntre];"
new_text, count = pattern.subn(replacement, text)
if count == 0:
    raise SystemExit("Failed to inject WA filter; structure changed.")
path.write_text(new_text)
PY
