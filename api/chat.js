// api/chat.js - Vercel Serverless Function
// Cette fonction gère les appels à l'API OpenAI Assistants avec RAG

import OpenAI from 'openai';

export default async function handler(req, res) {
  // Configuration CORS pour permettre les appels depuis GitHub Pages
  res.setHeader('Access-Control-Allow-Credentials', true);
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,OPTIONS,PATCH,DELETE,POST,PUT');
  res.setHeader('Access-Control-Allow-Headers', 'X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version');

  // Gérer les requêtes OPTIONS (preflight)
  if (req.method === 'OPTIONS') {
    res.status(200).end();
    return;
  }

  // Accepter uniquement les requêtes POST
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { message, threadId = null } = req.body;

    if (!message) {
      return res.status(400).json({ error: 'Message is required' });
    }

    // Vérifier les variables d'environnement
    const apiKey = process.env.OPENAI_API_KEY;
    const assistantId = process.env.ASSISTANT_ID;

    if (!apiKey) {
      return res.status(500).json({ error: 'OpenAI API key not configured' });
    }

    if (!assistantId) {
      return res.status(500).json({ error: 'Assistant ID not configured. Run setup-assistant.js first.' });
    }

    // Initialiser le client OpenAI
    const openai = new OpenAI({ apiKey });

    // Créer ou réutiliser un thread
    let currentThreadId = threadId;

    if (!currentThreadId) {
      const thread = await openai.beta.threads.create();
      currentThreadId = thread.id;
    }

    // Ajouter le message de l'utilisateur au thread
    await openai.beta.threads.messages.create(currentThreadId, {
      role: 'user',
      content: message
    });

    // Créer un run avec streaming
    const run = openai.beta.threads.runs.stream(currentThreadId, {
      assistant_id: assistantId
    });

    // Configuration du streaming SSE (Server-Sent Events)
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');

    // Envoyer le thread ID au client
    res.write(`data: ${JSON.stringify({ threadId: currentThreadId })}\n\n`);

    // Variables pour accumuler la réponse
    let fullResponse = '';

    // Gérer les événements du stream
    run.on('textDelta', (textDelta) => {
      const content = textDelta.value;
      if (content) {
        fullResponse += content;
        res.write(`data: ${JSON.stringify({ content })}\n\n`);
      }
    });

    run.on('error', (error) => {
      console.error('Stream error:', error);
      res.write(`data: ${JSON.stringify({ error: error.message })}\n\n`);
    });

    run.on('end', () => {
      res.write('data: [DONE]\n\n');
      res.end();
    });

    // Attendre que le stream se termine
    await run.finalRun();

  } catch (error) {
    console.error('Server error:', error);

    if (!res.headersSent) {
      res.status(500).json({
        error: 'Internal server error',
        message: error.message
      });
    } else {
      res.write(`data: ${JSON.stringify({ error: error.message })}\n\n`);
      res.write('data: [DONE]\n\n');
      res.end();
    }
  }
}
