#!/usr/bin/env node
// Serveur de developpement pour le point d'entree MCP, sans Vercel.
//
// Il monte le meme handler que la fonction `api/mcp.js` deployee en production,
// derriere un serveur HTTP de la bibliotheque standard. Ce qui est verifie ici
// vaut donc pour la production : memes controles d'origine et d'hote, meme
// transport, memes outils.
//
//   node mcp/bin/http.js [--port 3333]
import { createServer } from 'node:http';

import handler from '../../api/mcp.js';

function parsePort(argv) {
  const index = argv.indexOf('--port');
  const value = index >= 0 ? Number(argv[index + 1]) : Number(process.env.PORT ?? 3333);
  if (!Number.isInteger(value) || value < 0 || value > 65535) {
    throw new Error(`Port invalide : ${argv[index + 1] ?? process.env.PORT}`);
  }
  return value;
}

// La fonction attend les commodites de Vercel : un corps deja analyse, et les
// aides `status()` et `json()` sur la reponse. On les fournit ici.
function adapt(req, res, body) {
  req.body = body ? JSON.parse(body) : undefined;
  res.status = (code) => {
    res.statusCode = code;
    return res;
  };
  res.json = (payload) => {
    res.setHeader('content-type', 'application/json');
    res.end(JSON.stringify(payload));
    return res;
  };
}

const port = parsePort(process.argv);

const server = createServer((req, res) => {
  if (!req.url.startsWith('/api/mcp')) {
    res.statusCode = 404;
    res.setHeader('content-type', 'application/json');
    res.end(JSON.stringify({ error: 'Utilisez /api/mcp' }));
    return;
  }

  let body = '';
  req.on('data', (chunk) => {
    body += chunk;
  });
  req.on('end', () => {
    try {
      adapt(req, res, body);
    } catch {
      res.statusCode = 400;
      res.setHeader('content-type', 'application/json');
      res.end(JSON.stringify({ error: 'Corps JSON invalide' }));
      return;
    }
    handler(req, res).catch((error) => {
      console.error('Echec de la requete MCP :', error);
      if (!res.headersSent) {
        res.statusCode = 500;
        res.end(JSON.stringify({ error: 'Erreur interne' }));
      }
    });
  });
});

server.listen(port, () => {
  const { port: bound } = server.address();
  console.log(`Serveur MCP French Names Australia`);
  console.log(`  Point d'entree : http://localhost:${bound}/api/mcp`);
  console.log(`  Inspecteur     : npx @modelcontextprotocol/inspector`);
  console.log(`  Arret          : Ctrl+C`);
});

for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => {
    server.close(() => process.exit(0));
  });
}
