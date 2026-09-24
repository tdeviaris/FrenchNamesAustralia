import assert from 'node:assert/strict';
import test from 'node:test';

import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { InMemoryTransport } from '@modelcontextprotocol/sdk/inMemory.js';

import { TOPONYMS } from '../../mcp/data-store.js';
import { createFrenchNamesMcpServer } from '../../mcp/server.js';

function payload(response) {
  return JSON.parse(response.content[0].text);
}

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

test('MCP server exposes the eleven read-only tools', async () => {
  await withClient(async (client) => {
    const response = await client.listTools();
    const names = response.tools.map((tool) => tool.name).sort();
    assert.deepEqual(names, [
      'analyze_toponyms',
      'find_nearby_toponyms',
      'get_dataset_summary',
      'get_journal_day',
      'get_route_summary',
      'get_toponym',
      'list_remarkable_dates',
      'search_journals',
      'search_route_positions',
      'search_timeline',
      'search_toponyms',
    ]);
    assert.ok(response.tools.every((tool) => tool.annotations?.readOnlyHint === true));
  });
});

test('MCP tool call returns exhaustive statistics as compact JSON', async () => {
  await withClient(async (client) => {
    const response = await client.callTool({
      name: 'analyze_toponyms',
      arguments: { groupBy: ['expedition'] },
    });
    assert.equal(response.isError, undefined);
    const data = payload(response);
    assert.equal(data.recordsScanned, TOPONYMS.length);
    assert.equal(data.recordsAnalyzed, TOPONYMS.length);
    assert.equal(data.truncated, false);
    assert.equal(data.groups.length, 3);
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

    assert.ok(
      templates.resourceTemplates.some(
        (template) => template.uriTemplate === 'fna://routes/{expedition}',
      ),
    );
    const route = await client.readResource({ uri: 'fna://routes/Flinders' });
    const summary = JSON.parse(route.contents[0].text);
    assert.ok(summary.positionsAnalyzed > 0);
    assert.ok(summary.groups.every((group) => group.dimensions.expedition === 'Flinders'));

    assert.ok(
      templates.resourceTemplates.some(
        (template) => template.uriTemplate === 'fna://journals/{date}',
      ),
    );
    const day = await client.readResource({ uri: 'fna://journals/1802-04-08' });
    const journal = JSON.parse(day.contents[0].text);
    assert.equal(journal.date, '1802-04-08');
  });
});

test('the new route and journal tools answer through the MCP transport', async () => {
  await withClient(async (client) => {
    const positions = await client.callTool({
      name: 'search_route_positions',
      arguments: { expedition: 'Flinders', flags: { mouillage: true }, limit: 5 },
    });
    assert.equal(positions.isError, undefined);
    assert.ok(payload(positions).total > 0);
    assert.ok(
      payload(positions).items.every((item) => item.flags.mouillage === true),
    );

    const journals = await client.callTool({
      name: 'get_journal_day',
      arguments: { date: '1801-05-27' },
    });
    assert.equal(journals.isError, undefined);
    assert.ok(payload(journals).entries.length > 0);

    const dates = await client.callTool({
      name: 'list_remarkable_dates',
      arguments: { expedition: 'Entrecasteaux' },
    });
    assert.equal(dates.isError, undefined);
    assert.ok(payload(dates).total > 0);
  });
});

test('narratives come back in the language of the question only', async () => {
  await withClient(async (client) => {
    const explicit = payload(
      await client.callTool({ name: 'search_toponyms', arguments: { query: 'Péron', language: 'en' } }),
    );
    assert.equal(explicit.language, 'en');
    assert.ok(explicit.items.every((item) => !('history_fr' in item)));

    const inferred = payload(
      await client.callTool({ name: 'search_toponyms', arguments: { query: 'where is the island named after Peron' } }),
    );
    assert.equal(inferred.language, 'en');

    const fallback = payload(
      await client.callTool({ name: 'search_toponyms', arguments: { query: 'Péron' } }),
    );
    assert.equal(fallback.language, 'fr');
    assert.ok(fallback.items.every((item) => !('history' in item)));
    assert.ok(fallback.items.every((item) => (item.history_fr ?? '').length <= 202));
  });
});

test('tool responses are sent once, without empty fields', async () => {
  await withClient(async (client) => {
    const response = await client.callTool({
      name: 'search_route_positions',
      arguments: { vessel: 'le Géographe', limit: 5 },
    });
    assert.equal(response.structuredContent, undefined);
    assert.doesNotMatch(response.content[0].text, /:""|:null|\n/);
    const data = payload(response);
    assert.ok(data.items.every((item) => !('observation' in item) && !('provenance' in item)));
  });
});

test('Baudin\'s journal is served from the Soviche edition, in the language asked', async () => {
  await withClient(async (client) => {
    const french = payload(
      await client.callTool({ name: 'get_journal_day', arguments: { date: '1802-04-08', language: 'fr' } }),
    );
    const autograph = french.entries.find((entry) => entry.source === 'baudin_autographe');
    assert.ok(autograph, 'the autograph journal must be read for 8 April 1802');
    assert.match(autograph.texte, /M\. Flinders/);
    assert.doesNotMatch(autograph.texte, /HPlinders|bétiment|vint à borâ/);
    assert.ok(french.entries.every((entry) => entry.source !== 'baudin_bnf'));

    const english = payload(
      await client.callTool({ name: 'get_journal_day', arguments: { date: '1802-04-08', language: 'en' } }),
    );
    const translated = english.entries.find((entry) => entry.source === 'baudin_autographe');
    assert.match(translated.texte, /Flinders/);
    assert.doesNotMatch(translated.texte, /nous|bâtiment/);
  });
});
