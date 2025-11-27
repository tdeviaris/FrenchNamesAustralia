// api/chat.js - Vercel Serverless Function
// Cette fonction gère les appels à l'API OpenAI

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
    const { message, conversationHistory = [] } = req.body;

    if (!message) {
      return res.status(400).json({ error: 'Message is required' });
    }

    // Récupérer la clé API depuis les variables d'environnement
    const apiKey = process.env.OPENAI_API_KEY;

    if (!apiKey) {
      return res.status(500).json({ error: 'OpenAI API key not configured' });
    }

    // Préparer les messages pour l'API OpenAI
    const messages = [
      {
        role: 'system',
        content: `Tu es un expert spécialisé dans les toponymes français le long de la côte australienne, particulièrement ceux issus des expéditions de d'Entrecasteaux (1791-1794) et Baudin (1800-1804).

Tu as une connaissance approfondie de :
- L'histoire des expéditions françaises en Australie
- Les 670 toponymes documentés dans les atlas officiels
- Les explorateurs, scientifiques et membres d'équipage
- Les cartes historiques et documents d'archives
- Le contexte géopolitique de l'époque (Révolution française, Empire napoléonien)
- Les relations avec les peuples aborigènes

Réponds de manière précise, informative et pédagogique. Cite des noms de lieux spécifiques quand c'est pertinent. Si tu ne connais pas une information précise, dis-le honnêtement.`
      },
      ...conversationHistory,
      {
        role: 'user',
        content: message
      }
    ];

    // Appel à l'API OpenAI avec streaming
    const response = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey}`
      },
      body: JSON.stringify({
        model: 'gpt-4o-mini', // Modèle économique mais performant
        messages: messages,
        temperature: 0.7,
        max_tokens: 1500,
        stream: true
      })
    });

    if (!response.ok) {
      const error = await response.json();
      console.error('OpenAI API error:', error);
      return res.status(response.status).json({ error: error.error?.message || 'OpenAI API error' });
    }

    // Configuration du streaming SSE (Server-Sent Events)
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');

    // Lire le stream de réponse d'OpenAI
    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        res.write('data: [DONE]\n\n');
        res.end();
        break;
      }

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n').filter(line => line.trim() !== '');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);

          if (data === '[DONE]') {
            res.write('data: [DONE]\n\n');
            continue;
          }

          try {
            const parsed = JSON.parse(data);
            const content = parsed.choices[0]?.delta?.content;

            if (content) {
              // Envoyer le chunk au client
              res.write(`data: ${JSON.stringify({ content })}\n\n`);
            }
          } catch (e) {
            // Ignorer les erreurs de parsing
            console.error('Parse error:', e);
          }
        }
      }
    }
  } catch (error) {
    console.error('Server error:', error);

    if (!res.headersSent) {
      res.status(500).json({
        error: 'Internal server error',
        message: error.message
      });
    }
  }
}
