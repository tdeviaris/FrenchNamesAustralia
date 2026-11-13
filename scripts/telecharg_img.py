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

Usage :
  python3 scripts/telecharg_img.py
  python3 scripts/telecharg_img.py --refresh-img Baudin255
"""

import io
import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

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
MANIFEST_FILE = DATA_DIR / "img_sources.json"

JSON_FILES = ["baudin.json", "entrecasteaux.json", "flinders.json"]

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


def wikimedia_download_url(url: str, width: int = 1600) -> str:
    """Transforme une page Commons File: en URL d'image téléchargeable.

    Les liens lisibles copiés depuis Commons peuvent ainsi rester dans la
    colonne URL IMG du tableau. Les URL directes upload.wikimedia.org et les
    autres sources sont conservées telles quelles.
    """
    try:
        parsed = urlsplit(url.strip())
    except ValueError:
        return url

    if parsed.netloc.lower() != "commons.wikimedia.org":
        return url

    prefix = "/wiki/"
    if not parsed.path.startswith(prefix):
        return url

    title = unquote(parsed.path[len(prefix):])
    if not title.lower().startswith("file:"):
        return url

    filename = title[5:].replace(" ", "_")
    encoded = quote(filename, safe="")
    return (
        "https://commons.wikimedia.org/wiki/Special:Redirect/file/"
        f"{encoded}?width={width}"
    )


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


MINIATURE_LARGEUR = 480          # largeur servie aux téléphones


def generate_miniature(jpg_path: Path) -> str:
    """Fabrique <nom>_min.avif, large de MINIATURE_LARGEUR pixels.

    L'AVIF de pleine taille garde les dimensions de l'original : un téléphone
    qui n'affiche qu'une vignette de soixante pixels téléchargeait jusqu'ici
    cinq mille pixels de large. Celui-ci est fait pour lui.
    """
    mini_jpg = jpg_path.with_name(jpg_path.stem + "_min.jpg")
    mini_avif = jpg_path.with_name(jpg_path.stem + "_min.avif")
    try:
        img = Image.open(jpg_path)
        if img.width <= MINIATURE_LARGEUR:
            return "skipped (déjà petite)"
        hauteur = round(img.height * MINIATURE_LARGEUR / img.width)
        img = img.convert("RGB").resize((MINIATURE_LARGEUR, hauteur), Image.LANCZOS)
        img.save(mini_jpg, "JPEG", quality=78, optimize=True)
    except Exception as e:
        return f"KO ({e})"

    if not AVIFENC:
        return f"OK jpeg {mini_jpg.stat().st_size // 1024} Ko (avifenc absent)"
    try:
        r = subprocess.run(
            [AVIFENC, "-q", "45", "-s", "4", "-y", "420", "--jobs", "all",
             "--ignore-exif", "--ignore-xmp", "--ignore-icc",
             str(mini_jpg), str(mini_avif)],
            capture_output=True, timeout=60)
        if r.returncode == 0:
            # Le JPEG reste : tous les navigateurs ne lisent pas l'AVIF, et la
            # page se sert du premier des deux qu'elle trouve.
            return f"OK {mini_avif.stat().st_size // 1024} Ko"
        return f"KO (avifenc exit {r.returncode})"
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


def process_entry(
    entry: dict,
    log_parts: list[str],
    refresh_codes: set[str],
    source_manifest: dict[str, str],
) -> None:
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

        mini_path = IMG_DIR / f"{code}_{suffix}_min.avif"

        manifest_key = f"{code}_{suffix}"
        recorded_source = source_manifest.get(manifest_key, "")
        source_changed = bool(
            jpg_path.exists() and recorded_source and recorded_source != url
        )
        force_refresh = (
            (suffix == "Img" and code in refresh_codes) or source_changed
        )

        if jpg_path.exists() and not force_refresh:
            # JPEG déjà présent — complète l'AVIF et la miniature s'ils manquent
            manques = []
            if AVIFENC and not avif_path.exists():
                manques.append(f"AVIF {generate_avif(jpg_path)}")
            if suffix == "Img" and not mini_path.exists():
                manques.append(f"miniature {generate_miniature(jpg_path)}")
            if manques:
                print(f"  {code} {suffix}: JPEG déjà présent, {' | '.join(manques)}")
            else:
                print(f"  {code} {suffix}: déjà présent, ignoré")
            results.append(f"{suffix} OK")
            continue

        download_url = wikimedia_download_url(url)
        action = "actualisation" if force_refresh else "téléchargement"
        print(f"  {code} {suffix}: {action} {url[:70]}...", end=" ", flush=True)

        if is_wikipedia_url(url):
            time.sleep(WIKIPEDIA_DELAY)

        raw, dl_msg = download_raw(download_url)
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

        source_manifest[manifest_key] = url

        if force_refresh:
            for derived in (
                avif_path,
                jpg_path.with_name(jpg_path.stem + "_min.jpg"),
                jpg_path.with_name(jpg_path.stem + "_min.avif"),
            ):
                derived.unlink(missing_ok=True)

        avif_msg = generate_avif(jpg_path)
        # La carte s'ouvre en grand, jamais en vignette : elle n'a pas besoin
        # de miniature. L'image de la fiche, si.
        mini_msg = generate_miniature(jpg_path) if suffix == "Img" else "sans objet"
        print(f"{jpeg_msg} | AVIF {avif_msg} | mini {mini_msg}")
        results.append(f"{suffix} {jpeg_msg} | AVIF {avif_msg} | mini {mini_msg}")

    if results:
        log_parts.append(f"{code} {' | '.join(results)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--refresh-img",
        action="append",
        default=[],
        metavar="CODE",
        help=(
            "retélécharge le portrait de ce code même si sa copie locale existe; "
            "l'option peut être répétée"
        ),
    )
    args = parser.parse_args()
    refresh_codes = set(args.refresh_img)

    try:
        with open(MANIFEST_FILE, encoding="utf-8") as f:
            source_manifest = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        source_manifest = {}

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
            process_entry(entry, log_parts, refresh_codes, source_manifest)

    with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
        json.dump(dict(sorted(source_manifest.items())), f, indent=2, ensure_ascii=False)
        f.write("\n")

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
