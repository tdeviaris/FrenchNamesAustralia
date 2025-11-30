# Assistant IA - Toponymes Français en Australie

Ce répertoire contient tous les fichiers nécessaires à la configuration et au fonctionnement de l'assistant IA expert en toponymes.

## Contenu du répertoire

- `setup-assistant.js` : Script de configuration de l'assistant OpenAI
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
node assistant/setup-assistant.js
```

Ce script va :
1. Uploader les fichiers de la base de connaissance vers OpenAI (5 fichiers)
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
  - `[Cap Bruny]{Entre09}` → lien vers `map_dentrecasteaux.html#09`
  - `[Riviere Huon]{Entre17}` → lien vers `map_dentrecasteaux.html#17`

### Liens externes
- **Format** : `[texte]{https://url-complete.com}`
- **Rendu** : Lien externe standard avec `target="_blank"`

## Modèle utilisé

- **Actuel** : `gpt-4.1` (le plus performant supporté par Assistants API)
- **Alternatives** : `gpt-4.1-mini`, `gpt-4.1-nano` (moins chers, à tester selon les besoins)

Pour changer de modèle, modifier la ligne 128 de `setup-assistant.js` puis relancer le script.

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
Base de connaissance (5 fichiers)
```

## Fonctionnalités

- Chat en temps réel avec streaming SSE
- Historique de conversation géré par OpenAI (threads)
- Recherche vectorielle dans la base de connaissance
- Deep links vers les cartes interactives
- Interface bilingue FR/EN
