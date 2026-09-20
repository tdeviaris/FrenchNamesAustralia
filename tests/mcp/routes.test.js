import assert from 'node:assert/strict';
import test from 'node:test';

import {
  JOURNAL_ENTRIES,
  REMARKABLE_DATES,
  ROUTE_POSITIONS,
  ROUTE_TRAJECTORIES,
} from '../../mcp/data-store.js';
import {
  getJournalDay,
  getRouteSummary,
  searchJournals,
  searchRemarkableDates,
  searchRoutePositions,
} from '../../mcp/query.js';
import {
  GetJournalDaySchema,
  SearchJournalsSchema,
  SearchRoutePositionsSchema,
} from '../../mcp/schemas.js';

test('every route position carries an expedition, a vessel, and usable coordinates', () => {
  assert.ok(ROUTE_POSITIONS.length > 1800);
  assert.ok(ROUTE_TRAJECTORIES.length > 0);
  for (const position of ROUTE_POSITIONS) {
    assert.ok(['Baudin', 'Entrecasteaux', 'Flinders'].includes(position.expedition));
    assert.ok(position.navire, `${position.id} has no vessel`);
    assert.ok(Number.isFinite(position.lat) && Number.isFinite(position.lon));
    assert.match(position.date, /^\d{4}-\d{2}-\d{2}$/);
  }
});

test("d'Entrecasteaux positions belong to both vessels sailing in company", () => {
  const entrecasteaux = ROUTE_POSITIONS.filter(
    (position) => position.expedition === 'Entrecasteaux',
  );
  assert.ok(entrecasteaux.length > 500);
  assert.ok(entrecasteaux.every((position) => position.navire === "la Recherche et l'Espérance"));
  assert.ok(
    entrecasteaux.every((position) =>
      ['la Recherche', "l'Espérance"].every((name) => position.navires.includes(name)),
    ),
  );

  const trajectories = ROUTE_TRAJECTORIES.filter(
    (trajectory) => trajectory.expedition === 'Entrecasteaux',
  );
  assert.ok(trajectories.length > 0);
  assert.ok(trajectories.every((trajectory) => trajectory.navires.length === 2));

  assert.ok(ROUTE_POSITIONS.every((position) => position.navires.length > 0));
});

test('collective route labels are resolved into the hulls they actually place', () => {
  assert.ok(
    ROUTE_POSITIONS.every((position) => position.navire !== 'les corvettes'),
    'the misleading collective label must never surface as a vessel',
  );

  const collective = ROUTE_POSITIONS.filter((position) => position.navireSource === 'les corvettes');
  assert.ok(collective.length > 400);
  assert.ok(collective.every((position) => position.navireCollectif === true));
  assert.ok(collective.every((position) => position.navires.includes('le Géographe')));

  // Avant le départ du Naturaliste pour la France, le 18 novembre 1802.
  const early = collective.find((position) => position.date === '1800-10-19');
  assert.deepEqual(early.navires, ['le Géographe', 'le Naturaliste']);

  // Après, le Casuarina acheté à Port Jackson prend sa place.
  const late = collective.find((position) => position.date === '1803-06-03');
  assert.deepEqual(late.navires, ['le Géographe', 'le Casuarina']);

  // Quand un compagnon tient sa propre table le même jour, il était relevé à
  // part : la position collective n'est plus que celle du bâtiment amiral.
  const apart = collective.find((position) => position.date === '1802-03-08');
  assert.deepEqual(apart.navires, ['le Géographe']);
  assert.ok(
    ROUTE_POSITIONS.some(
      (position) => position.date === '1802-03-08' && position.navireSource === 'le Naturaliste',
    ),
  );
});

test('a hull is found wherever a reading places it, collective or not', () => {
  const geographe = searchRoutePositions({ vessel: 'le Géographe', limit: 1 });
  const named = ROUTE_POSITIONS.filter((position) => position.navireSource === 'le Géographe');
  assert.ok(
    geographe.total > named.length * 3,
    'the collective readings must widen the Géographe well beyond its own tables',
  );
  assert.equal(
    geographe.total,
    ROUTE_POSITIONS.filter((position) => position.navires.includes('le Géographe')).length,
  );

  const perHull = getRouteSummary({ groupBy: ['coque'] });
  assert.equal(perHull.perHull, true);
  const counts = Object.fromEntries(
    perHull.groups.map((group) => [group.dimensions.coque, group.count]),
  );
  assert.equal(counts['le Géographe'], geographe.total);
  assert.ok(counts["l'Espérance"] === counts['la Recherche']);
  assert.equal(
    perHull.groups.reduce((total, group) => total + group.count, 0),
    ROUTE_POSITIONS.reduce((total, position) => total + position.navires.length, 0),
  );

  // Le libellé publié reste interrogeable, pour remonter à la table source.
  const traceable = searchRoutePositions({ vessel: 'les corvettes', limit: 1 });
  assert.equal(traceable.total, ROUTE_POSITIONS.filter((p) => p.navireSource === 'les corvettes').length);
});

test('either vessel of a squadron finds the shared positions', () => {
  const recherche = searchRoutePositions({ vessel: 'la Recherche', limit: 1 });
  const esperance = searchRoutePositions({ vessel: "l'Espérance", limit: 1 });
  const unaccented = searchRoutePositions({ vessel: 'esperance', limit: 1 });

  assert.ok(recherche.total > 500);
  assert.equal(esperance.total, recherche.total);
  assert.equal(unaccented.total, recherche.total);
  assert.equal(esperance.items[0].navire, "la Recherche et l'Espérance");

  const summary = getRouteSummary({ vessel: "l'Espérance" });
  assert.ok(summary.trajectories.length > 0);
  assert.ok(summary.groups.every((group) => group.dimensions.expedition === 'Entrecasteaux'));
});

test('route search filters by vessel, date interval, and qualifiers', () => {
  const investigator = searchRoutePositions({ vessel: 'Investigator', limit: 200 });
  assert.ok(investigator.total > 100);
  assert.ok(investigator.items.every((item) => item.navire === "l'Investigator"));

  const window = searchRoutePositions({
    expedition: 'Baudin',
    dateFrom: '1802-04-08',
    dateTo: '1802-04-09',
    limit: 200,
  });
  assert.ok(window.total > 0);
  assert.ok(window.items.every((item) => item.date >= '1802-04-08' && item.date <= '1802-04-09'));

  const anchored = searchRoutePositions({ flags: { mouillage: true }, limit: 200 });
  assert.ok(anchored.total > 0);
  assert.ok(anchored.items.every((item) => item.flags.mouillage === true));

  const extrapolated = searchRoutePositions({ flags: { extrapole: false }, limit: 200 });
  assert.ok(extrapolated.items.every((item) => item.flags.extrapole === false));
});

test('route search orders by distance and keeps the radius honest', () => {
  const nearby = searchRoutePositions({
    center: { latitude: -43.57255, longitude: 146.8995 },
    radiusKm: 200,
    order: 'distance',
    limit: 50,
  });
  assert.ok(nearby.total > 0);
  const distances = nearby.items.map((item) => item.distanceKm);
  assert.deepEqual(distances, [...distances].sort((a, b) => a - b));
  assert.ok(distances.every((distance) => distance <= 200));
});

test('route summaries cover every position without pagination', () => {
  const summary = getRouteSummary({ groupBy: ['expedition', 'navire'] });
  assert.equal(summary.truncated, false);
  assert.equal(summary.positionsAnalyzed, ROUTE_POSITIONS.length);
  assert.equal(
    summary.groups.reduce((total, group) => total + group.count, 0),
    ROUTE_POSITIONS.length,
  );
  for (const group of summary.groups) {
    assert.ok(group.dateRange.from <= group.dateRange.to);
    assert.ok(group.distinctDates > 0);
  }

  const flinders = getRouteSummary({ expedition: 'Flinders', groupBy: ['year'] });
  assert.ok(flinders.groups.every((group) => /^\d{4}$/.test(group.dimensions.year)));
});

test('journals are searchable across sources and return excerpts by default', () => {
  const all = searchJournals({ limit: 1 });
  assert.equal(all.total, JOURNAL_ENTRIES.length);

  const hit = searchJournals({ query: 'appareillé', limit: 10 });
  assert.ok(hit.total > 0);
  assert.ok(hit.items.every((item) => item.texte.length <= 720));

  const full = searchJournals({ query: 'appareillé', limit: 1, full: true });
  assert.equal(full.items[0].texte.length, full.items[0].characters);

  const scoped = searchJournals({ sources: ['breton'], limit: 200 });
  assert.ok(scoped.total > 0);
  assert.ok(scoped.items.every((item) => item.source === 'breton'));
});

test('one day gathers every journal, position, and milestone at once', () => {
  const day = getJournalDay({ date: '1801-05-27' });
  assert.equal(day.date, '1801-05-27');
  assert.ok(day.entries.length > 0);
  assert.ok(day.entries.every((entry) => entry.texte.length > 0));
  assert.deepEqual(
    day.sourcesAvailable,
    day.entries.map((entry) => entry.source),
  );
  assert.ok(day.routePositions.every((position) => position.date === '1801-05-27'));
  assert.equal(day.truncated, false);

  const empty = getJournalDay({ date: '1799-01-01' });
  assert.equal(empty.entries.length, 0);
  assert.equal(empty.routePositions.length, 0);
});

test('remarkable dates cover the three expeditions in both languages', () => {
  const all = searchRemarkableDates({ limit: 200 });
  assert.equal(all.total, REMARKABLE_DATES.length);
  const expeditions = new Set(all.items.map((item) => item.expedition));
  assert.deepEqual([...expeditions].sort(), ['Baudin', 'Entrecasteaux', 'Flinders']);

  const french = searchRemarkableDates({ language: 'fr', limit: 5 });
  assert.ok(french.items.every((item) => 'libelle_fr' in item && !('libelle_en' in item)));

  const dates = all.items.map((item) => item.date);
  assert.deepEqual(dates, [...dates].sort());
});

test('route and journal schemas reject incoherent input', () => {
  assert.equal(
    SearchRoutePositionsSchema.safeParse({ order: 'distance' }).success,
    false,
    'ordering by distance requires a centre',
  );
  assert.equal(
    SearchRoutePositionsSchema.safeParse({ center: { latitude: -35, longitude: 140 } }).success,
    false,
  );
  assert.equal(
    SearchRoutePositionsSchema.safeParse({ dateFrom: '1803-01-01', dateTo: '1801-01-01' }).success,
    false,
  );
  assert.equal(SearchRoutePositionsSchema.safeParse({ flags: { inconnu: true } }).success, false);
  assert.equal(SearchJournalsSchema.safeParse({ sources: ['inconnu'] }).success, false);
  assert.equal(GetJournalDaySchema.safeParse({ date: '8 avril 1802' }).success, false);
});
