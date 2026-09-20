import assert from 'node:assert/strict';
import test from 'node:test';

import { hasCoordinates, normalizeState, TOPONYMS } from '../../mcp/data-store.js';
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
  assert.equal(summary.toponyms, TOPONYMS.length);
  assert.ok(summary.toponyms >= 1000, 'the three corpora must all be loaded');
  assert.deepEqual(summary.expeditions, ['Baudin', 'Entrecasteaux', 'Flinders']);
  assert.equal(summary.timelineEvents, 125);
  assert.equal(summary.invariants.uniqueCodes, TOPONYMS.length);
  assert.equal(summary.invariants.missingCodes, 0);
  assert.equal(
    summary.invariants.unlocatedRecords,
    TOPONYMS.filter((record) => !hasCoordinates(record)).length,
  );
  assert.equal(summary.invariants.unlocatedCodes.length, summary.invariants.unlocatedRecords);
  assert.ok(
    summary.coordinateBounds.minLongitude > 100,
    'unlocated records must not drag the bounds to the null island',
  );
});

test('the three expeditions are loaded with their own provenance', () => {
  const analysis = analyzeToponyms({ groupBy: ['expedition'] });
  const counts = Object.fromEntries(
    analysis.groups.map((group) => [group.dimensions.expedition, group.count]),
  );
  assert.equal(counts.Baudin + counts.Entrecasteaux + counts.Flinders, TOPONYMS.length);

  const flinders = getToponym('Flinders001', 'both');
  assert.equal(flinders.expedition, 'Flinders');
  assert.equal(flinders.navire, "l'Investigator");
  assert.equal(flinders.provenance.dataset, 'data/flinders.json');
  assert.ok(flinders.citation_fr.length > 100, 'the French quotation must be attached');
});

test('Flinders quotations and Hakluyt attributions are searchable and attached', () => {
  const summary = getDatasetSummary();
  assert.ok(summary.toponymsWithCitation > 300);
  assert.ok(summary.toponymsWithAttribution > 100);

  const thistle = getToponym('Flinders009', 'both');
  assert.equal(thistle.attribution.sujet, 'John Thistle');
  assert.ok(thistle.provenance.attribution, 'data/attributions_hakluyt.json');

  const byAttribution = searchToponyms({
    query: 'John Thistle',
    fields: ['attributions'],
    limit: 20,
  });
  assert.ok(byAttribution.items.some((record) => record.code === 'Flinders009'));

  const englishOnly = getToponym('Flinders009', 'en');
  assert.equal('citation_fr' in englishOnly, false);
});

test('Flinders filters narrow the corpus by vessel, sector, date, and uncertainty', () => {
  const norfolk = searchToponyms({ vessel: 'le Norfolk', limit: 200 });
  assert.ok(norfolk.total > 0);
  assert.ok(norfolk.items.every((record) => record.navire === 'le Norfolk'));

  const uncertain = analyzeToponyms({ uncertain: true, groupBy: ['expedition'] });
  assert.ok(uncertain.recordsAnalyzed > 0);
  assert.deepEqual(
    uncertain.groups.map((group) => group.dimensions.expedition),
    ['Flinders'],
  );

  const dated = searchToponyms({ dateFrom: '1802-01-01', dateTo: '1802-12-31', limit: 200 });
  assert.ok(dated.total > 0);
  assert.ok(dated.items.every((record) => record.date >= '1802-01-01' && record.date <= '1802-12-31'));
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

  assert.equal(codes.length, TOPONYMS.length);
  assert.equal(new Set(codes).size, TOPONYMS.length);
  assert.deepEqual([...codes].sort(), TOPONYMS.map((record) => record.code).sort());
});

test('statistics scan all matching records and reproduce independent state counts', () => {
  const expected = TOPONYMS.reduce((groups, record) => {
    const state = normalizeState(record.state);
    groups[state] = (groups[state] ?? 0) + 1;
    return groups;
  }, {});
  const analysis = analyzeToponyms({ groupBy: ['state'], distinctBy: ['code'] });
  assert.equal(analysis.recordsScanned, TOPONYMS.length);
  assert.equal(analysis.recordsAnalyzed, TOPONYMS.length);
  assert.equal(analysis.distinctCounts.code, TOPONYMS.length);
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

test('unlocated toponyms are excluded from every geographic filter', () => {
  const unlocated = TOPONYMS.filter((record) => !hasCoordinates(record));
  assert.ok(unlocated.length > 0, 'the corpus still carries records without coordinates');

  const nearNullIsland = findNearbyToponyms({
    latitude: 0,
    longitude: 0,
    radiusKm: 500,
    limit: 200,
  });
  assert.equal(nearNullIsland.totalMatches, 0);

  const wholeWorld = analyzeToponyms({
    boundingBox: { south: -90, north: 90, west: -180, east: 180 },
  });
  assert.equal(wholeWorld.recordsAnalyzed, TOPONYMS.length - unlocated.length);

  const everything = analyzeToponyms({});
  assert.equal(everything.geographicSummary.unlocatedRecords, unlocated.length);
});

test('state matching ignores case across the three corpora', () => {
  const upper = searchToponyms({ states: ['QLD'], limit: 200 });
  const mixed = searchToponyms({ states: ['Tas'], limit: 200 });
  assert.ok(upper.total > 0);
  assert.ok(mixed.total > 0);
  assert.ok(
    mixed.items.some((record) => record.expedition === 'Flinders'),
    'Tas must also match the Flinders records',
  );
});

test('schemas reject excessive pages and incomplete radius filters', () => {
  assert.equal(SearchToponymsSchema.safeParse({ limit: 201 }).success, false);
  assert.equal(
    AnalyzeToponymsSchema.safeParse({ center: { latitude: -35, longitude: 140 } }).success,
    false,
  );
});
