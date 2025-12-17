// api/responses-chat.js - Vercel Serverless Function
// Migration Assistants API -> Responses API (streaming SSE + file_search)

import OpenAI from 'openai';
import { TOPONYMES_INSTRUCTIONS } from '../responses/instructions.js';

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Credentials', true);
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,OPTIONS,PATCH,DELETE,POST,PUT');
  res.setHeader(
    'Access-Control-Allow-Headers',
    'X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version',
  );

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
      model: 'gpt-4.1',
      instructions: TOPONYMES_INSTRUCTIONS,
      input: messageWithLanguage,
      previous_response_id: responseId,
      store: true,
      temperature: 0.3,
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

    stream.on('response.created', (event) => {
      const createdId = event?.response?.id;
      if (createdId) {
        res.write(`data: ${JSON.stringify({ responseId: createdId })}\n\n`);
      }
    });

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

    stream.on('end', () => {
      res.write('data: [DONE]\n\n');
      res.end();
    });

    await stream.finalResponse();
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
