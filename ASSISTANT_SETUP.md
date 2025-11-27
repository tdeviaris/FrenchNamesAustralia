# Migration vers l'API Assistants OpenAI avec RAG

Ce guide vous explique comment configurer l'Assistant OpenAI avec la base de connaissance pour votre site de toponymes.

## 📋 Prérequis

- Node.js installé (v18 ou supérieur)
- Une clé API OpenAI
- Accès au projet Vercel

## 🚀 Installation - Étape par étape

### 1. Installer les dépendances

```bash
npm install
```

Cela installera le SDK OpenAI (version 4.73.0 ou supérieure).

### 2. Configurer la clé API OpenAI

Créez un fichier `.env` à la racine du projet (s'il n'existe pas déjà) :

```bash
OPENAI_API_KEY=sk-votre-clé-api-ici
```

⚠️ **Important** : Ne commitez JAMAIS ce fichier dans Git. Il est déjà dans `.gitignore`.

### 3. Uploader la base de connaissance et créer l'Assistant

Exécutez le script de configuration :

```bash
npm run setup-assistant
```

Ce script va :
- ✅ Uploader les 3 fichiers de la base de connaissance vers OpenAI
  - `data/baudin.json`
  - `data/entrecasteaux.json`
  - `Descriptif_fr.txt`
- ✅ Créer un Vector Store avec ces fichiers
- ✅ Créer un Assistant configuré avec `file_search` (RAG)
- ✅ Sauvegarder l'`ASSISTANT_ID` dans `.env`

**Résultat attendu** :

```
🚀 Début de la configuration de l'Assistant Toponymes...

📤 Upload des fichiers de la base de connaissance...
  ✅ baudin.json uploadé (ID: file-xxx)
  ✅ entrecasteaux.json uploadé (ID: file-yyy)
  ✅ Descriptif_fr.txt uploadé (ID: file-zzz)

✅ 3 fichiers uploadés avec succès

🗄️  Création du Vector Store...
✅ Vector Store créé (ID: vs-xxx)

⏳ Indexation des fichiers en cours...
  📊 Fichiers: 3/3 indexés
✅ Indexation terminée

🤖 Création de l'Assistant...
✅ Assistant créé (ID: asst-xxx)

💾 Sauvegarde de la configuration...
✅ Configuration sauvegardée dans .env

════════════════════════════════════════════════════════════
✅ Configuration terminée avec succès !
════════════════════════════════════════════════════════════
```

### 4. Configurer Vercel

Vous devez ajouter les variables d'environnement dans Vercel :

#### Option A : Via le CLI Vercel

```bash
vercel env add OPENAI_API_KEY
# Coller votre clé API

vercel env add ASSISTANT_ID
# Coller l'Assistant ID affiché par le script setup
```

#### Option B : Via le Dashboard Vercel

1. Allez sur https://vercel.com/dashboard
2. Sélectionnez votre projet
3. Allez dans **Settings** → **Environment Variables**
4. Ajoutez :
   - `OPENAI_API_KEY` = `sk-votre-clé`
   - `ASSISTANT_ID` = `asst-xxx` (l'ID affiché par le script)

### 5. Déployer sur Vercel

```bash
npm run deploy
```

## 🧪 Tester en local

Avant de déployer, vous pouvez tester localement :

```bash
npm run dev
```

Puis ouvrez http://localhost:3000/expert.html

## 📊 Différences avec l'ancienne implémentation

### Avant (Chat Completions API)
- ❌ Pas de base de connaissance
- ❌ Seulement un prompt système générique
- ❌ Pas de RAG (Retrieval Augmented Generation)
- ⚠️ Historique géré côté client (variable `conversationHistory`)

### Maintenant (Assistants API)
- ✅ Base de connaissance complète (3 fichiers)
- ✅ RAG activé avec `file_search`
- ✅ Recherche vectorielle dans les documents
- ✅ Historique géré par OpenAI (via `threadId`)
- ✅ Réponses basées sur vos données réelles

## 🔍 Comment ça fonctionne

### Architecture

```
Frontend (expert.html)
    ↓
    Envoie: { message, threadId }
    ↓
Vercel Function (api/chat.js)
    ↓
    Crée/réutilise un Thread
    ↓
OpenAI Assistant API
    ↓
    Recherche dans Vector Store (RAG)
    ↓
    Génère réponse avec GPT-4o
    ↓
Streaming SSE vers le client
```

### Gestion des conversations

Chaque conversation crée un **Thread** OpenAI qui :
- Stocke l'historique automatiquement
- Permet la recherche dans la base de connaissance
- Persiste tant que le thread existe

Le `threadId` est maintenu côté client et envoyé à chaque requête.

## 💰 Coûts

### Upload et stockage
- Upload initial : ~gratuit (fichiers < 1 Mo)
- Stockage Vector Store : ~0.10$ / Go / jour

### Utilisation
- GPT-4o : ~0.005$ / 1K tokens en entrée, ~0.015$ / 1K tokens en sortie
- File search : ~0.10$ / assistant / jour (actif)

**Estimation** : Pour un usage modéré (100-200 questions/jour), environ 5-10$ / mois.

## 🔧 Maintenance

### Mettre à jour la base de connaissance

Si vous modifiez les fichiers JSON ou le Descriptif.txt :

```bash
# Re-exécuter le script de setup
npm run setup-assistant

# Redéployer
npm run deploy
```

Le script créera un nouvel Assistant avec les fichiers mis à jour.

### Supprimer l'ancien Assistant

Pour éviter les coûts de stockage, supprimez les anciens assistants via :

```bash
# Lister les assistants
curl https://api.openai.com/v1/assistants \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "OpenAI-Beta: assistants=v2"

# Supprimer un assistant
curl https://api.openai.com/v1/assistants/asst-xxx \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "OpenAI-Beta: assistants=v2" \
  -X DELETE
```

## ❓ Dépannage

### Erreur : "Assistant ID not configured"

L'`ASSISTANT_ID` n'est pas défini dans Vercel. Vérifiez :
1. Le script `setup-assistant` a bien tourné
2. La variable est ajoutée dans Vercel (`vercel env ls`)

### Erreur : "File not found"

Vérifiez que les 3 fichiers existent :
- `data/baudin.json`
- `data/entrecasteaux.json`
- `Descriptif_fr.txt`

### Réponses vides ou erreurs de streaming

Vérifiez les logs Vercel :
```bash
vercel logs
```

## 📚 Documentation OpenAI

- [Assistants API](https://platform.openai.com/docs/assistants/overview)
- [File Search](https://platform.openai.com/docs/assistants/tools/file-search)
- [Vector Stores](https://platform.openai.com/docs/api-reference/vector-stores)

---

**Prochaines étapes** : Après avoir tout configuré, testez avec des questions comme :
- "Combien de toponymes ont été nommés par Baudin ?"
- "Quels sont les noms liés à l'expédition d'Entrecasteaux en Tasmanie ?"
- "Qui était François Péron ?"

L'Assistant devrait maintenant chercher dans vos documents pour répondre avec précision !
