#!/usr/bin/env node
// Point d'entree stdio, pour les clients MCP locaux qui ne parlent pas HTTP
// (Claude Desktop, Claude Code, la plupart des IDE). Le serveur est le meme :
// seul le transport change.
//
//   node mcp/bin/stdio.js
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';

import { createFrenchNamesMcpServer } from '../server.js';

// Rien ne doit etre ecrit sur la sortie standard : elle porte le protocole.
const server = createFrenchNamesMcpServer();
const transport = new StdioServerTransport();

await server.connect(transport);

for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, async () => {
    await server.close().catch(() => undefined);
    process.exit(0);
  });
}
