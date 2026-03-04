#!/usr/bin/env python3
"""
reduc_Img.py

Réduit les dimensions et recompresse les JPEG dans img_telecharg/ :
  - *_Img.jpg   : largeur max 3500 px, hauteur max 2200 px, qualité 80
  - *_Carte.jpg : dimension max (largeur ou hauteur) 5000 px, qualité 90

Règles :
  - Si le résultat serait plus lourd que l'original, le fichier n'est pas modifié
    (sauf si un redimensionnement est nécessaire, auquel cas on enregistre quand même).
  - Les très grandes images (dépassant la limite de sécurité de Pillow) sont gérées.

Un fichier log (scripts/reduc_Img.log) liste les réductions effectuées.

Usage : python3 scripts/reduc_Img.py
"""

import io
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    sys.exit("Erreur : module 'Pillow' manquant. Installez-le avec : pip install Pillow")

# Désactive la limite anti-décompression bomb (images légitimes très grandes)
Image.MAX_IMAGE_PIXELS = None

SCRIPT_DIR = Path(__file__).parent
ROOT_DIR   = SCRIPT_DIR.parent
IMG_DIR    = ROOT_DIR / "img_telecharg"
LOG_FILE   = SCRIPT_DIR / "reduc_Img.log"

RULES = {
    "_Img.jpg":   {"max_w": 3500, "max_h": 2200, "quality": 80},
    "_Carte.jpg": {"max_w": 5000, "max_h": 5000, "quality": 90},
}


def human_size(n_bytes: int) -> str:
    if n_bytes >= 1_048_576:
        return f"{n_bytes / 1_048_576:.1f} Mo"
    return f"{n_bytes / 1024:.0f} Ko"


def get_rule(filename: str) -> dict | None:
    for suffix, rule in RULES.items():
        if filename.endswith(suffix):
            return rule
    return None


def process_image(path: Path, rule: dict, log_lines: list[str]) -> None:
    orig_size = path.stat().st_size

    with Image.open(path) as img:
        orig_w, orig_h = img.size

        ratio = min(rule["max_w"] / orig_w, rule["max_h"] / orig_h)
        needs_resize = ratio < 1.0

        if needs_resize:
            new_w = int(orig_w * ratio)
            new_h = int(orig_h * ratio)
            img_out = img.resize((new_w, new_h), Image.LANCZOS)
        else:
            new_w, new_h = orig_w, orig_h
            img_out = img.copy()

        if img_out.mode != "RGB":
            img_out = img_out.convert("RGB")

        # Encode en mémoire pour comparer les tailles avant d'écrire
        buf = io.BytesIO()
        img_out.save(buf, "JPEG", quality=rule["quality"], optimize=True)

    new_size = buf.tell()

    # Si pas de redimensionnement et que la recompression grossit le fichier → ignorer
    if not needs_resize and new_size >= orig_size:
        print(f"  {path.name}: ignorée (recompression +{new_size - orig_size:,} octets)")
        log_lines.append(f"{path.name} | ignorée (recompression grossirait le fichier) | {orig_w}x{orig_h} | {human_size(orig_size)}")
        return

    path.write_bytes(buf.getvalue())
    gain = orig_size - new_size

    if needs_resize:
        dim_info = f"{orig_w}x{orig_h} → {new_w}x{new_h}"
        action = "redimensionnée + recompressée"
    else:
        dim_info = f"{orig_w}x{orig_h} (inchangé)"
        action = "recompressée"

    size_info = f"{human_size(orig_size)} → {human_size(new_size)} (-{gain:,} octets)"

    print(f"  {path.name}: {action} | {dim_info} | {size_info}")
    log_lines.append(f"{path.name} | {action} | {dim_info} | {size_info}")


def main() -> None:
    if not IMG_DIR.exists():
        sys.exit(f"Répertoire introuvable : {IMG_DIR}")

    jpg_files = sorted(IMG_DIR.glob("*.jpg"))
    if not jpg_files:
        print("Aucun fichier JPEG trouvé dans img_telecharg/")
        return

    log_lines: list[str] = []
    processed = skipped = errors = 0

    print(f"Traitement de {len(jpg_files)} fichiers dans {IMG_DIR.name}/\n")

    for path in jpg_files:
        rule = get_rule(path.name)
        if rule is None:
            skipped += 1
            continue

        try:
            process_image(path, rule, log_lines)
            processed += 1
        except Exception as e:
            errors += 1
            print(f"  {path.name}: ERREUR — {e}")
            log_lines.append(f"{path.name} | ERREUR | {e}")

    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines) + "\n")

    print(f"\n{'─' * 60}")
    print(f"Terminé : {processed} fichiers traités, {skipped} ignorés, {errors} erreur(s)")
    print(f"Log : {LOG_FILE}")


if __name__ == "__main__":
    main()
