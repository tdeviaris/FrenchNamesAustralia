import { McpServer, ResourceTemplate } from '@modelcontextprotocol/sdk/server/mcp.js';

import { normalizeText, TOPONYMS } from './data-store.js';
import {
  AnalyzeToponymsSchema,
  GetJournalDaySchema,
  GetToponymSchema,
  NearbyToponymsSchema,
  RemarkableDatesSchema,
  RouteSummarySchema,
  SearchJournalsSchema,
  SearchRoutePositionsSchema,
  SearchTimelineSchema,
  SearchToponymsSchema,
} from './schemas.js';
import {
  analyzeToponyms,
  findNearbyToponyms,
  getDatasetSummary,
  getJournalDay,
  getRouteSummary,
  getToponym,
  searchJournals,
  searchRemarkableDates,
  searchRoutePositions,
  searchTimeline,
  searchToponyms,
} from './query.js';

const READ_ONLY_ANNOTATIONS = {
  readOnlyHint: true,
  destructiveHint: false,
  idempotentHint: true,
  openWorldHint: false,
};

function result(data) {
  return {
    content: [{ type: 'text', text: JSON.stringify(data, null, 2) }],
    structuredContent: data,
  };
}

function notFound(message) {
  return {
    isError: true,
    content: [{ type: 'text', text: JSON.stringify({ error: message }) }],
  };
}

export function createFrenchNamesMcpServer() {
  const server = new McpServer(
    { name: 'french-names-australia', version: '0.1.0' },
    {
      capabilities: { tools: {}, resources: {} },
      instructions:
        'Read-only access to the Baudin, d\'Entrecasteaux, and Flinders corpora: 1021 toponyms, ' +
        'the daily route positions of the three expeditions, the onboard journals, the Baudin timeline, ' +
        'and the remarkable dates. Prefer get_toponym for complete bilingual narratives, ' +
        'find_nearby_toponyms for coordinates, analyze_toponyms for exhaustive statistics, ' +
        'search_route_positions for where a vessel was on a given day, and get_journal_day to read ' +
        'every source for one date at once. Thirty-two toponyms carry no coordinates: they are flagged ' +
        'located: false and are excluded from geographic filters.',
    },
  );

  server.registerTool(
    'search_toponyms',
    {
      title: 'Search Australian French toponyms',
      description:
        'Search names, Indigenous names, French/English characteristics and history, French translations of Flinders quotations, Hakluyt attributions, and the Flinders classification fields. Filter by expedition, state, vessel, category, sector, date, and uncertainty. Detailed lists are paginated; use the returned cursor for the next page.',
      inputSchema: SearchToponymsSchema,
      annotations: READ_ONLY_ANNOTATIONS,
    },
    async (input) => result(searchToponyms(input)),
  );

  server.registerTool(
    'get_toponym',
    {
      title: 'Get one complete toponym record',
      description:
        'Return the complete, untruncated source record for a code such as Baudin001, Entre01, or Flinders055, including coordinates, full French/English characteristic and history fields, the French translation of the Flinders quotation, and the Hakluyt attribution when they exist.',
      inputSchema: GetToponymSchema,
      annotations: READ_ONLY_ANNOTATIONS,
    },
    async ({ code, language }) => {
      const record = getToponym(code, language);
      return record ? result(record) : notFound(`Unknown toponym code: ${code}`);
    },
  );

  server.registerTool(
    'find_nearby_toponyms',
    {
      title: 'Find toponyms near coordinates',
      description:
        'Find records within a radius of a latitude and longitude, ordered by Haversine distance. Returns coordinates, distance, and bilingual narrative excerpts.',
      inputSchema: NearbyToponymsSchema,
      annotations: READ_ONLY_ANNOTATIONS,
    },
    async (input) => result(findNearbyToponyms(input)),
  );

  server.registerTool(
    'analyze_toponyms',
    {
      title: 'Analyze the complete toponym corpus',
      description:
        'Run exhaustive counts, groupings, distinct counts, field coverage, and geographic summaries over every matching record. This tool is never limited by result pagination.',
      inputSchema: AnalyzeToponymsSchema,
      annotations: READ_ONLY_ANNOTATIONS,
    },
    async (input) => result(analyzeToponyms(input)),
  );

  server.registerTool(
    'search_timeline',
    {
      title: 'Search the Baudin expedition timeline',
      description:
        'Search the 125 bilingual chronological events of the Baudin expedition by text, date interval, vessel, and interpolation status. For the three expeditions at once, use list_remarkable_dates.',
      inputSchema: SearchTimelineSchema,
      annotations: READ_ONLY_ANNOTATIONS,
    },
    async (input) => result(searchTimeline(input)),
  );

  server.registerTool(
    'get_dataset_summary',
    {
      title: 'Get dataset metadata and coverage',
      description:
        'Return corpus size across all datasets (toponyms, route positions, journal entries, timeline, remarkable dates), coordinate and date bounds, vessels, journal sources, invariants, and completeness statistics.',
      annotations: READ_ONLY_ANNOTATIONS,
    },
    async () => result(getDatasetSummary()),
  );

  server.registerTool(
    'search_route_positions',
    {
      title: 'Search daily route positions',
      description:
        'Search the 1875 dated positions of the Baudin, d\'Entrecasteaux, and Flinders routes. Filter by expedition, vessel, date interval, bounding box, radius, and route qualifiers such as mouillage, extrapole, or releve_carte. Returns coordinates, the route table and section, the remark, and the onboard weather reading.',
      inputSchema: SearchRoutePositionsSchema,
      annotations: READ_ONLY_ANNOTATIONS,
    },
    async (input) => result(searchRoutePositions(input)),
  );

  server.registerTool(
    'get_route_summary',
    {
      title: 'Summarize the expedition routes',
      description:
        'Aggregate every matching route position by expedition, vessel, year, section, or route table: counts, date ranges, geographic bounds, qualifier counts, and weather coverage. Never limited by pagination.',
      inputSchema: RouteSummarySchema,
      annotations: READ_ONLY_ANNOTATIONS,
    },
    async (input) => result(getRouteSummary(input)),
  );

  server.registerTool(
    'search_journals',
    {
      title: 'Search the onboard journals',
      description:
        'Full-text search across the five transcribed journals of the Baudin expedition (Baudin, the BnF manuscript, Breton, the anonymous Naturaliste journal, and the Géographe journal). Returns excerpts around the match by default; set full to true for complete day entries.',
      inputSchema: SearchJournalsSchema,
      annotations: READ_ONLY_ANNOTATIONS,
    },
    async (input) => result(searchJournals(input)),
  );

  server.registerTool(
    'get_journal_day',
    {
      title: 'Read one day across every source',
      description:
        'Return, for a single ISO date, the complete journal entries of every available source together with the route positions, the timeline events, and the remarkable dates recorded that day.',
      inputSchema: GetJournalDaySchema,
      annotations: READ_ONLY_ANNOTATIONS,
    },
    async (input) => result(getJournalDay(input)),
  );

  server.registerTool(
    'list_remarkable_dates',
    {
      title: 'List the remarkable dates of the three expeditions',
      description:
        'Search the 73 bilingual milestone dates covering Baudin, d\'Entrecasteaux, and Flinders, by text, expedition, vessel, and date interval.',
      inputSchema: RemarkableDatesSchema,
      annotations: READ_ONLY_ANNOTATIONS,
    },
    async (input) => result(searchRemarkableDates(input)),
  );

  server.registerResource(
    'dataset-summary',
    'fna://dataset/summary',
    {
      title: 'French Names Australia dataset summary',
      description: 'Dataset volumes, geographic coverage, source files, and integrity invariants.',
      mimeType: 'application/json',
    },
    async (uri) => ({
      contents: [
        {
          uri: uri.href,
          mimeType: 'application/json',
          text: JSON.stringify(getDatasetSummary(), null, 2),
        },
      ],
    }),
  );

  server.registerResource(
    'toponym-record',
    new ResourceTemplate('fna://toponyms/{code}/{language}', {
      list: undefined,
      complete: {
        code: (value) => {
          const prefix = String(value).toLocaleLowerCase('fr');
          return TOPONYMS.map((record) => record.code)
            .filter((code) => code.toLocaleLowerCase('fr').startsWith(prefix))
            .slice(0, 100);
        },
        language: (value) =>
          ['fr', 'en', 'both'].filter((language) =>
            language.startsWith(String(value).toLocaleLowerCase('fr')),
          ),
      },
    }),
    {
      title: 'Complete toponym record',
      description:
        'A complete source record addressed by code and language, for example fna://toponyms/Baudin001/both.',
      mimeType: 'application/json',
    },
    async (uri, variables) => {
      const code = String(variables.code);
      const language = String(variables.language);
      if (!['fr', 'en', 'both'].includes(language)) {
        throw new Error(`Unsupported language: ${language}`);
      }
      const record = getToponym(code, language);
      if (!record) throw new Error(`Unknown toponym code: ${code}`);
      return {
        contents: [
          {
            uri: uri.href,
            mimeType: 'application/json',
            text: JSON.stringify(record, null, 2),
          },
        ],
      };
    },
  );

  server.registerResource(
    'route-summary',
    new ResourceTemplate('fna://routes/{expedition}', {
      list: undefined,
      complete: {
        expedition: (value) =>
          ['Baudin', 'Entrecasteaux', 'Flinders'].filter((name) =>
            normalizeText(name).startsWith(normalizeText(value)),
          ),
      },
    }),
    {
      title: 'Route summary for one expedition',
      description:
        'Counts, date ranges, geographic bounds, and qualifier coverage per vessel, for example fna://routes/Flinders.',
      mimeType: 'application/json',
    },
    async (uri, variables) => {
      const expedition = String(variables.expedition);
      if (!['Baudin', 'Entrecasteaux', 'Flinders'].includes(expedition)) {
        throw new Error(`Unknown expedition: ${expedition}`);
      }
      return {
        contents: [
          {
            uri: uri.href,
            mimeType: 'application/json',
            text: JSON.stringify(getRouteSummary({ expedition }), null, 2),
          },
        ],
      };
    },
  );

  server.registerResource(
    'journal-day',
    new ResourceTemplate('fna://journals/{date}', { list: undefined }),
    {
      title: 'One day across every source',
      description:
        'Journal entries, route positions, timeline events, and remarkable dates for one ISO date, for example fna://journals/1802-04-08.',
      mimeType: 'application/json',
    },
    async (uri, variables) => {
      const date = String(variables.date);
      if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) {
        throw new Error(`Invalid date: ${date}`);
      }
      return {
        contents: [
          {
            uri: uri.href,
            mimeType: 'application/json',
            text: JSON.stringify(getJournalDay({ date }), null, 2),
          },
        ],
      };
    },
  );

  return server;
}
