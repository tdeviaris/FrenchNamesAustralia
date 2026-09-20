#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Refait le logo de la RGSSA avec un texte lisible dans le pied de page.

Le logo d'origine est un JPEG de 2400 x 716. L'embleme occupe toute la
hauteur, le texte moins de la moitie : dans le pied de page, ou l'image est
plafonnee a 56 px de haut, une ligne de texte ne fait plus que 10 px. On la
devine plutot qu'on ne la lit.

L'embleme est repris tel quel, au pixel pres -- c'est une marque, on n'y
touche pas. Seul le texte est refait, dans sa police d'origine : Times New
Roman rend « The Royal Geographical Society » en 1914 px la ou l'original en
fait 1882, et la seconde ligne en 1367 contre 1354, soit moins de deux pour
cent d'ecart sur les deux. Blanc sur noir, meme taille pour les deux lignes,
comme dans l'original.

Le grossissement est borne par la mise en page, non par le gout : le pied de
page accorde au logo min(260px, 28vw) de large pour 56 px de haut
(css/nav.css). A hauteur constante, tout elargissement de l'image agrandit le
texte affiche, jusqu'a ce que la largeur bute sur ce conteneur. Le facteur
1,42 amene l'image a 249 px de large a l'ecran, sous la limite, et fait
passer la premiere ligne de 10,6 a 15 px.

Usage :
    python3 scripts/logo_rgssa.py            # ecrit img/rgssa-logo.png
    python3 scripts/logo_rgssa.py --facteur 1.6 --sortie /tmp/essai.png
"""

import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

RACINE = Path(__file__).parent.parent
ORIGINAL = RACINE / "img" / "rgssa-logo_white-on-black.jpg"
SORTIE = RACINE / "img" / "rgssa-logo.png"
POLICE = "/System/Library/Fonts/Supplemental/Times New Roman.ttf"

# Releve sur l'original, en pixels.
FIN_EMBLEME = 477          # derniere colonne de l'embleme, marge comprise
HAUTEUR = 716
X_TEXTE = 495              # ou commence le texte
MARGE_DROITE = 23
CAPITALE = 97              # hauteur du T de « The »
ECART_LIGNES = 226         # d'une ligne de base a l'autre
TAILLE_POUR_CAPITALE = 146 # corps Times donnant cette capitale
LIGNES = ("The Royal Geographical Society", "Of South Australia Inc.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--facteur", type=float, default=1.42,
                    help="grossissement du texte (1,42 remplit le pied de page)")
    ap.add_argument("--retrait", type=float, default=2,
                    help="retrait de la seconde ligne, en blancs")
    ap.add_argument("--hauteur", type=int, default=224,
                    help="hauteur du fichier produit ; le pied de page "
                         "l'affiche a 56 px, quatre fois moins")
    ap.add_argument("--sortie", default=str(SORTIE))
    args = ap.parse_args()
    k = args.facteur

    original = Image.open(ORIGINAL).convert("RGB")
    embleme = original.crop((0, 0, FIN_EMBLEME, HAUTEUR))

    police = ImageFont.truetype(POLICE, round(TAILLE_POUR_CAPITALE * k))
    retrait = round(police.getlength(" ") * args.retrait)
    largeurs = [police.getbbox(l)[2] - police.getbbox(l)[0] + (retrait if i else 0)
                for i, l in enumerate(LIGNES)]
    largeur = X_TEXTE + max(largeurs) + MARGE_DROITE

    image = Image.new("RGB", (largeur, HAUTEUR), "black")
    image.paste(embleme, (0, 0))

    # Le bloc de texte est centre sur l'embleme, dont le dessin occupe
    # y 35 a 683. L'original le posait un peu plus bas, sans raison visible.
    capitale, ecart = CAPITALE * k, ECART_LIGNES * k
    centre = (35 + 683) / 2
    base = centre - (capitale + ecart) / 2 + capitale

    # La seconde ligne est plus courte et commence plus bas, la ou le pendant
    # de l'embleme descend vers la droite : alignee sur la premiere, elle le
    # frole. Un retrait de deux blancs -- la chasse d'un « i » -- lui rend de
    # l'air sans rompre l'alignement du bloc.
    dessin = ImageDraw.Draw(image)
    for i, ligne in enumerate(LIGNES):
        dessin.text((X_TEXTE + (retrait if i else 0), base + i * ecart), ligne,
                    font=police, fill="white", anchor="ls")

    # Le texte est compose en pleine resolution puis l'ensemble est reduit :
    # la reduction lisse les lettres et noie le grain JPEG de l'embleme. Sortir
    # les 3233 px d'origine ferait 190 Ko pour une image affichee a 56 px, et
    # le transfert Vercel se compte.
    if args.hauteur and args.hauteur != HAUTEUR:
        image = image.resize((round(largeur * args.hauteur / HAUTEUR), args.hauteur),
                             Image.LANCZOS)
    Path(args.sortie).parent.mkdir(parents=True, exist_ok=True)
    image.convert("L").save(args.sortie, optimize=True)
    rapport = largeur / HAUTEUR
    print(f"{args.sortie} : {largeur} x {HAUTEUR}, rapport {rapport:.2f}")
    print(f"a 56 px de haut : {56 * rapport:.0f} px de large "
          f"(le pied de page en accorde 260)")
    print(f"hauteur d'une capitale a l'ecran : {56 * capitale / HAUTEUR:.1f} px "
          f"(contre {56 * CAPITALE / HAUTEUR:.1f} avant)")


if __name__ == "__main__":
    main()
