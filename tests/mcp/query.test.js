import assert from 'node:assert/strict';
import test from 'node:test';

import { TOPONYMS } from '../../mcp/data-store.js';
import {
  analyzeToponyms,
  findNearbyToponyms,
  getDatasetSummary,
  getToponym,
  searchTimeline,
  searchToponyms,
} from '../../mcp/query.js';
import { AnalyzeToponymsSchema, SearchToponymsSchema } from '../../mcp/schemas.js';

test('dataset integrity invariants are preserved', () => {
  const summary = getDatasetSummary();
  assert.equal(summary.toponyms, 671);
  assert.equal(summary.timelineEvents, 125);
  assert.equal(summary.invariants.uniqueCodes, 671);
  assert.equal(summary.invariants.missingCodes, 0);
  assert.equal(summary.invariants.invalidCoordinates, 0);
});

test('getToponym returns complete bilingual priority fields without truncation', () => {
  const record = getToponym('Baudin001', 'both');
  assert.equal(record.code, 'Baudin001');
  assert.equal(record.lat, -38.85044);
  assert.equal(record.lon, 146.07164);
  assert.ok(record.characteristic_fr.length > 500);
  assert.ok(record.characteristic.length > 500);
  assert.ok(record.history_fr.length > 1000);
  assert.ok(record.history.length > 1000);
  assert.deepEqual(record.provenance, {
    dataset: 'data/baudin.json',
    code: 'Baudin001',
  });
});

test('text search is accent-insensitive and respects language and field selection', () => {
  const french = searchToponyms({
    query: 'respectable savant et voyageur',
    language: 'fr',
    fields: ['history'],
    limit: 20,
  });
  assert.ok(french.items.some((record) => record.code === 'Baudin001'));

  const accentInsensitive = searchToponyms({
    query: 'peron',
    language: 'fr',
    fields: ['history'],
    limit: 200,
  });
  assert.ok(accentInsensitive.total > 0);
  assert.ok(accentInsensitive.items.some((record) => record.code === 'Baudin001'));

  const english = searchToponyms({
    query: 'respectable scholar and traveller',
    language: 'en',
    fields: ['history'],
    limit: 20,
  });
  assert.ok(english.items.some((record) => record.code === 'Baudin001'));
  assert.equal('history_fr' in english.items[0], false);
});

test('pagination reconstructs the complete corpus without duplicates or omissions', () => {
  const codes = [];
  let cursor;
  do {
    const page = searchToponyms({ limit: 200, cursor });
    codes.push(...page.items.map((record) => record.code));
    cursor = page.nextCursor;
  } while (cursor);

  assert.equal(codes.length, 671);
  assert.equal(new Set(codes).size, 671);
  assert.deepEqual([...codes].sort(), TOPONYMS.map((record) => record.code).sort());
});

test('statistics scan all matching records and reproduce independent state counts', () => {
  const expected = TOPONYMS.reduce((groups, record) => {
    groups[record.state] = (groups[record.state] ?? 0) + 1;
    return groups;
  }, {});
  const analysis = analyzeToponyms({ groupBy: ['state'], distinctBy: ['code'] });
  assert.equal(analysis.recordsScanned, 671);
  assert.equal(analysis.recordsAnalyzed, 671);
  assert.equal(analysis.distinctCounts.code, 671);
  assert.equal(analysis.truncated, false);

  for (const group of analysis.groups) {
    assert.equal(group.count, expected[group.dimensions.state]);
  }
});

test('statistical text filters use full French and English narratives', () => {
  const french = analyzeToponyms({
    query: 'respectable savant et voyageur',
    language: 'fr',
    fields: ['history'],
    groupBy: ['expedition'],
  });
  assert.ok(french.recordsAnalyzed >= 1);
  assert.equal(french.truncated, false);

  const english = analyzeToponyms({
    query: 'respectable scholar and traveller',
    language: 'en',
    fields: ['history'],
  });
  assert.ok(english.recordsAnalyzed >= 1);
});

test('nearby search calculates distance and orders the exact coordinate first', () => {
  const result = findNearbyToponyms({
    latitude: -38.85044,
    longitude: 146.07164,
    radiusKm: 1,
    language: 'both',
    limit: 20,
  });
  assert.ok(result.totalMatches >= 1);
  assert.equal(result.items[0].code, 'Baudin001');
  assert.equal(result.items[0].distanceKm, 0);
  assert.equal(result.items[0].lat, -38.85044);
  assert.equal(result.items[0].lon, 146.07164);
});

test('timeline can be filtered by date, vessel, and language', () => {
  const result = searchTimeline({
    language: 'fr',
    vessel: 'geographe',
    dateFrom: '1800-10-19',
    dateTo: '1800-10-19',
    limit: 20,
  });
  assert.ok(result.total >= 1);
  assert.ok(result.items.every((event) => event.geographe));
  assert.ok(result.items.every((event) => 'histoire' in event && !('story' in event)));
});

test('schemas reject excessive pages and incomplete radius filters', () => {
  assert.equal(SearchToponymsSchema.safeParse({ limit: 201 }).success, false);
  assert.equal(
    AnalyzeToponymsSchema.safeParse({ center: { latitude: -35, longitude: 140 } }).success,
    false,
  );
});
