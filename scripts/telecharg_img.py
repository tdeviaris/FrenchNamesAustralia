#!/usr/bin/env python3
"""
telecharg_img.py

Télécharge les images depuis les champs imgUrl et mapUrl de baudin.json
et entrecasteaux.json. Les images sont stockées dans img_telecharg/ à la
racine du projet :
  - Redimensionnement si nécessaire :
      *_Img   : largeur max 3500 px, hauteur max 2200 px, qualité JPEG 80
      *_Carte : dimension max 5000 px, qualité JPEG 90
  - Preview AVIF généré automatiquement (qualité 15, speed 0) si avifenc
    est disponible.

Prérequis : pip install requests Pillow
Optionnel : brew install libavif  (pour les previews AVIF)

Usage : python3 scripts/telecharg_img.py
"""

import io
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("Erreur : module 'requests' manquant. Installez-le avec : pip install requests")

try:
    from PIL import Image
except ImportError:
    sys.exit("Erreur : module 'Pillow' manquant. Installez-le avec : pip install Pillow")

Image.MAX_IMAGE_PIXELS = None  # images légitimes très grandes

SCRIPT_DIR = Path(__file__).parent
ROOT_DIR   = SCRIPT_DIR.parent
DATA_DIR   = ROOT_DIR / "data"
IMG_DIR    = ROOT_DIR / "img_telecharg"
LOG_FILE   = SCRIPT_DIR / "telecharg_img.log"

JSON_FILES = ["baudin.json", "entrecasteaux.json"]

FIELDS = {
    "imgUrl":  "Img",
    "mapUrl":  "Carte",
}

RULES = {
    "Img":   {"max_w": 3500, "max_h": 2200, "quality": 80},
    "Carte": {"max_w": 5000, "max_h": 5000, "quality": 90},
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}

TIMEOUT          = 30
WIKIPEDIA_DELAY  = 1.5
MAX_RETRIES      = 3
AVIFENC          = shutil.which("avifenc")  # None si non installé


def is_wikipedia_url(url: str) -> bool:
    return "wikimedia.org" in url or "wikipedia.org" in url


def save_jpeg(raw: bytes, dest_path: Path, rule: dict) -> str:
    """
    Ouvre l'image depuis les bytes bruts, redimensionne si nécessaire,
    sauvegarde en JPEG avec la qualité définie.
    Retourne un message descriptif.
    """
    img = Image.open(io.BytesIO(raw))
    orig_w, orig_h = img.size

    ratio = min(rule["max_w"] / orig_w, rule["max_h"] / orig_h)
    if ratio < 1.0:
        new_w = int(orig_w * ratio)
        new_h = int(orig_h * ratio)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        resize_info = f" (redim. {orig_w}x{orig_h}→{new_w}x{new_h})"
    else:
        resize_info = ""

    if img.mode != "RGB":
        img = img.convert("RGB")

    img.save(dest_path, "JPEG", quality=rule["quality"], optimize=True)
    size_ko = dest_path.stat().st_size // 1024
    return f"OK{resize_info} {size_ko} Ko"


def generate_avif(jpg_path: Path) -> str:
    """Génère le preview AVIF à côté du JPEG. Retourne 'OK', 'skipped' ou message d'erreur."""
    if not AVIFENC:
        return "skipped (avifenc absent)"
    avif_path = jpg_path.with_suffix(".avif")
    try:
        result = subprocess.run(
            [
                AVIFENC,
                "-q", "15",
                "-s", "0",
                "-y", "420",
                "--jobs", "all",
                "--ignore-exif", "--ignore-xmp", "--ignore-icc",
                str(jpg_path), str(avif_path),
            ],
            capture_output=True,
            timeout=120,
        )
        if result.returncode == 0:
            size = avif_path.stat().st_size
            if size < 20 * 1024:  # < 20 Ko → trop dégradé, inutile
                avif_path.unlink()
                return f"skipped ({size // 1024} Ko < 20 Ko min)"
            return f"OK {size // 1024} Ko"
        return f"KO (avifenc exit {result.returncode})"
    except subprocess.TimeoutExpired:
        return "KO (timeout avifenc)"
    except Exception as e:
        return f"KO ({e})"


def download_raw(url: str) -> tuple[bytes | None, str]:
    """Télécharge l'URL et retourne (bytes, message). Gère 429 + retries."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        except requests.exceptions.Timeout:
            return None, "KO (timeout)"
        except requests.exceptions.ConnectionError as e:
            return None, f"KO (connexion: {e})"
        except requests.exceptions.RequestException as e:
            return None, f"KO ({e})"

        if resp.status_code == 429:
            wait = max(int(resp.headers.get("Retry-After", 10)), 10)
            print(f"\n    → 429 rate limit, attente {wait}s (tentative {attempt}/{MAX_RETRIES})...",
                  end=" ", flush=True)
            time.sleep(wait)
            continue

        try:
            resp.raise_for_status()
        except requests.exceptions.HTTPError:
            return None, f"KO (HTTP {resp.status_code})"

        return resp.content, "OK"

    return None, f"KO (429 après {MAX_RETRIES} tentatives)"


def process_entry(entry: dict, log_parts: list[str]) -> None:
    """Traite un enregistrement JSON : télécharge imgUrl et mapUrl si remplis."""
    code = entry.get("code", "???")
    results = []

    for field, suffix in FIELDS.items():
        url = entry.get(field, "").strip()
        if not url:
            continue

        jpg_path  = IMG_DIR / f"{code}_{suffix}.jpg"
        avif_path = IMG_DIR / f"{code}_{suffix}.avif"
        rule      = RULES[suffix]

        if jpg_path.exists():
            # JPEG déjà présent — génère l'AVIF s'il manque
            if AVIFENC and not avif_path.exists():
                avif_msg = generate_avif(jpg_path)
                print(f"  {code} {suffix}: JPEG déjà présent, AVIF généré → {avif_msg}")
            else:
                print(f"  {code} {suffix}: déjà présent, ignoré")
            results.append(f"{suffix} OK")
            continue

        print(f"  {code} {suffix}: {url[:70]}...", end=" ", flush=True)

        if is_wikipedia_url(url):
            time.sleep(WIKIPEDIA_DELAY)

        raw, dl_msg = download_raw(url)
        if raw is None:
            print(dl_msg)
            results.append(f"{suffix} {dl_msg}")
            continue

        try:
            jpeg_msg = save_jpeg(raw, jpg_path, rule)
        except Exception as e:
            print(f"KO (image: {e})")
            results.append(f"{suffix} KO (image: {e})")
            continue

        avif_msg = generate_avif(jpg_path)
        print(f"{jpeg_msg} | AVIF {avif_msg}")
        results.append(f"{suffix} {jpeg_msg} | AVIF {avif_msg}")

    if results:
        log_parts.append(f"{code} {' | '.join(results)}")


def main() -> None:
    IMG_DIR.mkdir(exist_ok=True)

    if AVIFENC:
        print(f"avifenc trouvé : {AVIFENC}")
    else:
        print("avifenc absent — previews AVIF ignorés (brew install libavif pour les activer)")

    log_parts: list[str] = []

    for json_filename in JSON_FILES:
        json_path = DATA_DIR / json_filename
        if not json_path.exists():
            print(f"Fichier non trouvé : {json_path}", file=sys.stderr)
            continue

        with open(json_path, encoding="utf-8") as f:
            entries = json.load(f)

        print(f"\n=== {json_filename} ({len(entries)} entrées) ===")

        for entry in entries:
            process_entry(entry, log_parts)

    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(log_parts) + "\n")

    total = len(log_parts)
    ok    = sum(1 for line in log_parts if "KO" not in line)
    ko    = total - ok
    print(f"\n{'─' * 50}")
    print(f"Terminé : {total} entrées traitées, {ok} sans erreur, {ko} avec erreur(s)")
    print(f"Log : {LOG_FILE}")


if __name__ == "__main__":
    main()
