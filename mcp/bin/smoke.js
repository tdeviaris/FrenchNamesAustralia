#!/usr/bin/env node
// Appelle chaque outil et chaque ressource une fois, et rend compte. Sert a
// verifier d'un coup d'oeil qu'un client obtiendra bien des reponses, et a
// mesurer ce que chacune pese dans une fenetre de contexte.
//
//   node mcp/bin/smoke.js            (en memoire, sans reseau)
//   node mcp/bin/smoke.js --url http://localhost:3333/api/mcp
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { InMemoryTransport } from '@modelcontextprotocol/sdk/inMemory.js';
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js';

import { createFrenchNamesMcpServer } from '../server.js';

const urlIndex = process.argv.indexOf('--url');
const url = urlIndex >= 0 ? process.argv[urlIndex + 1] : null;

const CALLS = [
  ['get_dataset_summary', {}, (r) => `${r.toponyms} toponymes, ${r.routePositions} positions, ${r.journalEntries} jours de journal`],
  ['search_toponyms', { query: 'Péron', language: 'fr' }, (r) => `${r.total} résultats, 1er : ${r.items[0]?.frenchName}`],
  ['get_toponym', { code: 'Flinders009' }, (r) => `${r.frenchName} — attribué à ${r.attribution?.sujet ?? '(non attribué)'}`],
  ['find_nearby_toponyms', { latitude: -35.0, longitude: 137.5, radiusKm: 50 }, (r) => `${r.totalMatches} dans 50 km`],
  ['analyze_toponyms', { groupBy: ['expedition'] }, (r) => r.groups.map((g) => `${g.dimensions.expedition} ${g.count}`).join(', ')],
  ['search_route_positions', { vessel: 'le Géographe' }, (r) => `${r.total} relevés placent le Géographe`],
  ['get_route_summary', { groupBy: ['coque'] }, (r) => r.groups.map((g) => `${g.dimensions.coque} ${g.count}`).join(', ')],
  ['search_journals', { query: 'mouillage', limit: 3 }, (r) => `${r.total} jours de journal`],
  ['get_journal_day', { date: '1802-04-08' }, (r) => `${r.entries.length} sources, ${r.routePositions.length} positions`],
  ['search_timeline', { language: 'fr', limit: 3 }, (r) => `${r.total} évènements`],
  ['list_remarkable_dates', { expedition: 'Flinders' }, (r) => `${r.total} jalons`],
];

const RESOURCES = [
  'fna://dataset/summary',
  'fna://toponyms/Baudin001/both',
  'fna://routes/Entrecasteaux',
  'fna://journals/1802-04-08',
];

function ko(text) {
  return `${Math.round(text.length / 1024)} Ko`;
}

async function connect() {
  const client = new Client({ name: 'fna-smoke', version: '1.0.0' });
  if (url) {
    await client.connect(new StreamableHTTPClientTransport(new URL(url)));
    return { client, label: url };
  }
  const server = createFrenchNamesMcpServer();
  const [clientSide, serverSide] = InMemoryTransport.createLinkedPair();
  await Promise.all([server.connect(serverSide), client.connect(clientSide)]);
  return { client, label: 'en mémoire', server };
}

const { client, label, server } = await connect();
console.log(`Serveur : ${label}\n`);

const tools = await client.listTools();
console.log(`${tools.tools.length} outils déclarés\n`);

let failures = 0;

for (const [name, args, describe] of CALLS) {
  const started = Date.now();
  try {
    const response = await client.callTool({ name, arguments: args });
    if (response.isError) throw new Error(response.content?.[0]?.text ?? 'isError');
    const text = response.content[0].text;
    const payload = JSON.parse(text);
    console.log(
      `  ok   ${name.padEnd(23)} ${String(Date.now() - started).padStart(4)} ms  ${ko(text).padStart(7)}  ${describe(payload)}`,
    );
  } catch (error) {
    failures += 1;
    console.log(`  ÉCHEC ${name.padEnd(23)} ${error.message}`);
  }
}

console.log();
for (const uri of RESOURCES) {
  try {
    const response = await client.readResource({ uri });
    console.log(`  ok   ${uri.padEnd(34)} ${ko(response.contents[0].text).padStart(7)}`);
  } catch (error) {
    failures += 1;
    console.log(`  ÉCHEC ${uri.padEnd(34)} ${error.message}`);
  }
}

await client.close();
await server?.close();

console.log(`\n${failures ? `${failures} échec(s)` : 'Tout répond.'}`);
process.exit(failures ? 1 : 0);
