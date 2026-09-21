#!/usr/bin/env python3
"""Porte le glossaire nautique du Markdown dans la page.

La source est `docs/glossaire-nautique.md` ; sa traduction, quand elle
existe, `docs/glossaire-nautique.en.md`. Le script en tire le sommaire et les
notices de chacun des trois volets, et les pose dans `glossary.html` entre
les reperes que la page porte a cet effet. Tant que la traduction manque, le
cote anglais recoit le texte francais : mieux vaut un glossaire lisible dans
une seule langue qu'une page vide.

    python3 scripts/glossaire_nautique.py

Le HTML est ecrit dans la page, pas charge a cote : le moteur de
questions-reponses lit le texte des pages, et ne verrait pas un JSON.
"""
import os
import re
import sys
import unicodedata

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(RACINE, 'glossary.html')
SOURCES = {
    'fr': os.path.join(RACINE, 'docs', 'glossaire-nautique.md'),
    'en': os.path.join(RACINE, 'docs', 'glossaire-nautique.en.md'),
}

# Ordre des volets dans le fichier source, et prefixe de leurs ancres. Le
# prefixe evite que « Mouillage », present dans deux volets, ne serve deux
# fois la meme ancre.
VOLETS = [('manoeuvre', 'man'), ('hydrographie', 'hyd'), ('vie-bord', 'vie')]

HAUT = {'fr': 'Retour en haut', 'en': 'Back to top'}

CORRESPONDANCES = os.path.join(RACINE, 'docs', 'glossaire-correspondances.md')

# Le tableau des correspondances n'est pas valide : il est porte dans la page
# pour que la relecture se fasse sur piece, et le dit.
AVERTISSEMENT = {
    'fr': "Les renvois vers le glossaire anglais sont une proposition, en cours de "
          "relecture.",
    'en': "The cross-references to the French glossary are a proposal, under review.",
}
ETIQUETTE = {'fr': 'Anglais', 'en': 'French logbooks'}
SANS = {'fr': "pas d'équivalent relevé", 'en': 'no counterpart recorded'}


def aplatit_apostrophe(texte):
    return texte.replace('\u2019', "'").strip()


def charge_correspondances():
    """Les rapprochements proposes, tires du tableau de docs/.

    Chaque ligne du tableau porte un signe de certitude, le terme francais, le
    terme anglais -- ou un tiret quand il n'y en a pas -- et la remarque.
    """
    if not os.path.exists(CORRESPONDANCES):
        return []
    couples = []
    for ligne in open(CORRESPONDANCES, encoding='utf-8'):
        m = re.match(r'^\|\s*([●◐○])\s*\|\s*\*\*(.+?)\*\*\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*$', ligne)
        if not m:
            continue
        signe, fr, en, note = m.groups()
        couples.append({
            'fr': aplatit_apostrophe(fr),
            'en': None if en in ('—', '-', '') else en.strip(),
            'niveau': {'●': 'sure', '◐': 'proche', '○': 'aucun'}[signe],
            'note': note.strip(),
        })
    return couples


def charge_anglais_seuls():
    """Le second tableau : termes anglais sans contrepartie francaise, et pourquoi."""
    if not os.path.exists(CORRESPONDANCES):
        return {}
    seuls = {}
    dans_le_tableau = False
    for ligne in open(CORRESPONDANCES, encoding='utf-8'):
        if ligne.startswith('## Termes anglais sans contrepartie'):
            dans_le_tableau = True
            continue
        if dans_le_tableau and ligne.startswith('## '):
            break
        if not dans_le_tableau:
            continue
        m = re.match(r'^\|\s*\*\*(.+?)\*\*\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*$', ligne)
        if m:
            # La note francaise sert la relecture, l'anglaise s'affiche sur la page.
            seuls[m.group(1).strip()] = m.group(3).strip() or m.group(2).strip()
    return seuls




def slug(texte):
    """Une ancre stable : sans accent, sans ponctuation, en minuscules."""
    plat = unicodedata.normalize('NFD', texte)
    plat = ''.join(c for c in plat if unicodedata.category(c) != 'Mn')
    plat = plat.replace('œ', 'oe').replace('æ', 'ae')
    plat = re.sub(r'[^a-zA-Z0-9]+', '-', plat).strip('-').lower()
    return plat


def italiques(texte):
    """Le Markdown des remarques : *un mot* devient une emphase, non des etoiles."""
    return re.sub(r'\*([^*]+)\*', r'<em>\1</em>', echappe(texte))


def echappe(texte):
    return (texte.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))


def lit_source(chemin):
    """Les trois volets du fichier : titre, intro, sous-sections et termes.

    Le format est celui que produit la relecture : `## volet`, `### section`,
    puis chaque terme en gras sur sa ligne et sa definition au-dessous.
    """
    with open(chemin, encoding='utf-8') as f:
        texte = f.read()

    volets = []
    for bloc in re.split(r'^## ', texte, flags=re.M)[1:]:
        lignes = bloc.split('\n')
        volet = {'titre': lignes[0].strip(), 'intro': '', 'contenu': []}
        courant = None
        for ligne in lignes[1:]:
            brut = ligne.strip()
            if not brut:
                continue
            if brut.startswith('### '):
                volet['contenu'].append(('section', brut[4:].strip()))
                courant = None
            elif brut.startswith('> '):
                # Une remarque de fin de section : elle porte sur l'ensemble
                # des termes qui precedent, non sur le dernier d'entre eux.
                volet['contenu'].append(('note', brut[2:].strip()))
                courant = None
            elif brut.startswith('**') and brut.endswith('**'):
                courant = [brut.strip('*').strip(), []]
                volet['contenu'].append(('terme', courant))
            elif courant is not None:
                courant[1].append(brut)
            elif not volet['contenu']:
                # Avant le premier titre ou terme : c'est l'intro du volet.
                volet['intro'] += (' ' if volet['intro'] else '') + brut
        volets.append(volet)

    if len(volets) != len(VOLETS):
        sys.exit(f'{chemin} : {len(volets)} volets au lieu de {len(VOLETS)}.')
    return volets


def rend_volet(volet, prefixe, langue, renvois=None):
    """Le sommaire du volet, puis ses notices.

    Les deux langues tiennent le meme terme -- « Abattre » reste « Abattre »
    meme une fois sa definition traduite. L'ancre anglaise porte donc sa
    langue en suffixe, sans quoi les deux moities de la page se disputeraient
    le meme identifiant et le lien tomberait toujours sur la premiere.
    """
    suffixe = '' if langue == 'fr' else f'-{langue}'
    lignes = []

    # Deux termes de meme nom -- « Tournevire » parait sous les ancres et sous
    # les palans -- se disputeraient la meme ancre. Le second prend un rang.
    # On les arrete une bonne fois ici : le sommaire et les notices tirent
    # ensuite de la meme liste, et ne peuvent plus se desaccorder.
    vus = {}
    ancres = []
    termes = []
    for genre, valeur in volet['contenu']:
        if genre != 'terme':
            continue
        terme = valeur[0]
        base = f'{prefixe}-{slug(terme)}'
        vus[base] = vus.get(base, 0) + 1
        rang = '' if vus[base] == 1 else f'-{vus[base]}'
        ancres.append(f'{base}{rang}{suffixe}')
        termes.append(terme)

    if volet['intro']:
        lignes.append(f'            <p class="part-intro">{echappe(volet["intro"])}</p>')
    if renvois:
        lignes.append(f'            <p class="part-avis">{echappe(AVERTISSEMENT[langue])}</p>')

    lignes.append('            <ul class="toc">')
    for terme, ancre in zip(termes, ancres):
        lignes.append(f'                <li><a href="#{ancre}">{echappe(terme)}</a></li>')
    lignes.append('            </ul>')

    suivante = iter(ancres)
    for genre, valeur in volet['contenu']:
        if genre == 'section':
            lignes.append(f'\n            <h3 class="part-section">{echappe(valeur)}</h3>')
            continue
        if genre == 'note':
            lignes.append(f'\n            <p class="part-note">{echappe(valeur)}</p>')
            continue
        terme, paragraphes = valeur
        ancre = next(suivante)
        corps = '\n                '.join(
            f'<p>{echappe(p)}</p>' for p in paragraphes) or '<p></p>'
        renvoi = (renvois or {}).get(aplatit_apostrophe(terme))
        if renvoi:
            mots_autres, niveau, note = renvoi
            if niveau == 'aucun':
                dit = f'<em>{echappe(SANS[langue])}</em>'
            else:
                # Plusieurs termes d'une langue visent parfois le meme mot dans
                # l'autre -- abattre, arriver et laisser arriver se disent tous
                # « bear away ». On les montre tous, sans quoi la notice
                # anglaise n'en garderait qu'un, le dernier venu.
                #
                # Le terme est donne en clair, sans lien. Les deux glossaires
                # occupent la meme page, mais le selecteur de langue en masque
                # une moitie : un lien vers l'autre langue ne menerait a rien de
                # visible, et l'atteindre demanderait de changer de langue pour
                # revenir ensuite. Le mot suffit a qui veut le chercher.
                dit = ', '.join(f'<strong>{echappe(mot)}</strong>' for mot in mots_autres)
            # Les remarques sont redigees en francais, pour la relecture. On les
            # montre du cote francais ; du cote anglais, seuls les termes isoles
            # portent une note, ecrite pour eux dans la bonne langue.
            if note and (langue == 'fr' or niveau == 'aucun'):
                dit += f' — <em>{italiques(note)}</em>'
            corps += (f'\n                <p class="renvoi renvoi--{niveau}">'
                      f'<span class="renvoi-clef">{ETIQUETTE[langue]}</span> {dit}</p>')
        lignes.append(f'''
            <section class="entry">
                <h4 id="{ancre}" class="entry-title is-term">
                    <span>{echappe(terme)}</span>
                    <a class="backtop" href="#top" title="{HAUT[langue]}">
                        <img src="img/up-arrow.svg" alt="{HAUT[langue]}">
                    </a>
                </h4>
                {corps}
            </section>''')

    return '\n'.join(lignes)


def pose(html, langue, cle, contenu):
    """Remplace ce qui se trouve entre les deux reperes du volet."""
    debut = f'<!-- nautique:{langue}:{cle}:debut -->'
    fin = f'<!-- nautique:{langue}:{cle}:fin -->'
    if debut not in html or fin not in html:
        sys.exit(f'Reperes introuvables pour {langue}/{cle} dans la page.')
    avant, reste = html.split(debut, 1)
    _, apres = reste.split(fin, 1)
    return f'{avant}{debut}\n{contenu}\n            {fin}{apres}'


def main():
    with open(PAGE, encoding='utf-8') as f:
        html = f.read()

    couples = charge_correspondances()
    # Le renvoi mene au terme de l'autre langue : on le prepare dans les deux sens.
    renvois = {'fr': {}, 'en': {}}
    accumule = {'fr': {}, 'en': {}}
    for c in couples:
        if c['en']:
            accumule['fr'].setdefault(c['fr'], []).append(
                (c['en'], c['niveau'], c['note']))
            accumule['en'].setdefault(c['en'], []).append(
                (c['fr'], c['niveau'], c['note']))
        else:
            renvois['fr'][c['fr']] = ((), 'aucun', c['note'])

    for langue in ('fr', 'en'):
        for terme, liste in accumule[langue].items():
            mots = tuple(x[0] for x in liste)
            # Le degre le plus prudent l'emporte, et les remarques se suivent.
            niveau = 'proche' if any(x[1] == 'proche' for x in liste) else 'sure'
            notes = [x[2] for x in liste if x[2]]
            renvois[langue][terme] = (mots, niveau, ' '.join(notes))

    # Les termes anglais que le francais ne nomme pas : on le dit aussi.
    for terme, pourquoi in charge_anglais_seuls().items():
        renvois['en'].setdefault(terme, ((), 'aucun', pourquoi))

    for langue in ('fr', 'en'):
        chemin = SOURCES[langue]
        repli = ''
        if not os.path.exists(chemin):
            chemin = SOURCES['fr']
            repli = ' (texte français, traduction à venir)'
        volets = lit_source(chemin)
        for volet, (cle, prefixe) in zip(volets, VOLETS):
            html = pose(html, langue, cle,
                        rend_volet(volet, prefixe, langue, renvois[langue]))
        termes = sum(1 for v in volets for c in v['contenu'] if c[0] == 'terme')
        print(f'{langue} : {termes} termes posés{repli}')

    with open(PAGE, 'w', encoding='utf-8') as f:
        f.write(html)


if __name__ == '__main__':
    main()
