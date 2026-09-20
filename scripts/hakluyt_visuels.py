#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Les visuels et les liens Wikipedia, d'apres l'article de Dany Breelle.

visuels_flinders.py devine le beneficiaire d'un toponyme en interrogeant
Wikipedia. C'est une conjecture, et elle se trompe : « Spencer Gulf » lui a
rendu le quatrieme comte Spencer quand Flinders honorait le deuxieme, et
« Draper Island » un general de l'armee de terre quand il s'agissait du
quartier-maitre mort de dysenterie.

L'article « Matthew Flinders's Australian Toponymy and its British
Connections » (Journal of the Hakluyt Society, 2013) tranche ces questions :
son auteure a depouille le Voyage to Terra Australis, le Private Journal et
les roles d'equipage. Ce script part donc du nom que l'article donne, et ne
demande plus a Wikipedia que ce qu'il sait faire : trouver l'article de cette
personne, son portrait et ses versions linguistiques.

Le fichier data/attributions_hakluyt.json porte ces attributions, une par
code, avec la page de l'article qui l'etablit. Il se lit et se corrige a la
main : c'est une source, pas un resultat.

Usage :
    python3 scripts/hakluyt_visuels.py               # tout
    python3 scripts/hakluyt_visuels.py --codes Flinders127,Flinders018
"""

import argparse
import json
import re
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import visuels_flinders as V

RACINE = Path(__file__).parent.parent
ATTRIBUTIONS = RACINE / "data" / "attributions_hakluyt.json"
SORTIE_JSON = RACINE / "output" / "visuels_hakluyt.json"
SORTIE_HTML = RACINE / "rapports" / "visuels_hakluyt.html"


def liens_langues(titre):
    """L'adresse de l'article anglais et celle de son homologue francais."""
    d = V.api("https://en.wikipedia.org/w/api.php", prop="langlinks",
              titles=titre, redirects=1, lllang="fr", llprop="url", lllimit=10)
    en = "https://en.wikipedia.org/wiki/" + urllib.parse.quote(titre.replace(" ", "_"))
    for page in ((d.get("query") or {}).get("pages") or {}).values():
        for l in page.get("langlinks") or []:
            return en, l.get("url") or ""
    return en, ""


def homme_du_temps(page):
    """L'article est-il celui d'un contemporain de Flinders ? La plupart des
    hommes que l'article nomme -- un quartier-maitre, un matelot, un medecin
    de famille -- n'ont pas d'article ; Wikipedia rend alors un homonyme du
    XXe siecle, et « John Draper » devient un pirate informatique, « George
    Nicol » un batteur des Beatles. Une categorie de naissance anterieure a
    1800, ou de deces anterieur a 1880, separe les deux cas."""
    cats = " ".join(page.get("categories") or []).lower()
    nes = [int(a) for a in re.findall(r"\b(1[5-9]\d\d)\s+births\b", cats)]
    morts = [int(a) for a in re.findall(r"\b(1[5-9]\d\d)\s+deaths\b", cats)]
    if nes:
        return min(nes) <= 1800
    return bool(morts) and min(morts) <= 1880


def acceptable(page, typ):
    """Un lieu, un navire ou une institution n'ont pas de date de naissance :
    on se contente d'exiger qu'ils portent le nom cherche. Pour une personne,
    l'epoque tranche."""
    if not page:
        return False
    return homme_du_temps(page) if typ == "personne" else True


def homonymie(page):
    """Une page d'homonymie n'est l'article de personne : « Joseph Cotton »
    renvoie a une liste, pas au directeur de la Compagnie des Indes."""
    cats = " ".join(page.get("categories") or []).lower()
    return "disambiguation" in cats


def article_du_sujet(sujet, typ="personne"):
    """L'article du beneficiaire. Le titre exact d'abord -- l'article de Dany
    ecrit le plus souvent le nom tel que Wikipedia le porte -- puis la
    recherche, qui rattrape les titres a rallonge (« Richard Bickerton » ->
    « Sir Richard Bickerton, 2nd Baronet »). Le patronyme doit figurer dans le
    titre retenu, sinon la recherche derive vers un article voisin.

    Un article sans portrait est retenu quand meme : il porte les deux liens
    Wikipedia, qui valent par eux-memes."""
    page = V.page_wikipedia(sujet, avec_categories=True)
    if page and not homonymie(page) and acceptable(page, typ):
        if page.get("fichier"):
            return page
    else:
        page = None

    # Le repli ne doit pas changer d'homme. « Richard Bickerton » a le droit
    # de devenir « Sir Richard Bickerton, 2nd Baronet », qui le contient ;
    # « Samuel Flinders » n'a pas le droit de devenir « Matthew Flinders »,
    # ni « John Aken » « Joseph Van Aken ». On exige donc le nom entier, pas
    # le seul patronyme -- c'est par le prenom que la derive se fait.
    attendu = sujet.split(",")[0].split("(")[0].strip().lower()
    for titre in V.recherche_wikipedia(sujet, 6):
        if attendu not in titre.lower():
            continue
        p = V.page_wikipedia(titre, avec_categories=True)
        if not p or homonymie(p) or not acceptable(p, typ):
            continue
        if p.get("fichier") and not V.REJETS_FICHIER.search(p["fichier"]):
            return p
        page = page or p           # sans portrait : on garde pour les liens
    return page


def cherche(code, att):
    """Ce que l'on peut poser sur la fiche : un portrait, deux liens."""
    page = article_du_sujet(att["sujet"], att["type"])
    if not page:
        return None
    en, fr = liens_langues(page["titre"])
    prop = {"voie": "hakluyt", "sujet": page["titre"],
            "motif": f"{att['note']} — {att['source']}",
            "distance_km": None, "fichier": page.get("fichier"),
            "wiki": en, "wiki_en": en, "wiki_fr": fr,
            "type": att["type"]}
    if page.get("fichier"):
        prop.update({k: v for k, v in V.commons_infos(page["fichier"]).items() if v})
    return prop


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--codes")
    args = ap.parse_args()

    att = json.loads(ATTRIBUTIONS.read_text(encoding="utf-8"))
    fiches = json.loads(V.FICHIER.read_text(encoding="utf-8"))
    par_code = {f["code"]: f for f in fiches}
    codes = [c for c in att if not args.codes or c in set(args.codes.split(","))]

    resultats, avec_image, avec_fr = [], 0, 0
    for i, code in enumerate(sorted(codes), 1):
        a = att[code]
        print(f"[{i}/{len(codes)}] {code} {a['toponyme']} -> {a['sujet']}")
        p = cherche(code, a)
        if p:
            if p.get("vignette") or p.get("url"):
                avec_image += 1
            if p.get("wiki_fr"):
                avec_fr += 1
            print(f"   → {p['sujet']}"
                  + ("  [portrait]" if p.get("fichier") else "  [sans image]")
                  + ("  [fr]" if p.get("wiki_fr") else ""))
        else:
            print("   → aucun article")
        resultats.append({"fiche": par_code[code], "proposition": p})

    SORTIE_JSON.parent.mkdir(parents=True, exist_ok=True)
    SORTIE_JSON.write_text(json.dumps(
        [{"code": r["fiche"]["code"], "nom": r["fiche"].get("ausEName"),
          "categorie": r["fiche"].get("categorie"), "classe": r["fiche"].get("classe"),
          "proposition": r["proposition"]} for r in resultats],
        ensure_ascii=False, indent=1), encoding="utf-8")
    V.ORDRE_VOIE.setdefault("hakluyt", -1)
    V.planche(resultats, SORTIE_HTML,
              f"{len(codes)} toponymes dont l’article de Dany Bréelle nomme le "
              f"bénéficiaire : {avec_image} portraits trouvés, {avec_fr} articles "
              "français. Cochez « à retenir », puis copiez la liste des codes.")
    print(f"\n{avec_image}/{len(codes)} portraits, {avec_fr} liens français — "
          f"{SORTIE_HTML.relative_to(RACINE)}")


if __name__ == "__main__":
    main()
