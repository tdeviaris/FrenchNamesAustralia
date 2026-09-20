# L’API Responses (OpenAI)

Ce répertoire porte l’intégration **Responses API** qui a remplacé l’ancienne
**Assistants API**.

## Variables d’environnement

- `OPENAI_API_KEY` : clé API OpenAI (backend uniquement)
- `VECTOR_STORE_ID` : id du Vector Store utilisé par `file_search`

## Setup du Vector Store

`setup-vector-store.js` construisait une base de six fichiers : les deux JSON de
toponymes, deux textes et deux PDF de présentation. **Il est dépassé.**

La base de connaissance est désormais fabriquée par `rag/`, qui indexe
l’intégralité du site — 483 fiches détaillées, glossaire, méthodologie, données
— et les journaux de bord, y compris ceux qui ne viennent pas du site :
transcriptions du Baudin Legacy Project, journal de Hamelin, récit publié de
Flinders. Soit 1 841 fichiers au lieu de 6.

Voir **[rag/README.md](../rag/README.md)**.

```bash
npm run rag:corpus     # refabrique le corpus depuis le site et les sources
npm run rag:essai      # compte, n'envoie rien
npm run rag:indexer    # crée un magasin neuf et l'emplit
```

`setup-vector-store.js` reste en place pour mémoire, et parce qu’il sert de
recours si l’on veut revenir à une base minuscule pour un essai.

## API (Vercel)

- Endpoint : `api/responses-chat.js`
- Instructions du modèle : `responses/instructions.js`
- Frontend : `expert.html`
