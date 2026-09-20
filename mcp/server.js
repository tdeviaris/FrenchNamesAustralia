import { McpServer, ResourceTemplate } from '@modelcontextprotocol/sdk/server/mcp.js';

import { TOPONYMS } from './data-store.js';
import {
  AnalyzeToponymsSchema,
  GetToponymSchema,
  NearbyToponymsSchema,
  SearchTimelineSchema,
  SearchToponymsSchema,
} from './schemas.js';
import {
  analyzeToponyms,
  findNearbyToponyms,
  getDatasetSummary,
  getToponym,
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
        'Read-only access to French toponyms in Australia. Prefer get_toponym for complete bilingual narratives, find_nearby_toponyms for coordinates, and analyze_toponyms for exhaustive statistics.',
    },
  );

  server.registerTool(
    'search_toponyms',
    {
      title: 'Search Australian French toponyms',
      description:
        'Search names, Indigenous names, French/English characteristics, and French/English history. Detailed lists are paginated; use the returned cursor for the next page.',
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
        'Return the complete, untruncated source record for a code such as Baudin001, including coordinates and full French/English characteristic and history fields.',
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
        'Search 125 bilingual chronological events by text, date interval, vessel, and interpolation status.',
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
        'Return corpus size, coordinate bounds, invariants, primary fields, sources, and completeness statistics.',
      annotations: READ_ONLY_ANNOTATIONS,
    },
    async () => result(getDatasetSummary()),
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

  return server;
}
