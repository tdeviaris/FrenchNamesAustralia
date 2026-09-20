import assert from 'node:assert/strict';
import test from 'node:test';

import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { InMemoryTransport } from '@modelcontextprotocol/sdk/inMemory.js';

import { createFrenchNamesMcpServer } from '../../mcp/server.js';

async function withClient(callback) {
  const server = createFrenchNamesMcpServer();
  const client = new Client({ name: 'fna-test-client', version: '1.0.0' });
  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
  await Promise.all([server.connect(serverTransport), client.connect(clientTransport)]);
  try {
    await callback(client);
  } finally {
    await client.close();
    await server.close();
  }
}

test('MCP server exposes the six read-only tools', async () => {
  await withClient(async (client) => {
    const response = await client.listTools();
    const names = response.tools.map((tool) => tool.name).sort();
    assert.deepEqual(names, [
      'analyze_toponyms',
      'find_nearby_toponyms',
      'get_dataset_summary',
      'get_toponym',
      'search_timeline',
      'search_toponyms',
    ]);
    assert.ok(response.tools.every((tool) => tool.annotations?.readOnlyHint === true));
  });
});

test('MCP tool call returns structured exhaustive statistics', async () => {
  await withClient(async (client) => {
    const response = await client.callTool({
      name: 'analyze_toponyms',
      arguments: { groupBy: ['expedition'] },
    });
    assert.equal(response.isError, undefined);
    assert.equal(response.structuredContent.recordsScanned, 671);
    assert.equal(response.structuredContent.recordsAnalyzed, 671);
    assert.equal(response.structuredContent.truncated, false);
    assert.equal(response.structuredContent.groups.length, 2);
  });
});

test('MCP resources expose dataset metadata and complete records', async () => {
  await withClient(async (client) => {
    const templates = await client.listResourceTemplates();
    assert.ok(
      templates.resourceTemplates.some(
        (template) => template.uriTemplate === 'fna://toponyms/{code}/{language}',
      ),
    );

    const response = await client.readResource({ uri: 'fna://toponyms/Baudin001/both' });
    const record = JSON.parse(response.contents[0].text);
    assert.equal(record.code, 'Baudin001');
    assert.ok(record.characteristic_fr.length > 500);
    assert.ok(record.history.length > 1000);
  });
});
