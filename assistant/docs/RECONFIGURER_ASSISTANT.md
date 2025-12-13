# 🔧 Guide : Reconfigurer l'assistant IA

## ⚠️ Important à savoir

Les modifications du prompt de l'assistant ont été faites dans le fichier `scripts/setup-assistant.js` et committées sur GitHub.

**MAIS** : Ces modifications ne sont **PAS encore actives** sur le site en ligne !

Pour que les changements prennent effet, vous devez **recréer l'assistant** sur OpenAI.

## 📝 Étapes pour activer les améliorations

### 1. Préparer votre environnement

Ouvrez un terminal et allez dans le dossier du projet :
```bash
cd ~/Desktop/Toponymes/FrenchNamesAustralia
```

### 2. Définir votre clé API OpenAI

```bash
export OPENAI_API_KEY=votre_clé_api_openai
```

💡 **Où trouver votre clé API** : https://platform.openai.com/api-keys

### 3. Exécuter le script de reconfiguration

```bash
node scripts/setup-assistant.js
```

Le script va :
- ✅ Uploader les 6 fichiers de la base de connaissance vers OpenAI
- ✅ Créer un **nouvel** assistant avec les nouvelles instructions anti-hallucination
- ✅ Sauvegarder automatiquement le nouvel ID dans `.env`

### 4. Déployer sur Vercel

```bash
vercel --prod
```

Cela met à jour la fonction serverless avec le nouvel ID d'assistant.

### 5. Tester les améliorations

Allez sur votre site et testez l'assistant avec ces questions :

#### Test 1 : Exemples de catégories
**Question** : "Donne-moi des exemples de toponymes commémoratifs"

**Avant** (comportement à éviter) :
> - Personne : Baie Péron
> - Descriptif : Cap Plat
> - Animal : Ile aux Mouettes
> - Lieu français : Anse de Normandie

**Après** (comportement attendu) :
> L'assistant cherche dans sa base et cite des lieux **réels** avec leurs **vrais codes**, par exemple :
> - [Cap Bruny]{Entre09}
> - [Rivière Huon]{Entre17}

#### Test 2 : Code d'un lieu
**Question** : "Quel est le code du Cap Bruny ?"

**Attendu** : `Entre09` (vérifié dans la base)

#### Test 3 : Lieux nommés d'après des personnes
**Question** : "Cite-moi 5 lieux nommés d'après des personnes"

**Attendu** : L'assistant cite uniquement des lieux existants dans sa base, avec leurs codes corrects.

## 🧹 Nettoyer les anciens assistants (optionnel mais recommandé)

Chaque fois que vous exécutez `setup-assistant.js`, un **nouvel** assistant est créé sur OpenAI.

Les anciens assistants restent actifs et **consomment des ressources** (donc de l'argent).

### Comment supprimer les anciens assistants

1. Allez sur https://platform.openai.com/assistants
2. Vous verrez tous vos assistants "Expert Toponymes"
3. Supprimez les anciens (gardez uniquement le plus récent)

## ❓ En cas de problème

### L'assistant ne répond pas

Vérifiez que :
1. Le fichier `.env` contient bien `ASSISTANT_ID=asst_...`
2. Vercel a bien les variables d'environnement :
   ```bash
   vercel env ls
   ```

### L'assistant hallucine toujours

1. Vérifiez que vous utilisez bien le **nouvel** assistant (celui créé après les modifications)
2. Testez avec des questions très précises pour forcer la recherche dans la base
3. Si le problème persiste, contactez-moi pour affiner davantage le prompt

## 📊 Changements techniques appliqués

1. **Température réduite** : 0.7 → 0.3 (moins de créativité, plus de précision)
2. **Règles anti-hallucination** : Interdiction formelle d'inventer des toponymes
3. **Vérification des codes** : Obligation de chercher via file_search avant de citer un code
4. **Instructions claires** : "Je ne sais pas" est préférable à inventer

## 💰 Coûts

La reconfiguration crée un nouvel assistant mais ne coûte rien en soi.

Les coûts viennent de :
- Utilisation de l'assistant (nombre de questions/réponses)
- Stockage des fichiers dans OpenAI
- Anciens assistants non supprimés

💡 **Astuce** : Supprimez les anciens assistants pour éviter les frais de stockage inutiles.
