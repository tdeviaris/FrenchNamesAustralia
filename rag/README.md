# La base de connaissance du chatbot

Le chatbot du site (`api/responses-chat.js`) répond en cherchant dans un
**Vector Store** OpenAI, que l'API Responses interroge via `file_search`. Ce
dossier fabrique ce magasin et garde trace de ce qu'on y a mis.

Avant, il contenait six fichiers : deux JSON de toponymes, deux textes et deux
PDF de présentation. Le reste du site — les 483 fiches détaillées, le glossaire,
la méthodologie, les journaux de bord — n'était pas interrogeable, et les
journées de journal sans coordonnées, que la carte ne montre jamais, restaient
invisibles. Il en contient aujourd'hui **1 853**, pour une trentaine de méga-octets.

## La chaîne

```
   sources du dehors          le site lui-même
   (PDF, .doc, HTML)          (HTML, JSON, CSV)
          │                          │
  convertir_sources.py        extraire_site.py
          │                          │
          └──────────┬───────────────┘
                     ▼
              rag/corpus/**.md
                     │
               indexer.mjs
                     ▼
            Vector Store OpenAI
```

Dans l'ordre :

```bash
./rag/telecharger_sources.sh tout     # rapatrie ce qui vient du dehors
.venv/bin/python rag/convertir_sources.py
.venv/bin/python rag/extraire_site.py
node rag/indexer.mjs --essai          # compte, n'envoie rien
node rag/indexer.mjs                  # crée un magasin neuf et l'emplit
```

`extraire_site.py` et `convertir_sources.py` réécrivent `rag/corpus/` sans rien
détruire d'autre ; on peut les relancer autant de fois qu'on veut. En revanche
`indexer.mjs` crée un magasin de plus à chaque appel : il coûte de l'argent et
du temps, on ne le lance donc qu'une fois le corpus jugé bon. Et une fois
lancé, **on ne touche plus à `rag/corpus/`** : les fichiers sont lus au fil des
lots, et un fichier réécrit en cours de route part dans le magasin dans l'un ou
l'autre état, sans qu'on sache lequel.

## Ce que contient le corpus

| Dossier | Fichiers | Contenu |
|---|---:|---|
| `corpus/toponymes/` | 1 021 | Une notice par lieu — 602 Baudin, 351 Flinders, 68 d'Entrecasteaux. Origine du nom, caractéristiques et histoire dans les deux langues, coordonnées, nom autochtone. |
| `corpus/site/` | 513 | Les 34 pages de la racine et les 483 fiches détaillées de `details/`, texte extrait. |
| `corpus/journaux_site/` | 271 | Les journaux que porte le site, un fichier par journal et par mois. **Toutes** les journées, y compris celles sans position : 307 journées de Flinders, 42 de Baudin et 114 de Breton que la carte ne montre jamais. |
| `corpus/journaux/` | 35 | Les journaux et documents du dehors, un fichier chacun. |
| `corpus/donnees/` | 13 | Chronologies, attributions Hakluyt, citations, relevés de carte, tables de route. |

Chaque `.md` commence par un en-tête YAML — titre, auteur, langue, source, cote
— que `file_search` rend au modèle avec le passage trouvé. C'est ce qui permet
au chatbot de dire « selon le journal de Ronsard » plutôt que « selon mes
données ».

Deux fichiers de `data/` sont laissés de côté : `ne_10m_coastline.geojson` et
`ne_10m_land.geojson`, qui sont des millions de coordonnées de littoral sans un
mot de texte, et `img_alias.json`, qui n'est qu'une table de correspondance de
noms de fichiers.

## Les sources du dehors

### Baudin Legacy Project (université de Sydney)

<https://baudin.sydney.edu.au/journals/> publie 41 PDF : les transcriptions en
français et, pour la plupart, leur traduction anglaise. On ne prend que les
**23 versions en langue d'origine** — chaque journal traduit possède son
original français, la traduction n'ajouterait rien qu'un doublon dans les
réponses.

Baudin, Bougainville, Breton, Brèvedent (deux cahiers), Brüe, Couture,
Duvaldailly, Henri de Freycinet, Louis de Freycinet, Gicquel, Giraud,
Heirisson, Leschenault, Levillain, Maurouard (journal historique et journal
hydrographique), Ronsard (trois versions), Saint-Cricq, et deux journaux
anonymes. Soit 2 023 pages, toutes pourvues d'une couche texte.

Le site marque le journal de **Hamelin** « non disponible » : il ne vient donc
pas de là.

### Hamelin

Le journal de Jacques Félix Emmanuel Hamelin, capitaine du *Naturaliste*, n'a
jamais été publié. Il existe :

- en **manuscrit** : 168 pages pour le cahier 1, 220 pour le cahier 2, scans
  d'une écriture cursive de 1801, non transcrits ;
- en **transcription partielle**, celle de Dany Bréelle, qui couvre le cahier 1
  — de thermidor an 8 à thermidor an 9, soit juillet 1800 à août 1801.

C'est cette transcription qui est indexée, sous deux formes : le découpage par
mois républicain (`transciptcahier1 oct05`, la plus détaillée) et l'état de
février 2023 du volume 1. Les trois autres états trouvés sur OneDrive
(`Hamelin_vol1_d1`, `d1-index`, `journalHamreprise1`) partagent 97 à 99 % de
leur vocabulaire avec celui de 2023 : ce sont des enregistrements successifs du
même travail, et les indexer ferait revenir quatre fois la même journée dans
les réponses. Ils restent dans `rag/sources/hamelin/` pour qui voudrait les
comparer.

**Au-delà d'août 1801, le journal de Hamelin n'est pas transcrit.** Les
instructions du chatbot le lui font dire plutôt que de laisser croire au
silence de la source.

#### Retélécharger depuis OneDrive

Le dossier est partagé en lecture, mais SharePoint renvoie 403 à `curl` tant
qu'on ne lui présente pas un cookie `FedAuth`. Pour l'obtenir :

1. ouvrir le lien de partage dans un navigateur — il ne demande aucun compte ;
2. relever le cookie `FedAuth` posé sur `onedrive.live.com` ;
3. `FEDAUTH='<valeur>' ./rag/telecharger_sources.sh hamelin`

Le cookie ne vit que quelques heures. L'API qui répond est
`_api/web/GetFileByServerRelativePath(decodedurl='…')/$value` ; `download.aspx`
et `api.onedrive.com`, eux, refusent.

### Project Gutenberg Australia

Les deux volumes de *A Voyage to Terra Australis* (Londres, 1814) :
<https://gutenberg.net.au/ebooks/e00049.html> et `e00050.html`.

Le serveur débite très lentement — il faut compter une bonne dizaine de minutes
par volume — et coupe la connexion au bout du délai : un `curl` par défaut
rapporte un texte **tronqué en plein milieu d'une phrase, sans signaler la
moindre erreur**. Il faut `--max-time 900`, et vérifier ce qu'on a obtenu : le
volume 1 pèse 995 125 octets, le volume 2 en pèse 1 058 768, et tous deux se
terminent par `</html>`. S'ils s'arrêtent ailleurs, relancer — c'est arrivé
quatre fois de suite avant d'aboutir.

### Documents déposés dans `docs/`

- `Flinders_Toponymy.pdf` — Dany Bréelle, « Flinders's Australian Toponymy and
  its British Connections », *Journal of the Hakluyt Society*
- `Flinders Journal Investigator Transcription.doc` — le journal de bord de
  l'*Investigator*, transcrit (c'est la pièce que pointe le lien OneDrive du
  cahier des charges ; elle était déjà là)
- `Baudin Journal de mer complet.docx` — le journal autographe de Baudin
  transcrit par Marc Soviche d'après les Archives nationales, Marine 5JJ36-40
- `Baudin-Bibliography-Current-9-September-2023.docx` — la bibliographie du
  Baudin Legacy Project, anglophone, 632 auteurs
- `Références Terres Australes Endnotes Sept 26.rtf` — la bibliographie de
  travail de Dany Bréelle, export EndNote : 504 références, francophones pour
  l'essentiel, avec les cotes BnF et les liens Gallica. Elle ne partage que 84
  auteurs sur 295 avec celle de Sydney — les deux se complètent plus qu'elles
  ne se recouvrent, et les deux sont indexées.

## Essayer le site en local

Un simple serveur de fichiers ne suffit pas : la page du Q&R appelle
`/api/responses-chat` sur son propre hôte, et personne ne répond — le chatbot
reste muet sans le moindre message d'erreur. `vercel dev` le ferait, mais il
exige une session Vercel.

```bash
npm run dev            # http://127.0.0.1:3000/expert.html
```

`scripts/serveur_local.mjs` sert le dépôt tel quel et confie toute adresse en
`/api/` au module correspondant, en lui présentant les mêmes `req` et `res`
qu'attend une fonction Vercel. Il lit `.env` : la clé OpenAI et
`VECTOR_STORE_ID`. Les modules d'`api/` sont rechargés à chaque requête, et rien
n'est mis en cache — on voit ce qu'on vient d'écrire.

⚠️ `VECTOR_STORE_ID` dans `.env` doit pointer sur le magasin que l'on veut
essayer. Il gardait longtemps l'ancien magasin de six fichiers, si bien que le
Q&R local répondait à côté pendant que la production allait bien.

## Éprouver le magasin avant de basculer

`essayer.mjs` pose cinq questions choisies pour n'avoir de réponse que dans ce
qui vient d'être ajouté — une journée de journal sans coordonnées, le journal de
Ronsard, la transcription de Hamelin, le glossaire, une fiche de toponyme — et
affiche pour chacune les documents que le modèle a consultés.

```bash
node rag/essayer.mjs                  # sur VECTOR_STORE_ID_V2
node rag/essayer.mjs vs_xxx "…"       # une question à soi
```

## Basculer le site sur le nouveau magasin

`indexer.mjs` écrit le nouvel identifiant dans `.env` sous **`VECTOR_STORE_ID_V2`**
et ne touche pas à `VECTOR_STORE_ID`. Tant que la variable Vercel n'a pas
changé, la production répond sur l'ancienne base.

Pour basculer :

1. Vercel → le projet → Settings → Environment Variables ;
2. `VECTOR_STORE_ID` ← la valeur de `VECTOR_STORE_ID_V2` ;
3. redéployer.

Pour revenir en arrière, remettre l'ancienne valeur : le premier magasin n'a pas
été supprimé.

## Quand le site change

Le corpus est une photographie. Après une modification des fiches, des données
ou des journaux, il faut refaire le tour :

```bash
.venv/bin/python rag/extraire_site.py
node rag/indexer.mjs
```

puis rebasculer la variable Vercel. Les anciens magasins peuvent être supprimés
depuis le tableau de bord OpenAI une fois le nouveau éprouvé.

## En cas d'indexation interrompue

`indexer.mjs` tient un journal de bord dans `rag/derniere_indexation.json` :
le magasin visé, les lots passés, les lots tombés. Pour compléter un magasin
sans tout renvoyer :

```bash
node rag/indexer.mjs --reprendre vs_xxxxxxxx
```
