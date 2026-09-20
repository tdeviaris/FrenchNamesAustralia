#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Retient les visuels choisis sur la planche de contrôle, pour le classeur.

La planche produite par visuels_flinders.py propose une image par toponyme ;
on en garde certaines. Ce script rassemble, pour chaque code retenu, l'adresse
de l'image, son auteur et sa licence -- Wikimedia demande l'attribution, et la
fiche doit donc la porter.

Il écrivait autrefois directement dans data/flinders.json. Ce n'est plus
possible : depuis septembre 2026 ce fichier est produit par l'onglet
« Flinders » du classeur Toponymes, et tout ce qui entre par un autre chemin
disparaît au premier export. Le script écrit donc dans data/visuels_flinders.json,
d'où le classeur les verse dans son onglet.

Le détour par le dépôt n'est pas une faiblesse : il laisse une trace versionnée
de chaque attribution, et il évite d'ouvrir au dépôt un accès en écriture au
classeur. Une fois les visuels dans l'onglet, Dany en change un à la main
quand elle veut, et c'est sa version qui fait foi.

L'import dans l'onglet n'est plus un geste : « Mettre à jour les JSONs » le
fait de lui-même, juste avant de lire l'onglet (voir scripts/Toponyms_update,
importeVisuels). Du côté du dépôt, il suffit donc de pousser :

  1. python3 scripts/visuels_flinders.py        -> propose, output/visuels_flinders.json
  2. python3 scripts/applique_visuels.py --codes …   -> retient, data/visuels_flinders.json
  3. commit et push
  4. classeur, menu GitHub > Mettre à jour les JSONs

Le fichier retenu s'ajoute à lui-même : un code déjà présent est remplacé, les
autres sont conservés. Pour en retirer un, employer --retirer.

Usage :
    python3 scripts/applique_visuels.py --codes Flinders001,Flinders014
    python3 scripts/applique_visuels.py --fichier codes_retenus.txt
    python3 scripts/applique_visuels.py --retirer Flinders014
    python3 scripts/applique_visuels.py --codes … --essai
"""

import argparse
import json
import re
from pathlib import Path

RACINE = Path(__file__).parent.parent
PROPOSITIONS = RACINE / "output" / "visuels_flinders.json"
RETENUS = RACINE / "data" / "visuels_flinders.json"

# Les quatre colonnes de l'onglet « Flinders » que ce fichier alimente.
COLONNES = {
    "imgUrl": "URL IMG",
    "imgCredit": "Credit image",
    "imgSource": "Source image",
    "imgSujet": "Sujet image",
    "wiki_fr": "URL WIKI FR",
    "wiki_en": "URL WIKi EN",
}


def url_propre(url):
    """Les URL de l'API traînent des paramètres de suivi : on les coupe."""
    return re.sub(r"\?utm_[^#]*", "", url or "")


def credit(prop):
    """« Auteur · Licence », tel que la fiche l'affichera."""
    morceaux = [prop.get("auteur"), prop.get("licence")]
    return " · ".join(m for m in morceaux if m)


def charge_retenus():
    if not RETENUS.exists():
        return {}
    return json.loads(RETENUS.read_text(encoding="utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--codes", help="codes séparés par des virgules")
    ap.add_argument("--fichier", help="fichier contenant les codes")
    ap.add_argument("--retirer", help="codes à retirer du fichier retenu")
    ap.add_argument("--propositions", default=str(PROPOSITIONS))
    ap.add_argument("--liens-seuls", dest="liens_seuls", action="store_true",
                    help="n'écrit que les liens Wikipédia, sans toucher à l'image")
    ap.add_argument("--essai", action="store_true", help="n'écrit rien")
    args = ap.parse_args()

    retenus = charge_retenus()

    if args.retirer:
        partis = []
        for code in re.split(r"[,\s]+", args.retirer):
            if code and retenus.pop(code, None) is not None:
                partis.append(code)
        print("retirés : %s" % (", ".join(partis) or "aucun"))
        if not args.essai:
            ecrit(retenus)
        return

    brut = args.codes or (Path(args.fichier).read_text(encoding="utf-8")
                          if args.fichier else "")
    codes = [c.strip() for c in re.split(r"[,\s]+", brut) if c.strip()]
    if not codes:
        raise SystemExit("aucun code retenu")

    props = {r["code"]: r["proposition"]
             for r in json.loads(Path(args.propositions).read_text(encoding="utf-8"))
             if r.get("proposition")}

    poses, remplaces, manquants = 0, [], []
    for code in codes:
        p = props.get(code)
        if not p:
            manquants.append(code)
            continue
        if code in retenus:
            remplaces.append(code)
        # Les quatre champs d'image forment un bloc : ils decrivent une image
        # precise, son auteur, sa page et son sujet. Sans image a poser, on
        # n'y touche pas -- ecrire le seul sujet legenderait l'image en place
        # du nom d'un portrait qui n'existe pas. « Sweers Island » portait une
        # photo de l'ile ; la proposition nommait Salomon Sweers, qui n'a pas
        # de portrait : la photo se serait retrouvee sous son nom.
        fiche = {}
        if not args.liens_seuls and p.get("url"):
            fiche = {
                "imgUrl": url_propre(p.get("url") or ""),
                "imgCredit": credit(p),
                "imgSource": url_propre(p.get("page") or p.get("wiki") or ""),
                "imgSujet": p.get("sujet") or "",
            }
        # Les liens Wikipedia du beneficiaire, quand la proposition les porte.
        # Ils valent par eux-memes : une fiche peut n'avoir qu'eux, sans
        # portrait -- Henry Waterhouse a un article, mais pas d'image.
        for champ in ("wiki_en", "wiki_fr"):
            if p.get(champ):
                fiche[champ] = p[champ]
        # Ce qui est vide n'ecrase rien : une passe de liens laisse l'image en
        # place, une passe d'image laisse les liens. Pour retirer, --retirer.
        retenus[code] = {**retenus.get(code, {}),
                         **{k: v for k, v in fiche.items() if v}}
        poses += 1
        print("%-12s %-11s %s" % (code, "liens" if args.liens_seuls else p.get("voie", ""),
                                  (p.get("sujet") or "")[:46]))

    if remplaces:
        print("\nvisuels remplacés : %s" % ", ".join(remplaces))
    if manquants:
        print("sans proposition  : %s" % ", ".join(manquants))
    if args.essai:
        print("\n(essai) %d visuels auraient été retenus, %d au total"
              % (poses, len(retenus)))
        return
    ecrit(retenus)


def ecrit(retenus):
    RETENUS.parent.mkdir(parents=True, exist_ok=True)
    RETENUS.write_text(
        json.dumps(dict(sorted(retenus.items())), ensure_ascii=False, indent=1),
        encoding="utf-8")
    print("\n%d visuels dans %s" % (len(retenus), RETENUS.relative_to(RACINE)))
    print("Reste à pousser, puis : classeur > menu GitHub > Mettre à jour les JSONs.")


if __name__ == "__main__":
    main()
