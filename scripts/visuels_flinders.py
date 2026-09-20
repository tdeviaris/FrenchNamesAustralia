#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cherche un visuel pour chaque toponyme de Flinders.

Les fiches de Baudin et de d'Entrecasteaux montrent d'abord CE QUE LE NOM
DESIGNE : l'homme qu'il honore, le navire, le lieu anglais dont il est
l'echo. Une photographie du cap australien ne vient qu'a defaut, quand le
nom ne renvoie a personne. Ce script suit la meme regle.

Il lit la famille du toponyme dans les champs `categorie` et `classe`, en
tire l'eponyme -- le nom propre debarrasse de son generique --, puis cherche
son portrait ou son illustration :

  * un officier, un matelot, un proche      -> son portrait
  * un lieu du Lincolnshire ou d'Angleterre -> une vue de ce lieu, verifiee
                                               dans les iles Britanniques
  * une plante, un animal                   -> l'espece
  * un navire, un navigateur anterieur      -> le batiment ou l'homme

Faute d'eponyme -- les noms descriptifs, Smooth Island, Craggy Islands --,
on retombe sur le lieu lui-meme : article Wikipedia verifie par ses
coordonnees, puis photo geolocalisee sur Commons.

Rien n'est ecrit dans les donnees : le script produit un JSON de propositions
et une planche de controle, ou l'on coche ce qu'on retient.

Usage :
    python3 scripts/visuels_flinders.py            # lot pilote de 30 fiches
    python3 scripts/visuels_flinders.py --tout     # les 351
    python3 scripts/visuels_flinders.py --codes Flinders001,Flinders009
"""

import argparse
import html
import json
import math
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

RACINE = Path(__file__).parent.parent
FICHIER = RACINE / "data" / "flinders.json"
SORTIE_JSON = RACINE / "output" / "visuels_flinders.json"
SORTIE_HTML = RACINE / "rapports" / "visuels_flinders.html"

AGENT = "FrenchNamesAustralia/1.0 (https://frenchnamesaustralia.com ; tdeviaris@melcion.com)"
PAUSE = 0.12

RAYON_ARTICLE = 10.0                  # au-dela, l'article parle d'un homonyme
RAYONS_COMMONS = (1500, 5000, 10000)
RAYON_SANS_NOM = 1.5

# Vues prises de l'espace, cartes de situation, blasons : rien qui illustre.
REJETS_FICHIER = re.compile(
    r"(?:^|[ _-])(?:ISS\d+|STS[-_]?\d+|Expedition\s?\d+)[ _-]|"
    r"View of Earth|View from the ISS|Earth from space|"
    r"locator|location map|\bmap of\b|coat of arms|"
    r"\bflag\b|\blogo\b|\bseal\b|blank\.|\.svg$",
    re.I)

# Le generique d'un toponyme : ce qui reste est l'eponyme.
GENERIQUES = {
    "cape", "point", "mount", "mt", "port", "island", "islands", "isle",
    "isles", "bay", "river", "rock", "rocks", "head", "hill", "hills",
    "range", "passage", "reach", "harbour", "harbor", "inlet", "shoal",
    "shoals", "reef", "reefs", "group", "peak", "peaks", "bluff", "sound",
    "strait", "straits", "creek", "lagoon", "cove", "beach", "spit", "bank",
    "banks", "channel", "arm", "basin", "gulf", "lake", "the", "of", "and",
    "north", "south", "east", "west", "upper", "lower", "great", "little",
    "new", "old",
}

# Familles d'eponymes, lues dans `categorie` et `classe`.
CAT_PERSONNE = {"High officer, personality", "Ship's company",
                "Family/friends/acquaintances", "Political figure, important personality"}
CAT_LIEU_GB = {"British place"}
CAT_NATURE = {"Natural history name animal/plant"}
CAT_NAVIGATEUR = {"Previous navigator/expedition"}
CLASSE_PERSONNE = {"Royal_Navy", "Investigator", "Nobility"}
CLASSE_GB = {"Lincolnshire"}
# Ces classes disent un nom descriptif : la forme, la position, une analogie.
CLASSE_DESCRIPTIVE = {"forms", "position", "analogy", "surveying"}

# Les tournures par lesquelles Flinders dit d'ou vient un nom.
MOTIFS_PERSONNE = [
    r"in compliment to (?:my friend |my |the )?([A-Z][^,.;()]{3,60})",
    r"named (?:it |them )?(?:after|for) (?:the late |my friend |my )?([A-Z][^,.;()]{3,60})",
    r"in honou?r of (?:the late |my friend |my )?([A-Z][^,.;()]{3,60})",
    r"after (?:the late |my friend )([A-Z][a-z]+ [A-Z][^,.;()]{2,50})",
]
GRADES = re.compile(
    r"^(?:the late |my friend |my |Captain |Capt\.? |Admiral |Rear.?Admiral |Vice.?Admiral "
    r"|Sir |Lord |Lady |Mr\.? |Mrs\.? |Dr\.? |Lieutenant |Lieut\.? |Colonel |General "
    r"|His Excellency |Governor |Earl (?:of )?|Viscount |Baron )+", re.I)

# La Grande-Bretagne, pour verifier qu'un lieu anglais est bien anglais.
BOITE_GB = (49.5, -11.0, 61.0, 2.2)


def appel(url, essais=3):
    """Wikipedia laisse tomber une requete de temps a autre. Sans reprise, la
    coupure d'une seule remonte jusqu'en haut et emporte une heure de travail
    -- le fichier n'etant ecrit qu'a la fin. Trois tentatives, en patientant
    un peu plus a chaque fois."""
    req = urllib.request.Request(url, headers={"User-Agent": AGENT})
    for essai in range(1, essais + 1):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            if essai == essais:
                raise
            print(f"   (reprise {essai}/{essais - 1} apres {type(e).__name__})")
            time.sleep(2 * essai)


def api(base, **params):
    params.setdefault("format", "json")
    params.setdefault("action", "query")
    time.sleep(PAUSE)
    return appel(base + "?" + urllib.parse.urlencode(params))


def distance_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def sans_balises(t):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", t or "")).strip()


# --- Wikipedia et Commons --------------------------------------------------

def page_wikipedia(titre, avec_categories=False):
    props = "pageimages|coordinates" + ("|categories" if avec_categories else "")
    d = api("https://en.wikipedia.org/w/api.php", prop=props, titles=titre,
            redirects=1, pithumbsize=800, piprop="thumbnail|name",
            cllimit=100 if avec_categories else None)
    for pid, page in ((d.get("query") or {}).get("pages") or {}).items():
        if pid == "-1" or "missing" in page:
            return None
        c = (page.get("coordinates") or [{}])[0]
        return {"titre": page.get("title"),
                "vignette": (page.get("thumbnail") or {}).get("source"),
                "fichier": page.get("pageimage"),
                "lat": c.get("lat"), "lon": c.get("lon"),
                "categories": [x.get("title", "") for x in page.get("categories") or []]}
    return None


def recherche_wikipedia(requete, limite=6):
    d = api("https://en.wikipedia.org/w/api.php", list="search",
            srsearch=requete, srlimit=limite, srnamespace=0)
    return [r.get("title", "") for r in (d.get("query") or {}).get("search") or []]


def commons_geosearch(lat, lon, rayon):
    d = api("https://commons.wikimedia.org/w/api.php", list="geosearch",
            gscoord=f"{lat}|{lon}", gsradius=rayon, gslimit=30, gsnamespace=6)
    return (d.get("query") or {}).get("geosearch") or []


def commons_recherche(requete, limite=10):
    d = api("https://commons.wikimedia.org/w/api.php", list="search",
            srsearch=requete, srnamespace=6, srlimit=limite)
    return [r.get("title", "") for r in (d.get("query") or {}).get("search") or []]


def commons_infos(nom_fichier):
    if not nom_fichier:
        return {}
    titre = nom_fichier if nom_fichier.startswith("File:") else "File:" + nom_fichier
    d = api("https://commons.wikimedia.org/w/api.php", prop="imageinfo",
            titles=titre, iiprop="url|extmetadata|size", iiurlwidth=800)
    for page in ((d.get("query") or {}).get("pages") or {}).values():
        info = (page.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata") or {}
        return {"url": info.get("url"), "vignette": info.get("thumburl"),
                "page": info.get("descriptionurl"),
                "auteur": sans_balises((meta.get("Artist") or {}).get("value")),
                "licence": sans_balises((meta.get("LicenseShortName") or {}).get("value")),
                "credit": sans_balises((meta.get("Credit") or {}).get("value"))}
    return {}


# --- L'eponyme -------------------------------------------------------------

def eponyme(fiche):
    """Le nom propre que porte le toponyme, debarrasse de son generique."""
    nom = fiche.get("ausEName") or fiche.get("frenchName") or ""
    nom = re.sub(r"[()]", " ", nom)
    mots = [m for m in re.findall(r"[A-Za-z']+", nom) if m.lower() not in GENERIQUES]
    # « Althorpe Isles » -> Althorpe ; « Thistle Cove » -> Thistle
    mots = [m[:-2] if m.lower().endswith("'s") else m for m in mots]
    return " ".join(mots).strip()


def nom_complet(fiche):
    """Le nom entier de la personne, quand le texte de Flinders le donne."""
    texte = fiche.get("characteristic") or ""
    for motif in MOTIFS_PERSONNE:
        m = re.search(motif, texte)
        if not m:
            continue
        nom = GRADES.sub("", m.group(1)).strip(" ,;'\"")
        nom = re.sub(r"\s+(?:of|in|who|whose|which|then|late|esq).*$", "", nom, flags=re.I)
        nom = nom.strip(" ,;")
        if len(nom.split()) >= 2:
            return nom
    return None


def famille(fiche):
    cat, cls = fiche.get("categorie") or "", fiche.get("classe") or ""
    if cls in CLASSE_DESCRIPTIVE and cat not in CAT_PERSONNE:
        return "descriptif"
    if cat in CAT_PERSONNE or cls in CLASSE_PERSONNE:
        return "personne"
    if cat in CAT_LIEU_GB or cls in CLASSE_GB:
        return "lieu_gb"
    if cat in CAT_NATURE:
        return "nature"
    if cat in CAT_NAVIGATEUR:
        return "navigateur"
    return "descriptif"


def annee_naissance(page):
    """L'annee de naissance que portent les categories de l'article."""
    cats = " ".join(page.get("categories") or []).lower()
    annees = [int(a) for a in re.findall(r"\b(1[5-9]\d\d)\s+births\b", cats)]
    return min(annees) if annees else None


def annee_mort(page):
    cats = " ".join(page.get("categories") or []).lower()
    annees = [int(a) for a in re.findall(r"\b(1[5-9]\d\d)\s+deaths\b", cats)]
    return max(annees) if annees else None


def annee_du_toponyme(fiche):
    m = re.match(r"(\d{4})", str(fiche.get("date") or ""))
    return int(m.group(1)) if m else 1802


def rang_vivant(page, annee):
    """Classe un homonyme par sa vraisemblance : on honore un vivant, ou un
    mort de fraiche date -- jamais un homme du siecle suivant. Le premier
    rang va a celui dont la vie recouvre l'annee du bapteme."""
    ne, mort = annee_naissance(page), annee_mort(page)
    if ne is not None and ne > annee - 15:          # trop jeune, ou pas encore ne
        return (3, abs((ne or annee) - annee))
    if ne is not None and (mort is None or mort >= annee):
        return (0, annee - ne)                      # vivant : le plus age d'abord
    if mort is not None and mort < annee:
        return (1, annee - mort)                    # mort peu avant : plausible
    return (2, 0)


def contemporain_plausible(page, annee):
    """Un enfant de deux ans ne recoit pas l'honneur d'un cap. On ecarte celui
    que rang_vivant met au dernier rang : ne trop tard, ou pas encore ne. Le
    tri suffisait tant qu'il y avait plusieurs homonymes ; quand il n'en reste
    qu'un, le tri le retient quand meme -- d'ou ce filtre."""
    return rang_vivant(page, annee)[0] < 3


def est_personne(page, contemporain=True, avant=1800):
    """Un article de personne n'a pas de coordonnees et porte une categorie de
    naissance ou de deces. Quand le nom vient du seul toponyme, sans que le
    texte de Flinders l'ait confirme, on exige en plus un contemporain : sinon
    « Clinton » ou « Pearson » ramenent n'importe quel homonyme du XXe siecle."""
    if page.get("lat") is not None:
        return False
    cats = " ".join(page.get("categories") or []).lower()
    if not ("births" in cats or "deaths" in cats or "people" in cats):
        return False
    if not contemporain:
        return True
    annees = [int(a) for a in re.findall(r"\b(1[5-9]\d\d)\s+births\b", cats)]
    if annees:
        return min(annees) <= avant
    # Sans annee de naissance, un deces anterieur a 1850 suffit a rassurer.
    morts = [int(a) for a in re.findall(r"\b(1[5-9]\d\d)\s+deaths\b", cats)]
    return bool(morts) and min(morts) < 1850


def dans_la_boite(page, boite):
    if page.get("lat") is None:
        return False
    s, o, n, e = boite
    return s <= page["lat"] <= n and o <= page["lon"] <= e


# --- Les passes ------------------------------------------------------------

def extrait_wikipedia(titre):
    """Le texte de l'article, en clair."""
    d = api("https://en.wikipedia.org/w/api.php", prop="extracts",
            titles=titre, explaintext=1, redirects=1)
    for page in ((d.get("query") or {}).get("pages") or {}).values():
        return page.get("extract") or ""
    return ""


def preuve_flinders(texte):
    """La phrase ou l'article nomme Flinders : c'est elle qui atteste le lien,
    et qui dit souvent lequel -- compagnon de bord, protecteur, parent."""
    for phrase in re.split(r"(?<=[.!?])\s+", texte):
        if re.search(r"\bFlinders\b", phrase):
            return re.sub(r"\s+", " ", phrase).strip()[:300]
    return None


# Les mots qui font d'une mention une vraie attache : le navire, le voyage,
# le fait d'avoir donne son nom.
ATTACHES = re.compile(
    r"Investigator|Norfolk|Tom Thumb|named (?:it |them )?(?:after|in|for)|"
    r"in compliment|sailed with|accompanied|voyage|circumnavigat|midshipman|"
    r"Terra Australis|New Holland", re.I)


# L'article du lieu australien dit presque toujours qui l'a nomme, et
# comment : « The gulf was named Spencer's Gulph by Flinders on 20 March 1802,
# after George John Spencer, the 2nd Earl Spencer. » On y prend le nom entier.
APRES = re.compile(
    r"\b(?:after|in honou?r of|in compliment to)\s+"
    r"(.{3,90}?)(?:\s+by\s|\s+on\s+\d|\s+in\s+\d{4}|[.;]|$)", re.I)
PAS_UN_NOM = re.compile(
    r"\b(?:the (?:ship|vessel|town|village|island|colony|bay|cape|port)|his |her |their "
    r"|a nearby|this |it was)\b", re.I)
ARTICLE_EN_TETE = re.compile(r"^(?:the|his|her|its)\s+", re.I)
TITRE = re.compile(r"\b(?:Earl|Duke|Lord|Baron|Viscount|Marquess|Sir|Admiral|Captain)\b", re.I)


def nom_par_wikipedia(fiche):
    """Ce que l'article du lieu dit de son propre nom.

    C'est la verification que l'on ferait a la main en cherchant « X Flinders » :
    la reponse donne le prenom et le lien. Wikipedia la porte le plus souvent
    dans l'article du cap ou de l'ile, non dans celui de l'homme. On exige que
    la phrase nomme Flinders : sans quoi c'est Cook qui a baptise le lieu, et
    l'eponyme n'est pas le sien.
    """
    nom = fiche.get("ausEName") or fiche.get("frenchName")
    if not nom:
        return None
    # L'article doit etre celui du toponyme, non celui du voisin : sans cette
    # verification, « Grindal Island » attrape la phrase de « Spencer Gulf ».
    propres = mots_du_nom(fiche)
    for requete in (nom, f"{nom} Matthew Flinders"):
        for titre in recherche_wikipedia(requete, 4):
            bas = titre.lower()
            if propres and not any(m in bas for m in propres):
                continue
            texte = extrait_wikipedia(titre)
            if "Flinders" not in texte:
                continue
            for phrase in re.split(r"(?<=[.!?])\s+", texte):
                if "named" not in phrase.lower() or not re.search(r"\bFlinders\b", phrase):
                    continue
                m = APRES.search(phrase)
                if not m:
                    continue
                cible = ARTICLE_EN_TETE.sub("", re.sub(r"\s+", " ", m.group(1)).strip(" ,;'\""))
                if PAS_UN_NOM.search(cible) or len(cible) > 80 or len(cible) < 4:
                    continue
                # « after Yorke » ne nomme personne : il faut un prenom, ou un
                # titre qui designe un homme precis.
                if len(cible.split()) < 2 and not TITRE.search(cible):
                    continue
                # Le nom doit avoir affaire au toponyme, sinon on a saute
                # d'un article a l'autre.
                if propres and not any(m in cible.lower() for m in propres):
                    continue
                return cible, titre, re.sub(r"\s+", " ", phrase).strip()[:300]
    return None


def par_nom_atteste(fiche):
    """Le portrait de celui que l'article du lieu designe nommement."""
    trouve = nom_par_wikipedia(fiche)
    if not trouve:
        return None
    nom, source, phrase = trouve
    # « George John Spencer, the 2nd Earl Spencer » ou « Earl of Hardwicke » :
    # le patronyme est le dernier mot, dans les deux cas.
    patronyme = re.sub(r"[^A-Za-z]", "", nom.split()[-1])
    candidats = []
    for requete in dict.fromkeys([nom, nom.split(",")[0], nom.split(",")[-1].strip()]):
        for titre in recherche_wikipedia(requete, 5):
            if patronyme and patronyme.lower() not in titre.lower():
                continue
            page = page_wikipedia(titre, avec_categories=True)
            if not page or not page.get("fichier") or REJETS_FICHIER.search(page["fichier"]):
                continue
            if not est_personne(page, contemporain=False):
                continue
            if not contemporain_plausible(page, annee_du_toponyme(fiche)):
                continue
            candidats.append(page)
        if candidats:
            break
    if not candidats:
        return None
    # Une lignee porte le meme titre sur cinq generations : Flinders honorait
    # celui qui vivait de son temps, donc le plus ancien des homonymes.
    page = min(candidats, key=lambda p: rang_vivant(p, annee_du_toponyme(fiche)))
    ne = annee_naissance(page)
    return {"voie": "personne", "sujet": page["titre"],
            "motif": f"« {page['titre']} »" + (f", né en {ne}" if ne else "")
                     + f" — d’après l’article « {source} »",
            "preuve": phrase, "distance_km": None, "fichier": page["fichier"],
            "wiki": f"https://en.wikipedia.org/wiki/{urllib.parse.quote(page['titre'])}"}


def par_personne_liee(fiche):
    """Cherche « <nom> Matthew Flinders » et ne retient l'article que s'il
    nomme Flinders : c'est la verification que l'on ferait a la main."""
    complet, court = nom_complet(fiche), eponyme(fiche)
    if not (complet or court):
        return None
    patronyme = (complet or court).split()[-1]
    vus, candidats = set(), []
    for requete in filter(None, [f"{complet} Matthew Flinders" if complet else None,
                                 f"{court} Matthew Flinders"]):
        for titre in recherche_wikipedia(requete, 8):
            if titre in vus or patronyme.lower() not in titre.lower():
                continue
            vus.add(titre)
            page = page_wikipedia(titre, avec_categories=True)
            if not page or not page.get("fichier") or REJETS_FICHIER.search(page["fichier"]):
                continue
            if not est_personne(page):
                continue
            if not contemporain_plausible(page, annee_du_toponyme(fiche)):
                continue
            preuve = preuve_flinders(extrait_wikipedia(titre))
            if not preuve:
                continue
            candidats.append((page, preuve, bool(ATTACHES.search(preuve))))
    if not candidats:
        return None
    # Une mention qui dit le lien vaut mieux qu'une mention de passage ; a
    # egalite, le plus ancien des homonymes.
    page, preuve, _ = sorted(
        candidats,
        key=lambda c: (not c[2], rang_vivant(c[0], annee_du_toponyme(fiche))))[0]
    ne = annee_naissance(page)
    return {"voie": "personne", "sujet": page["titre"],
            "motif": f"« {page['titre']} »" + (f", né en {ne}" if ne else "")
                     + " — l’article nomme Flinders",
            "preuve": preuve, "distance_km": None, "fichier": page["fichier"],
            "wiki": f"https://en.wikipedia.org/wiki/{urllib.parse.quote(page['titre'])}"}


def par_personne(fiche):
    """Le portrait de celui que le nom honore."""
    complet = nom_complet(fiche)
    court = eponyme(fiche)
    requetes = []
    if complet:
        requetes.append((complet, f"nommé d’après {complet}"))
    if court:
        indices = "Royal Navy" if (fiche.get("classe") in CLASSE_PERSONNE or
                                   fiche.get("categorie") in CAT_PERSONNE) else ""
        requetes.append((f"{court} {indices}".strip(), f"éponyme « {court} »"))
    patronyme = (complet or court).split()[-1] if (complet or court) else None
    for requete, motif in requetes:
        candidats = []
        for titre in recherche_wikipedia(requete):
            if patronyme and patronyme.lower() not in titre.lower():
                continue
            page = page_wikipedia(titre, avec_categories=True)
            if not page or not page.get("fichier") or REJETS_FICHIER.search(page["fichier"]):
                continue
            if not est_personne(page, contemporain=(requete != complet)):
                continue
            if not contemporain_plausible(page, annee_du_toponyme(fiche)):
                continue
            candidats.append(page)
        if not candidats:
            continue
        # Le plus ancien des homonymes : « Spencer » designe le deuxieme comte,
        # contemporain de Flinders, non le quatrieme.
        page = min(candidats, key=lambda p: rang_vivant(p, annee_du_toponyme(fiche)))
        ne = annee_naissance(page)
        return {"voie": "personne", "sujet": page["titre"],
                "motif": f"{motif} — article « {page['titre']} »"
                         + (f", né en {ne}" if ne else ""),
                "distance_km": None, "fichier": page["fichier"],
                "wiki": f"https://en.wikipedia.org/wiki/{urllib.parse.quote(page['titre'])}"}
    return None


def par_lieu_gb(fiche):
    """Le lieu anglais dont le toponyme est l'echo — souvent du Lincolnshire,
    d'ou Flinders venait."""
    court = eponyme(fiche)
    if not court:
        return None
    for suffixe in ("Lincolnshire", "England", "") if fiche.get("classe") == "Lincolnshire" \
            else ("England", "Lincolnshire", ""):
        for titre in recherche_wikipedia(f"{court} {suffixe}".strip(), 5):
            if court.split()[0].lower() not in titre.lower():
                continue
            page = page_wikipedia(titre)
            if not page or not page.get("fichier") or REJETS_FICHIER.search(page["fichier"]):
                continue
            if not dans_la_boite(page, BOITE_GB):
                continue
            return {"voie": "lieu_gb", "sujet": page["titre"],
                    "motif": f"lieu anglais homonyme — « {page['titre']} »",
                    "distance_km": None, "fichier": page["fichier"],
                    "wiki": f"https://en.wikipedia.org/wiki/{urllib.parse.quote(page['titre'])}"}
    return None


def par_sujet(fiche, requetes, voie, libelle):
    """Passe generique : une espece, un navire, un navigateur."""
    court = eponyme(fiche)
    for requete in requetes:
        for titre in recherche_wikipedia(requete, 5):
            if court and court.split()[0].lower() not in titre.lower():
                continue
            page = page_wikipedia(titre)
            if not page or not page.get("fichier") or REJETS_FICHIER.search(page["fichier"]):
                continue
            # Un article australien geolocalise, c'est le cap lui-meme : on ne
            # veut pas de lui dans cette passe.
            if page.get("lat") is not None and fiche.get("lat") is not None:
                if distance_km(fiche["lat"], fiche["lon"], page["lat"], page["lon"]) < 50:
                    continue
            return {"voie": voie, "sujet": page["titre"],
                    "motif": f"{libelle} — « {page['titre']} »",
                    "distance_km": None, "fichier": page["fichier"],
                    "wiki": f"https://en.wikipedia.org/wiki/{urllib.parse.quote(page['titre'])}"}
    return None


def par_nature(fiche):
    court = eponyme(fiche)
    if not court:
        return None
    return par_sujet(fiche, [court, f"{court} species", f"{court} Australia"],
                     "nature", "espèce")


# Une classe de batiments modernes porte souvent le nom du cap, et non
# l'inverse : « Leeuwin-class survey vessel » n'illustre pas le navire de 1622.
MODERNES = re.compile(r"\bclass\b|\bHMAS\b|\bHNLMS\b|\bHr\.?Ms\.?\b|\bRAN\b|\b(?:19|20)\d\d\b", re.I)


def par_navigateur(fiche):
    """Le navire ou l'homme dont le cap porte le nom. Le texte de Flinders dit
    souvent lequel -- « Leeuwin (Lioness), a Dutch vessel ... in 1622 » : on y
    prend les mots qui orientent la recherche."""
    court = eponyme(fiche)
    if not court:
        return None
    texte = fiche.get("characteristic") or ""
    indices = [m for m in ("Dutch", "VOC", "Portuguese", "Spanish", "French",
                           "navigator", "explorer", "captain")
               if re.search(rf"\b{m}\b", texte, re.I)]
    requetes = [f"{court} {i} ship" for i in indices[:2]]
    requetes += [f"{court} (ship)", f"{court} ship", f"{court} explorer", court]
    for requete in requetes:
        for titre in recherche_wikipedia(requete, 5):
            if court.split()[0].lower() not in titre.lower() or MODERNES.search(titre):
                continue
            page = page_wikipedia(titre)
            if not page or not page.get("fichier") or REJETS_FICHIER.search(page["fichier"]):
                continue
            if page.get("lat") is not None and fiche.get("lat") is not None:
                if distance_km(fiche["lat"], fiche["lon"], page["lat"], page["lon"]) < 50:
                    continue
            return {"voie": "navigateur", "sujet": page["titre"],
                    "motif": f"navire ou navigateur — « {page['titre']} »",
                    "distance_km": None, "fichier": page["fichier"],
                    "wiki": f"https://en.wikipedia.org/wiki/{urllib.parse.quote(page['titre'])}"}
    return None


def par_article(fiche):
    """Le lieu lui-meme, quand le nom ne renvoie a personne."""
    for titre in filter(None, [fiche.get("ausEName"), fiche.get("frenchName")]):
        page = page_wikipedia(titre)
        if not page or not page.get("fichier") or REJETS_FICHIER.search(page["fichier"]):
            continue
        if page.get("lat") is None:
            continue
        d = distance_km(fiche["lat"], fiche["lon"], page["lat"], page["lon"])
        if d > RAYON_ARTICLE:
            continue
        return {"voie": "lieu", "sujet": page["titre"],
                "motif": f"le lieu — article « {page['titre']} », à {d:.1f} km",
                "distance_km": round(d, 2), "fichier": page["fichier"],
                "wiki": f"https://en.wikipedia.org/wiki/{urllib.parse.quote(page['titre'])}"}
    return None


def mots_du_nom(fiche):
    mots = re.findall(r"[A-Za-z]{4,}", fiche.get("ausEName") or "")
    propres = [m.lower() for m in mots if m.lower() not in GENERIQUES]
    return set(propres) or {m.lower() for m in mots}


def par_commons(fiche):
    mots = mots_du_nom(fiche)
    for rayon in RAYONS_COMMONS:
        trouves = [f for f in commons_geosearch(fiche["lat"], fiche["lon"], rayon)
                   if not REJETS_FICHIER.search(f.get("title", ""))]
        if not trouves:
            continue
        nommes = [f for f in trouves if any(m in f.get("title", "").lower() for m in mots)]
        proches = [f for f in trouves if f.get("dist", 1e9) <= RAYON_SANS_NOM * 1000]
        candidats = nommes or proches
        if not candidats:
            continue
        meilleur = sorted(candidats, key=lambda f: f.get("dist", 0))[0]
        d = meilleur.get("dist", 0) / 1000.0
        nomme = meilleur in nommes
        return {"voie": "lieu", "sujet": meilleur["title"],
                "motif": ("le lieu — photo nommant le lieu, à %.1f km" % d if nomme
                          else "le lieu — photo géolocalisée à %.1f km" % d),
                "distance_km": round(d, 2), "fichier": meilleur["title"], "wiki": ""}
    return None


def cherche(fiche):
    f = famille(fiche)
    passes = {
        "personne":   [par_nom_atteste, par_personne_liee, par_personne, par_article, par_commons],
        "lieu_gb":    [par_lieu_gb, par_nom_atteste, par_personne_liee, par_personne, par_article, par_commons],
        "nature":     [par_nature, par_article, par_commons],
        "navigateur": [par_navigateur, par_nom_atteste, par_personne_liee, par_personne, par_article, par_commons],
        "descriptif": [par_article, par_commons],
    }[f]
    for passe in passes:
        try:
            trouve = passe(fiche)
        except Exception as err:
            print(f"   ! {passe.__name__} : {err}", file=sys.stderr)
            continue
        if trouve:
            trouve["famille"] = f
            trouve.update(commons_infos(trouve["fichier"]))
            trouve["confiance"] = confiance(trouve)
            return trouve
    return None


def confiance(prop):
    """Une illustration de l'eponyme vaut mieux qu'une vue du lieu ; une vue
    du lieu vaut mieux que rien."""
    voie = prop["voie"]
    if voie in ("personne", "lieu_gb", "nature", "navigateur"):
        return "haute"
    if voie == "lieu":
        d = prop.get("distance_km")
        if "article" in prop.get("motif", ""):
            return "moyenne" if (d is not None and d <= 3) else "faible"
        return "moyenne" if "nommant" in prop.get("motif", "") else "faible"
    return "faible"


# --- Planche de controle ---------------------------------------------------

def echantillon(fiches, taille):
    par_cat = {}
    for f in fiches:
        par_cat.setdefault(f.get("categorie") or "?", []).append(f)
    lot, restant = [], taille
    for cat, groupe in sorted(par_cat.items(), key=lambda kv: -len(kv[1])):
        part = max(1, round(taille * len(groupe) / len(fiches)))
        part = min(part, restant, len(groupe))
        pas = max(1, len(groupe) // part)
        lot += groupe[::pas][:part]
        restant -= part
        if restant <= 0:
            break
    return lot[:taille]


PAGE = """<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8">
<title>Visuels proposés — toponymes Flinders</title>
<style>
 body {{ font-family: -apple-system, system-ui, sans-serif; margin: 24px; background: #f7f7f5; color: #222; }}
 h1 {{ font-size: 20px; margin: 0 0 4px; }}
 p.chapeau {{ color: #666; margin: 0 0 20px; font-size: 14px; }}
 .grille {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 16px; }}
 .carte {{ background: #fff; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; display: flex; flex-direction: column; }}
 .carte.retenu {{ border-color: #2a7a2a; box-shadow: 0 0 0 2px #cfe8cf; }}
 .carte img {{ width: 100%; height: 180px; object-fit: cover; background: #eee; display: block; }}
 .corps {{ padding: 10px 12px; font-size: 13px; line-height: 1.4; flex: 1; }}
 .nom {{ font-weight: 700; }}
 .meta {{ color: #666; font-size: 12px; margin-top: 4px; }}
 .voie {{ display: inline-block; font-size: 11px; padding: 1px 6px; border-radius: 10px; background: #e7eefc; color: #1a4b9c; }}
 .voie.hakluyt {{ background: #fdf0d5; color: #8a5a00; }}
 .voie.lieu {{ background: #eee; color: #555; }}
 .voie.personne {{ background: #e7eefc; color: #1a4b9c; }}
 .voie.lieu_gb {{ background: #f3e8fd; color: #5b2a9c; }}
 .voie.nature {{ background: #e8f5e9; color: #256029; }}
 .voie.navigateur {{ background: #fff0e0; color: #8a4b00; }}
 .preuve {{ font-size: 11px; line-height: 1.35; color: #444; background: #f4f6f9; border-left: 2px solid #c3d0e0; padding: 4px 6px; margin-top: 5px; font-style: italic; }}
 .pied {{ padding: 8px 12px; border-top: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; }}
 .barre {{ position: sticky; top: 0; background: #f7f7f5; padding: 10px 0; margin-bottom: 12px; border-bottom: 1px solid #ddd; z-index: 5; }}
 button {{ font: inherit; padding: 6px 12px; border-radius: 6px; border: 1px solid #bbb; background: #fff; cursor: pointer; }}
 textarea {{ width: 100%; height: 60px; font-family: ui-monospace, monospace; font-size: 12px; margin-top: 8px; }}
 label.retenir {{ cursor: pointer; font-weight: 600; }}
</style></head><body>
<h1>Visuels proposés — toponymes Flinders</h1>
<p class="chapeau">{chapeau}</p>
<div class="barre">
  <button onclick="tout(true)">Tout retenir</button>
  <button onclick="tout(false)">Tout décocher</button>
  <button onclick="copier()">Copier les codes retenus</button>
  <span id="compte"></span>
  <textarea id="retenus" readonly></textarea>
</div>
<div class="grille">{cartes}</div>
<script>
 const maj = () => {{
   const r = [...document.querySelectorAll('input:checked')].map(i => i.dataset.code);
   document.getElementById('retenus').value = r.join(',');
   document.getElementById('compte').textContent = r.length + ' retenu(s) sur {total}';
 }};
 document.addEventListener('change', e => {{
   if (e.target.matches('input[type=checkbox]')) {{
     e.target.closest('.carte').classList.toggle('retenu', e.target.checked);
     maj();
   }}
 }});
 const tout = v => {{
   document.querySelectorAll('input[type=checkbox]').forEach(i => {{
     i.checked = v; i.closest('.carte').classList.toggle('retenu', v);
   }});
   maj();
 }};
 const copier = () => {{
   const t = document.getElementById('retenus'); t.select();
   navigator.clipboard.writeText(t.value);
 }};
 maj();
</script></body></html>
"""

ORDRE_VOIE = {"personne": 0, "lieu_gb": 1, "navigateur": 2, "nature": 3, "lieu": 4}


def planche(resultats, chemin, chapeau):
    cartes = []
    resultats = sorted(resultats, key=lambda r: (
        ORDRE_VOIE.get((r.get("proposition") or {}).get("voie"), 9),
        (r.get("proposition") or {}).get("distance_km") or 0))
    for r in resultats:
        f, p = r["fiche"], r.get("proposition")
        nom = html.escape(f.get("ausEName") or f.get("frenchName") or "")
        if p:
            img = p.get("vignette") or p.get("url") or ""
            credit = " · ".join(x for x in (p.get("auteur"), p.get("licence")) if x)
            corps = (f"<div class=\"nom\">{nom}</div>"
                     f"<div class=\"meta\">{html.escape(f.get('categorie') or '')}</div>"
                     f"<div class=\"meta\"><span class=\"voie {p['voie']}\">{p['voie']}</span> "
                     f"{html.escape(p.get('motif') or '')}</div>"
                     + (f"<div class=\"preuve\">« {html.escape(p['preuve'][:220])} »</div>"
                        if p.get("preuve") else "")
                     + f"<div class=\"meta\">{html.escape(credit[:120])}</div>")
            lien = p.get("page") or p.get("wiki") or "#"
        else:
            img, lien = "", "#"
            corps = (f"<div class=\"nom\">{nom}</div>"
                     f"<div class=\"meta\">{html.escape(f.get('categorie') or '')}</div>"
                     f"<div class=\"meta\">aucun candidat</div>")
        coche = "" if not p else (
            f"<label class=\"retenir\"><input type=\"checkbox\" data-code=\"{f['code']}\"> à retenir</label>")
        cartes.append(
            f"<div class=\"carte\"><img src=\"{html.escape(img)}\" alt=\"\" loading=\"lazy\">"
            f"<div class=\"corps\">{corps}</div>"
            f"<div class=\"pied\"><a href=\"{html.escape(lien)}\" target=\"_blank\">{f['code']}</a>"
            f"{coche}</div></div>")
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(PAGE.format(chapeau=html.escape(chapeau),
                                  cartes="\n".join(cartes),
                                  total=len(resultats)), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tout", action="store_true")
    ap.add_argument("--manquantes", action="store_true",
                    help="les fiches qui n'ont pas encore d'image")
    ap.add_argument("--taille", type=int, default=30)
    ap.add_argument("--codes")
    args = ap.parse_args()

    fiches = json.loads(FICHIER.read_text(encoding="utf-8"))
    if args.codes:
        voulus = set(args.codes.split(","))
        lot = [f for f in fiches if f["code"] in voulus]
    elif args.manquantes:
        lot = [f for f in fiches if not (f.get("imgUrl") or "").strip()]
    elif args.tout:
        lot = fiches
    else:
        lot = echantillon(fiches, args.taille)

    resultats = []
    for i, f in enumerate(lot, 1):
        print(f"[{i}/{len(lot)}] {f['code']} {f.get('ausEName')} ({famille(f)})")
        p = cherche(f)
        print(f"   → {p['voie']} : {p.get('motif')}" if p else "   → rien")
        resultats.append({"fiche": f, "proposition": p})

    eponymes = sum(1 for r in resultats
                   if (r["proposition"] or {}).get("voie") in ORDRE_VOIE and
                   (r["proposition"] or {}).get("voie") != "lieu")
    trouves = sum(1 for r in resultats if r["proposition"])
    SORTIE_JSON.parent.mkdir(parents=True, exist_ok=True)
    SORTIE_JSON.write_text(json.dumps(
        [{"code": r["fiche"]["code"], "nom": r["fiche"].get("ausEName"),
          "categorie": r["fiche"].get("categorie"), "classe": r["fiche"].get("classe"),
          "proposition": r["proposition"]} for r in resultats],
        ensure_ascii=False, indent=1), encoding="utf-8")
    planche(resultats, SORTIE_HTML,
            f"{trouves} candidats sur {len(resultats)} fiches, dont {eponymes} illustrent "
            "l’éponyme lui-même. Cochez « à retenir », puis copiez la liste des codes.")
    print(f"\n{trouves}/{len(resultats)} candidats, dont {eponymes} éponymes — "
          f"{SORTIE_HTML.relative_to(RACINE)}")


if __name__ == "__main__":
    main()
