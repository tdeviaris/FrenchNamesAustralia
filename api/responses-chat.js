// api/responses-chat.js - Vercel Serverless Function
// Migration Assistants API -> Responses API (streaming SSE + file_search)

import OpenAI from 'openai';
import { TOPONYMES_INSTRUCTIONS } from '../responses/instructions.js';

const ALLOWED_ORIGINS = [
  'https://french-names-australia.vercel.app',
  'https://www.frenchplacenames.au',
  'https://frenchplacenames.au',
  'https://www.frenchplacenames.com',
  'https://frenchplacenames.com',
];

export default async function handler(req, res) {
  const origin = req.headers.origin;
  const corsOrigin = ALLOWED_ORIGINS.includes(origin) ? origin : ALLOWED_ORIGINS[0];
  res.setHeader('Access-Control-Allow-Origin', corsOrigin);
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    res.status(200).end();
    return;
  }

  if (req.method !== 'POST') {
    res.status(405).json({ error: 'Method not allowed' });
    return;
  }

  let stream = null;
  try {
    const { message, responseId = null, language = 'en' } = req.body || {};

    if (!message) {
      res.status(400).json({ error: 'Message is required' });
      return;
    }

    const apiKey = process.env.OPENAI_API_KEY;
    const vectorStoreId = process.env.VECTOR_STORE_ID;

    if (!apiKey) {
      res.status(500).json({ error: 'OpenAI API key not configured' });
      return;
    }

    if (!vectorStoreId) {
      res.status(500).json({
        error: 'VECTOR_STORE_ID not configured. Run responses/setup-vector-store.js then set it on Vercel.',
      });
      return;
    }

    const languagePrefix =
      language === 'fr'
        ? '[IMPORTANT: Réponds UNIQUEMENT en français, même si la question est en anglais] '
        : '[IMPORTANT: Answer ONLY in English, even if the question is in French] ';

    const messageWithLanguage = languagePrefix + message;

    const openai = new OpenAI({ apiKey });

    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');
    stream = openai.responses.stream({
      // Mesuré sur le corpus complet (voir rag/departager.mjs) : sur six
      // épreuves, terra produit deux fois moins de liens morts que gpt-5.4-mini
      // et ne laisse jamais fuir de marqueur de citation. Il coûte 0,8 seconde
      // de plus avant le premier mot — le reste s'écrit sous les yeux du
      // lecteur, qui ne l'attend donc pas.
      model: 'gpt-5.6-terra',
      instructions: TOPONYMES_INSTRUCTIONS,
      input: messageWithLanguage,
      previous_response_id: responseId,
      store: true,
      // Un effort plus soutenu n'améliore pas les réponses ici, et allonge la
      // queue de distribution : jusqu'à douze secondes de silence initial.
      // Les modèles à raisonnement refusent temperature.
      reasoning: { effort: 'low' },
      tools: [
        {
          type: 'file_search',
          vector_store_ids: [vectorStoreId],
          max_num_results: 20,
        },
      ],
    });

    req.on('close', () => {
      try {
        stream?.abort();
      } catch {
        // ignore
      }
    });

    // L'identifiant n'est PLUS envoye a l'ouverture. Une reponse longue depasse
    // parfois la minute que Vercel accorde a la fonction : elle est alors tuee
    // en pleine phrase, et OpenAI, qui ne l'a jamais vue s'achever, ne
    // l'enregistre pas. Le navigateur, lui, avait deja note l'identifiant et
    // s'y accrochait a chaque question suivante -- qui recevait un 400
    // « Previous response not found ». Le fil etait mort, et le rechargement
    // n'y changeait rien puisque l'identifiant survivait dans le stockage local.
    //
    // On ne l'envoie donc qu'une fois la reponse menee a terme, plus bas. Une
    // reponse coupee ne laisse aucune trace : la question suivante repart du
    // dernier echange valide.

    stream.on('response.output_text.delta', (event) => {
      const content = event?.delta;
      if (content) {
        res.write(`data: ${JSON.stringify({ content })}\n\n`);
      }
    });

    stream.on('error', (error) => {
      console.error('Stream error:', error);
      res.write(`data: ${JSON.stringify({ error: error.message })}\n\n`);
    });

    const finale = await stream.finalResponse();

    // Seule une reponse achevee et enregistree cote OpenAI peut servir de
    // maillon a la suivante.
    if (finale?.status === 'completed' && finale?.id) {
      res.write(`data: ${JSON.stringify({ responseId: finale.id })}\n\n`);
    }
    res.write('data: [DONE]\n\n');
    res.end();
  } catch (error) {
    console.error('Server error:', error);

    if (!res.headersSent) {
      res.status(500).json({ error: 'Internal server error', message: error?.message });
      return;
    }

    res.write(`data: ${JSON.stringify({ error: error?.message || 'Internal server error' })}\n\n`);
    res.write('data: [DONE]\n\n');
    res.end();
  }
}
