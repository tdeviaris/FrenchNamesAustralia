# Migration vers l’API Responses (OpenAI)

Ce répertoire contient le nécessaire pour remplacer l’ancienne intégration **Assistants API** par la nouvelle **Responses API**.

## Variables d’environnement

- `OPENAI_API_KEY` : clé API OpenAI (backend uniquement)
- `VECTOR_STORE_ID` : id du Vector Store utilisé par `file_search`

## Setup du Vector Store

1. Exporter la clé :
   - `export OPENAI_API_KEY="..."`
2. Lancer :
   - `node responses/setup-vector-store.js`
3. Copier `VECTOR_STORE_ID` dans les variables d’environnement Vercel, puis redeployer.

## API (Vercel)

- Endpoint : `api/responses-chat.js`
- Frontend de test : `expert2.html`

