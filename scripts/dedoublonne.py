#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ne garde qu'un exemplaire des fichiers presents plusieurs fois a l'identique.

Le site est publie tel quel : Vercel conserve une copie entiere du depot par
deploiement, et le forfait gratuit plafonne a 10 Go. Or le depot porte 742 Mo
de fichiers rigoureusement identiques, octet pour octet.

Deux causes, l'une et l'autre legitimes a l'origine :

  - plusieurs toponymes figurent sur la meme planche gravee, et chacun en
    gardait sa copie sous son propre code : une planche de 3,8 Mo etait
    stockee trente-trois fois ;
  - une page de detail existe en anglais et en francais, et chaque version
    portait son jeu d'illustrations.

Le contenu ne change pas : une seule copie demeure, et les autres noms y
renvoient. La maniere d'y renvoyer differe selon la facon dont le nom est
ecrit :

  - details/ et rapports/ nomment leurs images en clair dans le HTML. On
    reecrit l'attribut src, et le fichier en trop disparait.
  - img_telecharg/ n'est jamais nomme en clair : map.html calcule le chemin
    depuis le code du toponyme. On dresse donc une table d'alias,
    data/img_alias.json, que la carte consulte.

Ce que le script ne touche pas, et pourquoi :

  - data/podcast_*.m4a, copie conforme de data/baudin_*.m4a (42 Mo). Les
    reunir supposerait que le podcast n'est pas une oeuvre distincte ; c'est
    un choix editorial, pas une question de stockage.
  - img/, dont les trois doublons portent des noms de sens different
    (« finding-aid » et « om3-finding-aid ») pour 0,3 Mo.

Rejouable : un depot deja dedoublonne ne produit plus aucune suppression.

Usage : python3 scripts/dedoublonne.py [--ecrire]
"""
import collections
import hashlib
import io
import json
import os
import re
import subprocess
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALIAS = os.path.join(RACINE, 'data', 'img_alias.json')

# Sous cette taille, le gain ne paie pas le derangement.
SEUIL = 4096
# Dossiers dont les images sont nommees en clair dans le HTML.
EN_CLAIR = ('details/', 'rapports/')
# Dossier dont les chemins sont calcules, et que la table d'alias dessert.
CALCULE = 'img_telecharg/'
# Ou chercher les references a reecrire.
EXTENSIONS = ('.html', '.htm', '.js', '.json', '.css')


def suivis():
    """Les fichiers versionnes : ce sont eux, et eux seuls, qui sont publies."""
    brut = subprocess.run(['git', 'ls-files', '-z'], cwd=RACINE,
                          capture_output=True).stdout
    return [f.decode() for f in brut.split(b'\0') if f]


def groupes(fichiers):
    """Les lots de fichiers rigoureusement identiques, par empreinte."""
    par_empreinte = collections.defaultdict(list)
    for f in fichiers:
        chemin = os.path.join(RACINE, f)
        try:
            taille = os.path.getsize(chemin)
        except OSError:
            continue
        if taille < SEUIL:
            continue
        with open(chemin, 'rb') as fh:
            empreinte = hashlib.sha1(fh.read()).hexdigest()
        par_empreinte[(empreinte, taille)].append(f)
    # Un lot se range par nom : le plus petit numero fait l'original, ce qui
    # rend le choix stable d'une execution a l'autre.
    return {k: sorted(v) for k, v in par_empreinte.items() if len(v) > 1}


def cites(fichiers):
    """Les noms de fichiers que le site nomme en clair quelque part."""
    vus = set()
    for f in fichiers:
        if not f.endswith(EXTENSIONS):
            continue
        try:
            texte = io.open(os.path.join(RACINE, f), encoding='utf-8').read()
        except (UnicodeDecodeError, OSError):
            continue
        vus.update(re.findall(r'[\w-]+\.(?:jpe?g|png|gif|avif|webp)', texte))
    return vus


def par_dossier(lot):
    """Un lot eclate par dossier : on ne renvoie jamais d'un dossier a l'autre.

    Une image de details/ qui se trouve identique a une planche de
    img_telecharg/ garde sa copie : les deux dossiers n'ont ni le meme
    public ni le meme cycle de vie, et les relier rendrait la suppression
    de l'un dangereuse pour l'autre.
    """
    par = collections.defaultdict(list)
    for f in lot:
        par[f.split('/')[0] + '/'].append(f)
    return [v for v in par.values() if len(v) > 1]


def original(lot, nommes):
    """Lequel des jumeaux garder.

    Un nom que le site cite passe avant un nom qu'il ne cite plus : le dossier
    details/ porte encore des images d'une nomenclature abandonnee, et garder
    celles-la reviendrait a rebaptiser les pages d'apres leurs orphelins. A
    egalite, le nom le plus court, puis l'ordre alphabetique -- qui, pour
    img_telecharg/, revient au plus petit numero de toponyme.
    """
    return sorted(lot, key=lambda f: (os.path.basename(f) not in nommes,
                                      len(os.path.basename(f)), f))[0]


def reecrit_references(remplacements, ecrire):
    """Reecrit les noms en clair. Retourne le nombre de fichiers touches."""
    touches = 0
    for f in suivis():
        if not f.endswith(EXTENSIONS):
            continue
        chemin = os.path.join(RACINE, f)
        try:
            texte = io.open(chemin, encoding='utf-8').read()
        except (UnicodeDecodeError, OSError):
            continue
        neuf = texte
        for ancien, canon in remplacements.items():
            if ancien in neuf:
                # Le nom doit etre entier : sans borne, « Baudin12_Carte.jpg »
                # mordrait sur « Baudin120_Carte.jpg ». La barre oblique, elle,
                # est admise devant : une page de la racine cite ses images
                # sous « details/Baudin583F_html_image001.jpg ».
                neuf = re.sub(r'(?<![\w.-])' + re.escape(ancien) + r'(?![\w])',
                              canon, neuf)
        if neuf != texte:
            touches += 1
            if ecrire:
                io.open(chemin, 'w', encoding='utf-8').write(neuf)
    return touches


REFERENCE = re.compile(
    r'(?:src|href|data-img|data-plein|srcset)="([^":?#]+\.(?:jpe?g|png|gif|avif|webp))"')


def references_cassees():
    """Les images qu'une page nomme et qui ne sont pas sur le disque.

    Le depot en portait deja quelques-unes avant tout dedoublonnage. Ce qui
    importe n'est donc pas le compte, mais qu'il n'augmente pas.
    """
    presents = set(suivis())
    cassees = []
    for f in presents:
        if not f.endswith(('.html', '.htm')):
            continue
        try:
            texte = io.open(os.path.join(RACINE, f), encoding='utf-8').read()
        except (UnicodeDecodeError, OSError):
            continue
        for ref in REFERENCE.findall(texte):
            if ref.startswith(('http', '//', 'data:')):
                continue
            cible = os.path.normpath(os.path.join(os.path.dirname(f), ref))
            if cible not in presents:
                cassees.append((f, cible))
    return cassees


def main(ecrire):
    fichiers = suivis()
    lots = groupes(fichiers)
    nommes = cites(fichiers)

    # --- Les noms ecrits en clair : on reecrit, puis on supprime.
    remplacements = {}          # nom de base en trop -> nom de base garde
    a_supprimer = []
    gagne_clair = 0
    # --- Les noms calcules : on dresse la table d'alias.
    alias = {}                  # nom de base en trop -> nom de base garde
    gagne_calcule = 0

    for (_, taille), lot in lots.items():
        for meme_dossier in par_dossier(lot):
            garde = original(meme_dossier, nommes)
            enlever = [f for f in meme_dossier if f != garde]
            dossier = garde.split('/')[0] + '/'
            if dossier in EN_CLAIR:
                for f in enlever:
                    remplacements[os.path.basename(f)] = os.path.basename(garde)
                    a_supprimer.append(f)
                    gagne_clair += taille
            elif dossier == CALCULE:
                for f in enlever:
                    alias[os.path.basename(f)] = os.path.basename(garde)
                    a_supprimer.append(f)
                    gagne_calcule += taille

    # Un alias pose sur le JPEG doit valoir pour son apercu AVIF, sinon la
    # carte irait chercher un apercu qui n'existe plus. Si l'original n'en a
    # pas et qu'un des noms ecartes en avait un, on promeut celui-la.
    # La carte affiche d'abord un apercu AVIF, le temps que la planche arrive.
    # Une planche gardee doit donc avoir le sien. Quand elle n'en a pas et
    # qu'un des noms ecartes en avait un, cet apercu est renomme plutot que
    # supprime : c'est le meme dessin, il change seulement de nom.
    #
    # Le dossier porte aussi des apercus fabriques sur place et non versionnes.
    # Un renommage doit compter avec eux, sinon git mv bute sur un fichier
    # qu'il ne voit pas dans l'index mais qui existe bel et bien.
    promus = []
    presents = set(fichiers)
    occupe = lambda p: p in presents or os.path.exists(os.path.join(RACINE, p))
    for ecarte, canon in sorted(alias.items()):
        if not ecarte.endswith('.jpg'):
            continue
        apercu_canon = CALCULE + canon[:-4] + '.avif'
        apercu_ecarte = CALCULE + ecarte[:-4] + '.avif'
        if occupe(apercu_canon) or apercu_ecarte not in presents:
            continue
        promus.append((apercu_ecarte, apercu_canon))
        presents.add(apercu_canon)
        # Promu, il n'est plus a supprimer -- ni a aliaser vers un nom mort.
        if apercu_ecarte in a_supprimer:
            a_supprimer.remove(apercu_ecarte)
            gagne_calcule -= os.path.getsize(os.path.join(RACINE, apercu_ecarte))
        alias.pop(os.path.basename(apercu_ecarte), None)

    # Un apercu ecarte doit suivre sa planche : si la planche X renvoie a Y,
    # son apercu renvoie a celui de Y, et non a ce que le hasard des empreintes
    # aurait choisi. Sans cela la carte irait sonder un apercu disparu.
    for ecarte, canon in list(alias.items()):
        if not ecarte.endswith('.jpg'):
            continue
        apercu_ecarte, apercu_canon = ecarte[:-4] + '.avif', canon[:-4] + '.avif'
        if occupe(CALCULE + apercu_canon):
            alias[apercu_ecarte] = apercu_canon
        else:
            # La planche gardee n'a pas d'apercu : aucun nom a proposer.
            alias.pop(apercu_ecarte, None)

    # La carte ne resout qu'un saut : la table ne doit donc pas enchainer. Un
    # alias qui vise un alias est reporte sur le terme de la chaine.
    for ecarte in list(alias):
        vu, cible = {ecarte}, alias[ecarte]
        while cible in alias and cible not in vu:
            vu.add(cible)
            cible = alias[cible]
        alias[ecarte] = cible

    # Invariant : on ne renvoie jamais a un fichier qu'on s'apprete a retirer,
    # et tout fichier retire de img_telecharg/ laisse un alias derriere lui.
    for cible in {CALCULE + v for v in alias.values()}:
        if cible in a_supprimer:
            a_supprimer.remove(cible)
            gagne_calcule -= os.path.getsize(os.path.join(RACINE, cible))
    orphelins = [f for f in a_supprimer
                 if f.startswith(CALCULE) and os.path.basename(f) not in alias]
    if orphelins:
        print('ANOMALIE : %d fichiers retires sans alias, rien n\'est ecrit'
              % len(orphelins))
        for f in orphelins[:5]:
            print('   %s' % f)
        return

    Mo = lambda o: o / float(2 ** 20)
    print('fichiers versionnes           : %d' % len(fichiers))
    print('lots de fichiers identiques   : %d' % len(lots))
    print()
    print('noms ecrits en clair (%s)' % ', '.join(d.rstrip('/') for d in EN_CLAIR))
    print('   %d copies retirees, %.1f Mo' % (len(remplacements), Mo(gagne_clair)))
    print('noms calcules (%s)' % CALCULE.rstrip('/'))
    print('   %d copies retirees, %.1f Mo' % (len(alias), Mo(gagne_calcule)))
    if promus:
        print('   %d apercus AVIF renommes pour suivre leur planche' % len(promus))
    print()
    print('TOTAL : %.1f Mo par deploiement' % Mo(gagne_clair + gagne_calcule))

    avant = len(references_cassees())
    print('images citees et introuvables, avant : %d' % avant)

    if not ecrire:
        print('\n(simulation — relancer avec --ecrire)')
        return

    touches = reecrit_references(remplacements, True)
    print('\nreferences reecrites dans %d fichiers' % touches)

    for source, cible in promus:
        subprocess.run(['git', 'mv', source, cible], cwd=RACINE, check=True)
    if promus:
        print('%d apercus AVIF renommes' % len(promus))

    # La table d'alias se reecrit en entier : elle decrit l'etat du dossier,
    # pas l'historique des executions.
    ancienne = {}
    if os.path.exists(ALIAS):
        ancienne = json.load(io.open(ALIAS, encoding='utf-8'))
    ancienne.update(alias)
    json.dump(dict(sorted(ancienne.items())), io.open(ALIAS, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('%s : %d alias' % (os.path.relpath(ALIAS, RACINE), len(ancienne)))

    if a_supprimer:
        for i in range(0, len(a_supprimer), 200):
            subprocess.run(['git', 'rm', '-q', '--'] + a_supprimer[i:i + 200],
                           cwd=RACINE, check=True)
        print('%d fichiers supprimes' % len(a_supprimer))

    apres = references_cassees()
    print('\nimages citees et introuvables, apres : %d' % len(apres))
    if len(apres) > avant:
        print('ATTENTION : le dedoublonnage en a casse %d' % (len(apres) - avant))
        for page, cible in apres[:10]:
            print('   %s cite %s' % (page, cible))


if __name__ == '__main__':
    main('--ecrire' in sys.argv)
