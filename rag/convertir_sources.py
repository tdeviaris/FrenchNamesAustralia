#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Convertit en Markdown les journaux et documents que le site ne publie pas.

Ce sont les pièces qui vivent hors du site : les transcriptions du Baudin
Legacy Project (université de Sydney), les transcriptions du journal de Hamelin
tenues par Dany Bréelle, le récit publié de Flinders chez Project Gutenberg
Australia, et quelques documents déposés dans docs/.

Chacune devient un seul fichier .md sous rag/corpus/journaux/, coiffé d'un
en-tête qui dit l'auteur, la cote, la langue et la provenance — c'est cet
en-tête que le chatbot cite quand il rend une réponse.

Les sources ne sont pas retéléchargées ici : voir rag/telecharger_sources.sh.

Usage : python3 rag/convertir_sources.py [--seulement <motif>]
"""
import os
import re
import subprocess
import sys
import unicodedata

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES = os.path.join(RACINE, 'rag', 'sources')
CORPUS = os.path.join(RACINE, 'rag', 'corpus', 'journaux')
DOCS_PROJET = os.path.join(os.path.dirname(RACINE), 'docs')

SYDNEY = 'https://baudin.sydney.edu.au/journals/'

# nom de fichier -> (titre, auteur, cote, langue)
JOURNAUX_SYDNEY = {
    'N-Baudin-Journal-de-mer-vol-1-': ("Journal de mer, volume 1", "Nicolas Baudin", "ANF Marine 5JJ36", 'fr'),
    'anon1journalbaud': ("Journal anonyme n° 1", "anonyme", "", 'fr'),
    'anon2': ("Journal anonyme n° 2", "anonyme", "", 'fr'),
    'bougainville': ("Journal", "Hyacinthe de Bougainville", "", 'fr'),
    'breton': ("Journal", "Désiré Breton", "", 'fr'),
    'brevedentjournalnautiquehistoriquecahier1': ("Journal nautique et historique, cahier 1", "Léon Brèvedent", "", 'fr'),
    'brevedentjournalnautiquehistoriquecahier2': ("Journal nautique et historique, cahier 2", "Léon Brèvedent", "", 'fr'),
    'bruefrench': ("Journal", "Joseph Brüe", "", 'fr'),
    'couture': ("Journal", "Joseph Victor Couture", "", 'fr'),
    'duvaldaillycahier1': ("Journal, cahier 1", "Étienne Henry Mengin Duvaldailly", "", 'fr'),
    'gicquel': ("Journal", "Pierre Guillaume Gicquel", "", 'fr'),
    'giraud': ("Journal", "Étienne Giraud", "", 'fr'),
    'heirisson': ("Journal", "François Antoine Heirisson", "", 'fr'),
    'henrifreycinet': ("Journal", "Henri de Freycinet", "", 'fr'),
    'leschenault': ("Journal", "Jean Baptiste Leschenault de La Tour", "", 'fr'),
    'levillainANF5JJ52french': ("Journal", "Stanislas Levillain", "ANF Marine 5JJ52", 'fr'),
    'louisfreycinet': ("Journal", "Louis de Freycinet", "", 'fr'),
    'maurouardjournalhistorique9bis': ("Journal historique", "Jean Marie Maurouard", "ANF Marine 5JJ9bis", 'fr'),
    'maurouardjournalhydrographique9ter': ("Journal hydrographique", "Jean Marie Maurouard", "ANF Marine 5JJ9ter", 'fr'),
    'ronsardjournal5JJ28': ("Journal", "François Michel Ronsard", "ANF Marine 5JJ28", 'fr'),
    'ronsardjournalnautiquevol15jj29': ("Journal nautique, volume 1", "François Michel Ronsard", "ANF Marine 5JJ29", 'fr'),
    'ronsardjournalnautiquevol25jj30': ("Journal nautique, volume 2", "François Michel Ronsard", "ANF Marine 5JJ30", 'fr'),
    'saintcricq': ("Journal", "Jacques de Saint-Cricq", "", 'fr'),
}

# Les onze cahiers mensuels de la transcription du cahier 1 de Hamelin, dans
# l'ordre du calendrier républicain et non dans celui, trompeur, des noms de
# fichiers (« 10- » se trie avant « 2- »).
HAMELIN_MOIS = [
    ('1-du6thermidorau30vendemiairean9.doc', "du 6 thermidor au 30 vendémiaire an 9"),
    ('2-du_1_au_30_brumaire_an9.doc', "du 1er au 30 brumaire an 9"),
    ('3-frimaire_an9.doc', "frimaire an 9"),
    ('4-_nivôse_an9.doc', "nivôse an 9"),
    ('5-_pluviôse_an9.doc', "pluviôse an 9"),
    ('6-_ventôse_an9.doc', "ventôse an 9"),
    ('7-_germinal_an9.doc', "germinal an 9"),
    ('8-_floréal_an9.doc', "floréal an 9"),
    ('9-_prairial_an9.doc', "prairial an 9"),
    ('10-_messidoran9.doc', "messidor an 9"),
    ('11-_thermidor_an9.doc', "thermidor an 9"),
]


def ardoise(nom):
    """Un nom de fichier sûr : accents translittérés plutôt qu'escamotés.

    Sans la translittération, « Références » donnerait « r_f_rences » — le nom
    reste unique, mais plus personne ne le retrouve à l'œil.
    """
    nom = unicodedata.normalize('NFKD', nom).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', '_', nom.lower()).strip('_')


def entete(titre, auteur, source, langue, complements=()):
    """L'en-tête YAML que file_search rend au chatbot avec le passage trouvé."""
    lignes = ['---', f'titre: "{titre}"']
    if auteur:
        lignes.append(f'auteur: "{auteur}"')
    lignes.append(f'langue: {langue}')
    lignes.append(f'source: "{source}"')
    for cle, valeur in complements:
        if valeur:
            lignes.append(f'{cle}: "{valeur}"')
    lignes += ['---', '', f'# {titre}', '']
    if auteur:
        lignes.append(f'**Auteur :** {auteur}')
    lignes.append(f'**Source :** {source}')
    lignes += ['', '---', '']
    return '\n'.join(lignes)


def nettoie(texte):
    """Rend lisible un texte sorti d'un PDF ou d'un .doc.

    Les césures de fin de ligne sont recollées, les lignes d'un même paragraphe
    réunies, et les blancs multiples réduits. On garde les sauts de paragraphe :
    ce sont eux qui découpent les morceaux indexés.
    """
    texte = texte.replace('\r\n', '\n').replace('\r', '\n')
    texte = unicodedata.normalize('NFC', texte)
    texte = texte.replace('­', '')          # trait d'union conditionnel
    # textutil laisse passer les codes de champ Word des notes de bas de page.
    # On retire le code et on garde la note : « PAGE \# "'Page: '#' '" gabier »
    # vaut mieux réduit à « gabier ».
    texte = re.sub(r'PAGE\s+\\\*?#?\s*"[^"]*"\s*', '', texte)
    texte = re.sub(r'^\s*PAGE(\s+\d+)?\s*$', '', texte, flags=re.M)
    texte = re.sub(r'[ \t ]+', ' ', texte)
    texte = re.sub(r'(\w)-\n(\w)', r'\1\2', texte)   # césure recollée
    texte = re.sub(r'\n{3,}', '\n\n', texte)
    lignes = [l.strip() for l in texte.split('\n')]
    return '\n'.join(lignes).strip()


def texte_du_pdf(chemin):
    """Extrait le texte page à page, en marquant chaque saut de page."""
    import pymupdf
    document = pymupdf.open(chemin)
    morceaux = []
    for numero, page in enumerate(document, start=1):
        brut = page.get_text('text')
        if brut.strip():
            morceaux.append(f'\n\n[page {numero}]\n\n' + brut)
    document.close()
    return nettoie(''.join(morceaux))


def texte_du_document(chemin):
    """Passe un .doc, .docx ou .rtf par textutil, qui est fourni par macOS."""
    sortie = subprocess.run(
        ['textutil', '-convert', 'txt', '-stdout', chemin],
        capture_output=True, check=True,
    )
    return nettoie(sortie.stdout.decode('utf-8', errors='replace'))


def texte_de_gutenberg(chemin):
    """Tire le récit de la page Project Gutenberg Australia.

    La page est un long flot de <p> précédé du bandeau du site et suivi de rien.
    On coupe au titre de l'ouvrage, et on garde les titres de chapitre que
    Flinders a mis en majuscules — ils portent les dates que le récit date.
    """
    from bs4 import BeautifulSoup
    with open(chemin, encoding='utf-8', errors='replace') as f:
        soupe = BeautifulSoup(f.read(), 'html.parser')
    for balise in soupe(['script', 'style', 'head']):
        balise.decompose()
    texte = soupe.get_text('\n')
    depart = texte.find('PRODUCTION NOTES')
    if depart > 0:
        texte = texte[depart:]
    return nettoie(texte)


def ecrit(nom, contenu):
    chemin = os.path.join(CORPUS, nom)
    with open(chemin, 'w', encoding='utf-8') as f:
        f.write(contenu)
    print(f'  ✅ {nom}  ({len(contenu):,} car.)'.replace(',', ' '))
    return len(contenu)


def convertit_sydney(motif):
    print('\n📘 Journaux du Baudin Legacy Project (université de Sydney)')
    for base, (titre, auteur, cote, langue) in sorted(JOURNAUX_SYDNEY.items(), key=lambda x: x[1][1]):
        if motif and motif not in base:
            continue
        chemin = os.path.join(SOURCES, 'sydney', base + '.pdf')
        if not os.path.exists(chemin):
            print(f'  ⚠️  absent : {base}.pdf')
            continue
        corps = texte_du_pdf(chemin)
        nom = 'sydney_' + ardoise(base) + '.md'
        ecrit(nom, entete(
            f'{auteur} — {titre}', auteur,
            f'Baudin Legacy Project, {SYDNEY} ({base}.pdf)', langue,
            [('cote', cote), ('expedition', 'Baudin')],
        ) + corps + '\n')


def convertit_hamelin(motif):
    if motif and 'hamelin' not in motif:
        return
    print("\n📗 Journal de Jacques Félix Emmanuel Hamelin (transcriptions Dany Bréelle)")
    racine = os.path.join(SOURCES, 'hamelin')
    origine = ("collection privée Dany Bréelle (OneDrive), "
               "dossier Documents/WORK/researchwork/Hamelin")

    # Le cahier 1, transcrit mois républicain par mois républicain.
    morceaux = []
    for fichier, mois in HAMELIN_MOIS:
        chemin = os.path.join(racine, 'cahier1_transcription', fichier)
        if not os.path.exists(chemin):
            print(f'  ⚠️  absent : {fichier}')
            continue
        morceaux.append(f'\n\n## {mois.capitalize()}\n\n' + texte_du_document(chemin))
    if morceaux:
        ecrit('hamelin_cahier1_transcription.md', entete(
            "Jacques Félix Emmanuel Hamelin — Journal du Naturaliste, cahier 1 (transcription)",
            "Jacques Félix Emmanuel Hamelin",
            origine + ", dossier « transciptcahier1 oct05 »", 'fr',
            [('transcription', 'Dany Bréelle'), ('expedition', 'Baudin'),
             ('navire', 'le Naturaliste'), ('etat', 'transcription en cours, cahier 1 seul')],
        ) + ''.join(morceaux) + '\n')

    # Le volume 1 existe en cinq états sur OneDrive. Quatre d'entre eux —
    # Hamelin_vol1_d1, d1-index, journalHamreprise1 et l'état de 2023 —
    # partagent 97 à 99 % de leur vocabulaire : ce sont des enregistrements
    # successifs du même travail. On n'indexe que le plus récent, sans quoi
    # une même journée reviendrait quatre fois dans les réponses. Les autres
    # restent dans rag/sources/hamelin/ pour qui voudrait les comparer.
    autres = [
        ('Hamelin_vol1_2023.doc', "Journal du Naturaliste, volume 1 (état de 2023)",
         "la reprise la plus récente de la transcription, révisée en février 2023"),
        ('Hamelin_vol1_pp1-15.doc', "Journal du Naturaliste, volume 1, pages 1 à 15",
         "déchiffrement détaillé des quinze premières pages"),
        ('Hamelin_et_sa_mission.doc', "Hamelin et sa mission", "notice de Dany Bréelle"),
    ]
    for fichier, titre, note in autres:
        chemin = os.path.join(racine, fichier)
        if not os.path.exists(chemin):
            print(f'  ⚠️  absent : {fichier}')
            continue
        nom = 'hamelin_' + ardoise(os.path.splitext(fichier)[0]) + '.md'
        ecrit(nom, entete(
            f'Jacques Félix Emmanuel Hamelin — {titre}',
            "Jacques Félix Emmanuel Hamelin",
            f'{origine}, {fichier}', 'fr',
            [('transcription', 'Dany Bréelle'), ('expedition', 'Baudin'),
             ('navire', 'le Naturaliste'), ('note', note)],
        ) + texte_du_document(chemin) + '\n')

    pdf = os.path.join(racine, 'Hamelin_Naturaliste_Port_Jackson.pdf')
    if os.path.exists(pdf):
        ecrit('hamelin_naturaliste_port_jackson.md', entete(
            "Le Naturaliste au Port Jackson : le témoignage du capitaine Hamelin",
            "Dany Bréelle",
            f'{origine}, Naturalisteau Port Jackson le temoignagedu capitaineHamelin.pdf', 'fr',
            [('expedition', 'Baudin'), ('navire', 'le Naturaliste')],
        ) + texte_du_pdf(pdf) + '\n')


def convertit_gutenberg(motif):
    if motif and 'flinders' not in motif and 'gutenberg' not in motif:
        return
    print('\n📕 Matthew Flinders, A Voyage to Terra Australis (1814)')
    for numero, identifiant in ((1, 'e00049'), (2, 'e00050')):
        chemin = os.path.join(SOURCES, 'gutenberg', f'flinders_voyage_vol{numero}_{identifiant}.html')
        if not os.path.exists(chemin):
            print(f'  ⚠️  absent : vol. {numero}')
            continue
        ecrit(f'flinders_voyage_terra_australis_vol{numero}.md', entete(
            f'Matthew Flinders — A Voyage to Terra Australis, volume {numero}',
            'Matthew Flinders',
            f'Project Gutenberg Australia, https://gutenberg.net.au/ebooks/{identifiant}.html', 'en',
            [('publication', 'Londres, G. and W. Nicol, 1814'), ('expedition', 'Flinders')],
        ) + texte_de_gutenberg(chemin) + '\n')


def convertit_documents_locaux(motif):
    """Les pièces déjà présentes dans docs/, à la racine du projet Toponymes."""
    print('\n📙 Documents déposés dans docs/')
    pieces = [
        ('Flinders_Toponymy.pdf', os.path.join(RACINE, 'docs'),
         "Flinders's Australian Toponymy and its British Connections",
         'Dany Bréelle', 'en',
         "Journal of the Hakluyt Society, https://www.hakluyt.com/downloadable_files/Journal/Flinders_Toponymy.pdf",
         [('expedition', 'Flinders')]),
        ('Flinders Journal Investigator Transcription.doc', DOCS_PROJET,
         "Journal de bord de l'Investigator (transcription)",
         'Matthew Flinders', 'en',
         "transcription du journal de bord de l'Investigator, dossier docs/ du projet",
         [('expedition', 'Flinders'), ('navire', "l'Investigator")]),
        ('Baudin Journal de mer complet.docx', DOCS_PROJET,
         "Journal de mer autographe de Nicolas Baudin (transcription Marc Soviche)",
         'Nicolas Baudin', 'fr',
         "transcription de Marc Soviche d'après les Archives nationales, Marine 5JJ36 à 5JJ40",
         [('expedition', 'Baudin'), ('transcription', 'Marc Soviche'),
          ('cote', 'ANF Marine 5JJ36-5JJ40')]),
        ('Baudin-Bibliography-Current-9-September-2023.docx', DOCS_PROJET,
         "Bibliographie du Baudin Legacy Project (9 septembre 2023)",
         '', 'en',
         "Baudin Legacy Project, université de Sydney",
         [('expedition', 'Baudin'), ('type', 'bibliographie')]),
        # L'export EndNote de Dany Bréelle : 504 références, francophones pour
        # l'essentiel, avec les cotes BnF et les liens Gallica. Elle ne partage
        # que 84 auteurs sur 295 avec celle de Sydney — les deux se complètent.
        ('Références Terres Australes Endnotes Sept 26.rtf', DOCS_PROJET,
         "Références sur les Terres australes (bibliographie Dany Bréelle)",
         'Dany Bréelle', 'fr',
         "bibliographie de travail de Dany Bréelle, export EndNote de septembre 2026",
         [('type', 'bibliographie'), ('references', '504')]),
    ]
    for fichier, dossier, titre, auteur, langue, source, complements in pieces:
        if motif and motif.lower() not in fichier.lower():
            continue
        chemin = os.path.join(dossier, fichier)
        if not os.path.exists(chemin):
            print(f'  ⚠️  absent : {chemin}')
            continue
        corps = texte_du_pdf(chemin) if chemin.lower().endswith('.pdf') else texte_du_document(chemin)
        nom = ardoise(os.path.splitext(fichier)[0]) + '.md'
        ecrit(nom, entete(titre, auteur, source, langue, complements) + corps + '\n')


def main():
    motif = None
    if '--seulement' in sys.argv:
        motif = sys.argv[sys.argv.index('--seulement') + 1]
    os.makedirs(CORPUS, exist_ok=True)
    convertit_sydney(motif)
    convertit_hamelin(motif)
    convertit_gutenberg(motif)
    convertit_documents_locaux(motif)
    fichiers = sorted(f for f in os.listdir(CORPUS) if f.endswith('.md'))
    total = sum(os.path.getsize(os.path.join(CORPUS, f)) for f in fichiers)
    print(f'\n📦 rag/corpus/journaux/ : {len(fichiers)} fichiers, {total / 1e6:.1f} Mo')


if __name__ == '__main__':
    main()
