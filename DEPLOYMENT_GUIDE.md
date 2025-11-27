# Guide de déploiement - Expert IA

Ce guide explique comment déployer la fonctionnalité "Expert IA" qui utilise l'API OpenAI avec Vercel.

## Prérequis

1. **Compte Vercel** (gratuit) : https://vercel.com/signup
2. **Clé API OpenAI** : https://platform.openai.com/api-keys
3. **Compte GitHub** (vous l'avez déjà)

## Étape 1 : Installer Vercel CLI (optionnel pour test local)

```bash
npm install -g vercel
```

## Étape 2 : Déployer sur Vercel

### Option A : Déploiement via interface web (RECOMMANDÉ - Plus simple)

1. **Se connecter à Vercel**
   - Allez sur https://vercel.com
   - Connectez-vous avec votre compte GitHub

2. **Importer le projet**
   - Cliquez sur "Add New" → "Project"
   - Sélectionnez votre repository GitHub "FrenchNamesAustralia"
   - Cliquez sur "Import"

3. **Configurer le projet**
   - Framework Preset: **Other** (site statique)
   - Root Directory: `./` (laisser par défaut)
   - Build Command: *laisser vide*
   - Output Directory: `./` (laisser par défaut)

4. **Ajouter la variable d'environnement**
   - Dans "Environment Variables", ajoutez :
     - **Name** : `OPENAI_API_KEY`
     - **Value** : Votre clé API OpenAI (commence par `sk-...`)
   - Cliquez sur "Add"

5. **Déployer**
   - Cliquez sur "Deploy"
   - Attendez quelques minutes
   - Vercel va vous donner une URL : `https://votre-projet.vercel.app`

6. **Mettre à jour expert.html**
   - Ouvrez `expert.html`
   - À la ligne 373, remplacez `VOTRE_URL_VERCEL` par l'URL que Vercel vous a donnée
   ```javascript
   const API_URL = window.location.hostname === 'localhost'
       ? 'http://localhost:3000/api/chat'
       : 'https://votre-projet-abc123.vercel.app/api/chat';
   ```
   - Sauvegardez et poussez sur GitHub
   - Vercel redéploiera automatiquement

### Option B : Déploiement via CLI

```bash
# Se connecter à Vercel
vercel login

# Déployer (première fois)
vercel

# Ajouter la clé API
vercel env add OPENAI_API_KEY

# Déployer en production
vercel --prod
```

## Étape 3 : Tester

1. Allez sur votre URL Vercel : `https://votre-projet.vercel.app/expert.html`
2. Posez une question dans le chat
3. Vous devriez voir une réponse apparaître progressivement

## Étape 4 : Garder GitHub Pages pour le site principal

Deux options :

### Option A : Tout sur Vercel (RECOMMANDÉ)
- Le site entier + l'API sont sur Vercel
- Plus simple à gérer
- URL unique

### Option B : GitHub Pages + Vercel API
- Site principal reste sur GitHub Pages
- API sur Vercel
- Dans `expert.html`, utilisez l'URL complète Vercel pour l'API

## Structure des fichiers

```
FrenchNamesAustralia/
├── api/
│   └── chat.js          ← Fonction serverless pour Vercel
├── expert.html           ← Page de chat
├── vercel.json          ← Configuration Vercel
├── package.json         ← Dépendances Node.js
└── ...autres fichiers
```

## Coûts

### Vercel (GRATUIT)
- 100 GB de bande passante par mois
- Fonctions serverless illimitées
- Largement suffisant pour votre usage

### OpenAI API
- **GPT-4o-mini** (recommandé) : ~0.002$ par 1000 tokens
- **GPT-4o** : ~0.03$ par 1000 tokens
- Exemple : 100 conversations de 10 échanges ≈ 1-2$

## Résolution de problèmes

### Erreur "OPENAI_API_KEY not configured"
- Vérifiez que vous avez ajouté la variable d'environnement sur Vercel
- Redéployez après l'ajout : `vercel --prod`

### Erreur CORS
- Vérifiez que `vercel.json` est bien présent
- Le fichier configure automatiquement CORS

### L'API ne répond pas
- Vérifiez l'URL dans `expert.html` ligne 373
- Ouvrez la console du navigateur (F12) pour voir les erreurs

### Réponses lentes
- Normal ! Le streaming prend quelques secondes pour commencer
- GPT-4o-mini est plus rapide que GPT-4o

## Sécurité

✅ **BON** : Clé API sur Vercel (serveur)
❌ **MAUVAIS** : Clé API dans le code JavaScript (frontend)

La solution actuelle est **sécurisée** car :
- La clé API n'est jamais envoyée au navigateur
- Elle reste sur les serveurs Vercel
- Les utilisateurs ne peuvent pas la voir

## Mise à jour

Quand vous poussez des changements sur GitHub :
- Vercel redéploie automatiquement (si connecté via GitHub)
- Pas besoin de redéployer manuellement

## Support

Si vous avez des problèmes :
1. Vérifiez les logs sur Vercel : https://vercel.com/dashboard
2. Regardez la console du navigateur (F12)
3. Testez avec `vercel dev` en local

## Prochaines étapes (optionnel)

- Ajouter un historique de conversation persistant
- Personnaliser le prompt system pour votre GPT
- Ajouter des suggestions de questions
- Limiter le nombre de requêtes par IP (rate limiting)
