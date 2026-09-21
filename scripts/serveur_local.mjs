#!/usr/bin/env node
/**
 * Sert le site en local, fonctions comprises.
 *
 * Un simple serveur de fichiers ne suffit pas : la page du Q&R appelle
 * /api/responses-chat sur son propre hôte, et personne ne répond. `vercel dev`
 * le ferait, mais il exige une session Vercel et une configuration de projet.
 * Ce serveur-ci ne demande qu'un fichier .env avec la clé OpenAI et
 * l'identifiant du magasin — ceux-là mêmes que le site utilise en production.
 *
 * Il sert les fichiers du dépôt tels quels, et confie toute adresse commençant
 * par /api/ au module correspondant dans api/, en lui présentant les mêmes
 * req et res qu'attend une fonction Vercel.
 *
 *   node scripts/serveur_local.mjs            # http://127.0.0.1:3000
 *   node scripts/serveur_local.mjs 8080       # sur un autre port
 *
 * Les modules d'api/ sont rechargés à chaque requête : une modification prend
 * effet sans redémarrer. Les fichiers statiques ne sont jamais mis en cache,
 * pour que le navigateur ne serve pas une version d'hier.
 */

import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const RACINE = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const PORT = Number(process.argv[2] || 3000);

const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.geojson': 'application/json; charset=utf-8',
  '.md': 'text/markdown; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.gif': 'image/gif',
  '.webp': 'image/webp',
  '.avif': 'image/avif',
  '.ico': 'image/x-icon',
  '.mp3': 'audio/mpeg',
  '.m4a': 'audio/mp4',
  '.mp4': 'video/mp4',
  '.woff2': 'font/woff2',
  '.txt': 'text/plain; charset=utf-8',
  '.csv': 'text/csv; charset=utf-8',
  '.pdf': 'application/pdf',
};

function chargeEnv() {
  for (const nom of ['.env.local', '.env']) {
    const chemin = path.join(RACINE, nom);
    if (!fs.existsSync(chemin)) continue;
    for (const ligne of fs.readFileSync(chemin, 'utf-8').split('\n')) {
      const m = ligne.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$/);
      if (m && !process.env[m[1]]) process.env[m[1]] = m[2].replace(/^["']|["']$/g, '');
    }
  }
}

/** Lit le corps d'une requête et le rend en objet, comme le fait Vercel. */
function litLeCorps(req) {
  return new Promise((resolve) => {
    let brut = '';
    req.on('data', (bout) => { brut += bout; });
    req.on('end', () => {
      try {
        resolve(brut ? JSON.parse(brut) : {});
      } catch {
        resolve({});
      }
    });
  });
}

/**
 * Complète l'objet réponse de Node avec ce qu'une fonction Vercel attend :
 * status(), json(), et un headersSent fiable.
 */
function habilleLaReponse(res) {
  res.status = (code) => { res.statusCode = code; return res; };
  res.json = (objet) => {
    if (!res.headersSent) res.setHeader('Content-Type', 'application/json; charset=utf-8');
    res.end(JSON.stringify(objet));
    return res;
  };
  return res;
}

async function serviceApi(req, res, cheminApi) {
  const module = path.join(RACINE, 'api', cheminApi + '.js');
  if (!fs.existsSync(module)) {
    res.statusCode = 404;
    res.end('Fonction inconnue : api/' + cheminApi + '.js');
    return;
  }
  // Le suffixe force un rechargement : sans lui, Node garderait la version
  // chargée au premier appel et l'on croirait ses corrections sans effet.
  const url = pathToFileURL(module).href + '?t=' + Date.now();
  const { default: handler } = await import(url);

  req.body = await litLeCorps(req);
  habilleLaReponse(res);
  await handler(req, res);
}

function serviceFichier(req, res, chemin) {
  let relatif = decodeURIComponent(chemin.split('?')[0]);
  if (relatif === '/') relatif = '/index.html';
  const absolu = path.join(RACINE, relatif);

  // On ne sort pas du dépôt, quoi que demande l'adresse.
  if (!absolu.startsWith(RACINE)) {
    res.statusCode = 403;
    res.end('Interdit');
    return;
  }
  if (!fs.existsSync(absolu) || fs.statSync(absolu).isDirectory()) {
    res.statusCode = 404;
    res.end('Introuvable : ' + relatif);
    return;
  }
  res.setHeader('Content-Type', TYPES[path.extname(absolu).toLowerCase()] || 'application/octet-stream');
  // Jamais de cache : on développe, on veut voir ce qu'on vient d'écrire.
  res.setHeader('Cache-Control', 'no-store');
  fs.createReadStream(absolu).pipe(res);
}

chargeEnv();

if (!process.env.OPENAI_API_KEY || !process.env.VECTOR_STORE_ID) {
  console.error('❌ OPENAI_API_KEY ou VECTOR_STORE_ID manquante dans .env');
  console.error('   Le site s’affichera, mais le Q&R restera muet.');
}

http.createServer(async (req, res) => {
  const debut = Date.now();
  try {
    if (req.url.startsWith('/api/')) {
      const nom = req.url.slice(5).split('?')[0];
      await serviceApi(req, res, nom);
    } else {
      serviceFichier(req, res, req.url);
    }
  } catch (erreur) {
    console.error('❌', req.url, erreur?.message || erreur);
    if (!res.headersSent) res.statusCode = 500;
    res.end('Erreur : ' + (erreur?.message || erreur));
  } finally {
    const duree = Date.now() - debut;
    if (req.url.startsWith('/api/')) console.log(`   ${req.method} ${req.url} — ${duree} ms`);
  }
}).listen(PORT, '127.0.0.1', () => {
  console.log(`\n🌐 http://127.0.0.1:${PORT}/expert.html`);
  console.log(`   magasin : ${process.env.VECTOR_STORE_ID || '(absent)'}`);
  console.log('   Ctrl-C pour arrêter.\n');
});
