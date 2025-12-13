# Assistant IA - Toponymes Français en Australie

Ce répertoire contient tous les fichiers nécessaires à la configuration et au fonctionnement de l'assistant IA expert en toponymes.

## Contenu du répertoire

- `scripts/setup-assistant.js` : Script de configuration de l'assistant OpenAI
- `Descriptif_fr.txt` : Description du projet en français
- `expedition_baudin.pdf` : Documentation sur l'expédition Baudin
- `expedition_dentrecasteaux.pdf` : Documentation sur l'expédition d'Entrecasteaux

## Configuration de l'assistant

### Prérequis

1. Clé API OpenAI configurée dans les variables d'environnement :
   ```bash
   export OPENAI_API_KEY="votre-clé-api"
   ```

### Installation

Lancer le script de configuration :
```bash
node scripts/setup-assistant.js
```

Ce script va :
1. Uploader les fichiers de la base de connaissance vers OpenAI (6 fichiers)
2. Créer un assistant avec file_search activé
3. Sauvegarder l'ID de l'assistant dans `.env`

### Fichiers de la base de connaissance

L'assistant a accès à :
- `data/baudin.json` : 602 toponymes de l'expédition Baudin (1800-1804)
- `data/entrecasteaux.json` : 68 toponymes de l'expédition d'Entrecasteaux (1791-1794)
- `Descriptif_fr.txt` : Description générale du projet
- `expedition_baudin.pdf` : Documentation détaillée sur l'expédition Baudin
- `expedition_dentrecasteaux.pdf` : Documentation détaillée sur l'expédition d'Entrecasteaux

## Format des liens

L'assistant utilise une syntaxe personnalisée pour les liens :

### Liens Wikipedia (personnes)
- **Lecture dans les JSON** : `$François Péron$François_Péron$`
- **Écriture par l'assistant** : `[François Péron]{François_Péron}`
- **Rendu dans expert.html** : Lien vers `https://fr.wikipedia.org/wiki/François_Péron` (ou .en selon la langue)

### Liens vers les lieux (cartes)
- **Lecture dans les JSON** : champs `code`, `frenchName`, `ausEName`
- **Écriture par l'assistant** : `[Cap Bruny]{Entre09}` ou `[Riviere Huon]{Entre17}`
- **Rendu dans expert.html** :
  - `[Cap Bruny]{Entre09}` → lien vers `map.html#09`
  - `[Riviere Huon]{Entre17}` → lien vers `map.html#17`

### Liens externes
- **Format** : `[texte]{https://url-complete.com}`
- **Rendu** : Lien externe standard avec `target="_blank"`

## Modèle utilisé

- **Actuel** : `gpt-4.1` (le plus performant supporté par Assistants API)
- **Température** : `0.3` (réduite pour minimiser les hallucinations)
- **Alternatives** : `gpt-4.1-mini`, `gpt-4.1-nano` (moins chers, à tester selon les besoins)

Pour changer de modèle, modifier la ligne 153 de `scripts/setup-assistant.js` puis relancer le script.

## Améliorations anti-hallucination (Déc 2024)

### Problèmes identifiés
- L'assistant inventait parfois des toponymes fictifs (ex: "Baie Péron", "Cap Plat", "Anse du Premier Janvier")
- Les codes de lieux étaient parfois incorrects, renvoyant vers le mauvais emplacement
- L'assistant créait des exemples au lieu de chercher dans sa base de connaissance

### Solutions mises en place

1. **Règle anti-hallucination absolue** :
   - Interdiction formelle d'inventer des toponymes
   - Obligation de vérifier chaque lieu via file_search avant de le citer
   - Instruction claire : dire "je ne sais pas" plutôt qu'inventer

2. **Vérification stricte des codes** :
   - Obligation de vérifier chaque code dans la base avant de l'utiliser
   - Format strict : "Entre" + numéro ou "Baudin" + numéro
   - Préférence donnée à l'absence de lien plutôt qu'à un code incorrect
   - Message clair : un code erroné détruit la confiance de l'utilisateur

3. **Réduction de la température** :
   - Passage de 0.7 à 0.3 pour réduire la créativité et favoriser la précision
   - Meilleure adhérence aux faits de la base de connaissance

### Tests recommandés après reconfiguration

1. "Donne-moi des exemples de toponymes commémoratifs"
   - **Attendu** : Recherche dans la base et cite des lieux réels avec codes vérifiés
   - **À éviter** : Invention de lieux fictifs

2. "Quel est le code du Cap Bruny ?"
   - **Attendu** : Entre09 (code exact vérifié dans la base)

3. "Cite-moi 5 lieux nommés d'après des personnes"
   - **Attendu** : Cherche dans la base et cite uniquement des lieux existants avec codes corrects

## Déploiement

Après toute modification de l'assistant, déployer sur Vercel :
```bash
vercel --prod
```

## Architecture

```
expert.html (interface chat)
    ↓ (appel API)
api/chat.js (serverless function Vercel)
    ↓ (Assistants API)
OpenAI Assistant
    ↓ (file_search RAG)
Base de connaissance (6 fichiers)
```

## Fonctionnalités

- Chat en temps réel avec streaming SSE
- Historique de conversation géré par OpenAI (threads)
- Recherche vectorielle dans la base de connaissance
- Deep links vers les cartes interactives
- Interface bilingue FR/EN
