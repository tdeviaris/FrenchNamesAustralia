import {
  DATASET_SUMMARY,
  normalizeText,
  SEARCH_INDEX,
  TIMELINE,
  TOPONYM_BY_CODE,
  TOPONYMS,
} from './data-store.js';

const SEARCH_FIELDS = {
  code: ['code'],
  names: ['frenchName', 'variantName', 'ausEName'],
  indigenous: ['indigenousName', 'indigenousLanguage'],
  characteristics: ['characteristic_fr', 'characteristic'],
  history: ['history_fr', 'history'],
};

const FIELD_WEIGHTS = {
  code: 100,
  frenchName: 40,
  variantName: 30,
  ausEName: 30,
  indigenousName: 30,
  indigenousLanguage: 10,
  characteristic_fr: 8,
  characteristic: 8,
  history_fr: 7,
  history: 7,
};

const COVERAGE_FIELDS = [
  'characteristic_fr',
  'characteristic',
  'history_fr',
  'history',
  'indigenousName',
  'indigenousLanguage',
  'imgUrl',
  'mapUrl',
  'wiki_fr',
  'wiki_en',
];

function round(value, digits = 6) {
  const factor = 10 ** digits;
  return Math.round(value * factor) / factor;
}

function encodeCursor(offset) {
  return Buffer.from(JSON.stringify({ offset }), 'utf8').toString('base64url');
}

function decodeCursor(cursor) {
  if (!cursor) return 0;
  try {
    const parsed = JSON.parse(Buffer.from(cursor, 'base64url').toString('utf8'));
    if (!Number.isInteger(parsed.offset) || parsed.offset < 0) throw new Error('Invalid offset');
    return parsed.offset;
  } catch {
    throw new Error('Invalid pagination cursor');
  }
}

function paginate(items, limit, cursor) {
  const offset = decodeCursor(cursor);
  const page = items.slice(offset, offset + limit);
  const nextOffset = offset + page.length;
  return {
    items: page,
    total: items.length,
    returned: page.length,
    limit,
    offset,
    truncated: nextOffset < items.length,
    nextCursor: nextOffset < items.length ? encodeCursor(nextOffset) : null,
  };
}

function fieldsForSearch(groups = Object.keys(SEARCH_FIELDS), language = 'both') {
  const fields = [...new Set(groups.flatMap((group) => SEARCH_FIELDS[group] ?? []))];
  if (language === 'fr') {
    return fields.filter((field) => !['characteristic', 'history'].includes(field));
  }
  if (language === 'en') {
    return fields.filter((field) => !['characteristic_fr', 'history_fr'].includes(field));
  }
  return fields;
}

function matchesCommonFilters(record, options = {}) {
  const { expedition, states, boundingBox } = options;
  if (expedition && record.expedition !== expedition) return false;
  if (states?.length && !states.includes(record.state)) return false;
  if (boundingBox) {
    if (
      record.lat < boundingBox.south ||
      record.lat > boundingBox.north ||
      record.lon < boundingBox.west ||
      record.lon > boundingBox.east
    ) {
      return false;
    }
  }
  return true;
}

function scoreIndexedRecord(indexed, normalizedQuery, fields) {
  if (!normalizedQuery) return 0;
  const tokens = normalizedQuery.split(' ').filter(Boolean);
  let score = 0;

  for (const field of fields) {
    const value = indexed.normalized[field];
    if (!value) continue;
    const weight = FIELD_WEIGHTS[field] ?? 1;
    if (value === normalizedQuery) score += weight * 8;
    else if (value.startsWith(normalizedQuery)) score += weight * 5;
    else if (value.includes(normalizedQuery)) score += weight * 3;
    else {
      const matchedTokens = tokens.filter((token) => value.includes(token)).length;
      score += weight * (matchedTokens / Math.max(tokens.length, 1));
    }
  }
  return round(score, 3);
}

function excerpt(value, query, maxLength = 360) {
  const text = String(value ?? '').trim();
  if (!text || text.length <= maxLength) return text;
  const normalized = normalizeText(text);
  const normalizedQuery = normalizeText(query);
  const matchIndex = normalizedQuery ? normalized.indexOf(normalizedQuery) : -1;
  const approximateStart = matchIndex >= 0 ? Math.max(0, matchIndex - Math.floor(maxLength / 3)) : 0;
  let start = approximateStart;
  if (start > 0) {
    const nextSpace = text.indexOf(' ', start);
    if (nextSpace >= 0) start = nextSpace + 1;
  }
  const end = Math.min(text.length, start + maxLength);
  return `${start > 0 ? '…' : ''}${text.slice(start, end).trim()}${end < text.length ? '…' : ''}`;
}

function narrativeSummary(record, language, query = '') {
  const result = {};
  if (language !== 'en') {
    result.characteristic_fr = excerpt(record.characteristic_fr, query);
    result.history_fr = excerpt(record.history_fr, query);
  }
  if (language !== 'fr') {
    result.characteristic = excerpt(record.characteristic, query);
    result.history = excerpt(record.history, query);
  }
  return result;
}

function recordSummary(record, language = 'both', query = '') {
  return {
    code: record.code,
    expedition: record.expedition,
    state: record.state,
    frenchName: record.frenchName,
    variantName: record.variantName,
    ausEName: record.ausEName,
    indigenousName: record.indigenousName,
    indigenousLanguage: record.indigenousLanguage,
    lat: record.lat,
    lon: record.lon,
    ...narrativeSummary(record, language, query),
    detailsLink: record.detailsLink,
    detailsLink_en: record.detailsLink_en,
    provenance: record._provenance,
  };
}

function localizedFullRecord(record, language = 'both') {
  const result = { ...record, provenance: record._provenance };
  delete result._provenance;
  if (language === 'fr') {
    delete result.characteristic;
    delete result.history;
    delete result.detailsLink_en;
    delete result.mapTitle_en;
    delete result.wiki_en;
  } else if (language === 'en') {
    delete result.characteristic_fr;
    delete result.history_fr;
    delete result.origin_fr;
    delete result.detailsLink;
    delete result.mapTitle_fr;
    delete result.wiki_fr;
  }
  return result;
}

function recordMatchesText(indexed, query, fields, language) {
  const normalizedQuery = normalizeText(query);
  if (!normalizedQuery) return true;
  return scoreIndexedRecord(indexed, normalizedQuery, fieldsForSearch(fields, language)) > 0;
}

export function searchToponyms(options = {}) {
  const {
    query = '',
    language = 'both',
    fields = Object.keys(SEARCH_FIELDS),
    expedition,
    states,
    boundingBox,
    limit = 20,
    cursor,
  } = options;
  const normalizedQuery = normalizeText(query);
  const selectedFields = fieldsForSearch(fields, language);

  const matches = SEARCH_INDEX.filter(({ record }) =>
    matchesCommonFilters(record, { expedition, states, boundingBox }),
  )
    .map((indexed) => ({
      record: indexed.record,
      score: normalizedQuery ? scoreIndexedRecord(indexed, normalizedQuery, selectedFields) : 0,
    }))
    .filter(({ score }) => !normalizedQuery || score > 0)
    .sort((a, b) => b.score - a.score || a.record.code.localeCompare(b.record.code));

  const page = paginate(matches, limit, cursor);
  return {
    recordsScanned: TOPONYMS.length,
    query,
    language,
    fields,
    ...page,
    items: page.items.map(({ record, score }) => ({
      relevanceScore: score,
      ...recordSummary(record, language, query),
    })),
  };
}

export function getToponym(code, language = 'both') {
  const record = TOPONYM_BY_CODE.get(normalizeText(code));
  return record ? localizedFullRecord(record, language) : null;
}

export function haversineDistanceKm(lat1, lon1, lat2, lon2) {
  const toRadians = (degrees) => (degrees * Math.PI) / 180;
  const earthRadiusKm = 6371.0088;
  const dLat = toRadians(lat2 - lat1);
  const dLon = toRadians(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRadians(lat1)) *
      Math.cos(toRadians(lat2)) *
      Math.sin(dLon / 2) ** 2;
  return earthRadiusKm * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

export function findNearbyToponyms(options) {
  const {
    latitude,
    longitude,
    radiusKm = 100,
    language = 'both',
    expedition,
    states,
    limit = 50,
  } = options;

  const matches = TOPONYMS.filter((record) =>
    matchesCommonFilters(record, { expedition, states }),
  )
    .map((record) => ({
      record,
      distanceKm: haversineDistanceKm(latitude, longitude, record.lat, record.lon),
    }))
    .filter(({ distanceKm }) => distanceKm <= radiusKm)
    .sort((a, b) => a.distanceKm - b.distanceKm || a.record.code.localeCompare(b.record.code));

  return {
    recordsScanned: TOPONYMS.length,
    center: { latitude, longitude },
    radiusKm,
    totalMatches: matches.length,
    returned: Math.min(matches.length, limit),
    truncated: matches.length > limit,
    items: matches.slice(0, limit).map(({ record, distanceKm }) => ({
      distanceKm: round(distanceKm, 3),
      ...recordSummary(record, language),
    })),
  };
}

function groupValue(record, field) {
  switch (field) {
    case 'hasIndigenousName':
      return Boolean(record.indigenousName);
    case 'hasIndigenousLanguage':
      return Boolean(record.indigenousLanguage);
    case 'hasImage':
      return Boolean(record.imgUrl);
    case 'hasMap':
      return Boolean(record.mapUrl);
    case 'hasWikipedia':
      return Boolean(record.wiki_fr || record.wiki_en);
    case 'hasCharacteristicsFr':
      return Boolean(record.characteristic_fr);
    case 'hasCharacteristicsEn':
      return Boolean(record.characteristic);
    case 'hasHistoryFr':
      return Boolean(record.history_fr);
    case 'hasHistoryEn':
      return Boolean(record.history);
    default:
      return record[field] || '(empty)';
  }
}

function geographicSummary(records) {
  if (!records.length) return null;
  const latitudes = records.map((record) => record.lat);
  const longitudes = records.map((record) => record.lon);
  return {
    bounds: {
      south: Math.min(...latitudes),
      north: Math.max(...latitudes),
      west: Math.min(...longitudes),
      east: Math.max(...longitudes),
    },
    meanCoordinate: {
      latitude: round(latitudes.reduce((sum, value) => sum + value, 0) / records.length),
      longitude: round(longitudes.reduce((sum, value) => sum + value, 0) / records.length),
    },
  };
}

function fieldCoverage(records) {
  return Object.fromEntries(
    COVERAGE_FIELDS.map((field) => {
      const present = records.filter((record) => String(record[field] ?? '').trim()).length;
      return [
        field,
        {
          present,
          missing: records.length - present,
          percentPresent: records.length ? round((present / records.length) * 100, 2) : 0,
        },
      ];
    }),
  );
}

export function analyzeToponyms(options = {}) {
  const {
    query = '',
    language = 'both',
    fields = ['names', 'indigenous', 'characteristics', 'history'],
    expedition,
    states,
    boundingBox,
    center,
    radiusKm,
    groupBy = [],
    distinctBy = [],
  } = options;

  const records = SEARCH_INDEX.filter((indexed) => {
    if (!matchesCommonFilters(indexed.record, { expedition, states, boundingBox })) return false;
    if (center && radiusKm != null) {
      const distance = haversineDistanceKm(
        center.latitude,
        center.longitude,
        indexed.record.lat,
        indexed.record.lon,
      );
      if (distance > radiusKm) return false;
    }
    return recordMatchesText(indexed, query, fields, language);
  }).map(({ record }) => record);

  const grouped = new Map();
  if (groupBy.length) {
    for (const record of records) {
      const dimensions = Object.fromEntries(groupBy.map((field) => [field, groupValue(record, field)]));
      const key = JSON.stringify(dimensions);
      const current = grouped.get(key) ?? { dimensions, count: 0 };
      current.count += 1;
      grouped.set(key, current);
    }
  }

  const groups = [...grouped.values()]
    .map((group) => ({
      ...group,
      percentOfAnalyzed: records.length ? round((group.count / records.length) * 100, 2) : 0,
    }))
    .sort(
      (a, b) =>
        b.count - a.count || JSON.stringify(a.dimensions).localeCompare(JSON.stringify(b.dimensions)),
    );

  return {
    recordsScanned: TOPONYMS.length,
    recordsAnalyzed: records.length,
    filters: { query, language, fields, expedition, states, boundingBox, center, radiusKm },
    groupBy,
    groups,
    distinctCounts: Object.fromEntries(
      distinctBy.map((field) => [
        field,
        new Set(
          records
            .map((record) => record[field])
            .filter((value) => String(value ?? '').trim() !== ''),
        ).size,
      ]),
    ),
    geographicSummary: geographicSummary(records),
    fieldCoverage: fieldCoverage(records),
    truncated: false,
  };
}

export function searchTimeline(options = {}) {
  const {
    query = '',
    language = 'both',
    vessel,
    dateFrom,
    dateTo,
    interpolation,
    limit = 20,
    cursor,
  } = options;
  const normalizedQuery = normalizeText(query);

  const matches = TIMELINE.filter((event) => {
    if (dateFrom && event.dateISO < dateFrom) return false;
    if (dateTo && event.dateISO > dateTo) return false;
    if (vessel && !event[vessel]) return false;
    if (interpolation != null && Boolean(event.interpolation) !== interpolation) return false;
    if (!normalizedQuery) return true;
    const texts = language === 'fr' ? [event.histoire] : language === 'en' ? [event.story] : [event.histoire, event.story];
    return texts.some((text) => normalizeText(text).includes(normalizedQuery));
  }).sort((a, b) => a.dateISO.localeCompare(b.dateISO) || a.id - b.id);

  const page = paginate(matches, limit, cursor);
  return {
    recordsScanned: TIMELINE.length,
    query,
    language,
    ...page,
    items: page.items.map((event) => {
      const item = {
        id: event.id,
        dateISO: event.dateISO,
        lat: event.lat,
        lon: event.lon,
        geographe: event.geographe,
        naturaliste: event.naturaliste,
        casuarina: event.casuarina,
        flinders: event.flinders,
        interpolation: event.interpolation,
        provenance: event._provenance,
      };
      if (language !== 'en') item.histoire = event.histoire;
      if (language !== 'fr') item.story = event.story;
      return item;
    }),
  };
}

export function getDatasetSummary() {
  return {
    ...DATASET_SUMMARY,
    fieldCoverage: fieldCoverage(TOPONYMS),
    invariants: {
      uniqueCodes: new Set(TOPONYMS.map((record) => record.code)).size,
      missingCodes: TOPONYMS.filter((record) => !record.code).length,
      invalidCoordinates: TOPONYMS.filter(
        (record) => !Number.isFinite(record.lat) || !Number.isFinite(record.lon),
      ).length,
    },
  };
}
