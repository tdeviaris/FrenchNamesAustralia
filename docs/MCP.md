# French Names Australia MCP server

This repository contains a read-only Model Context Protocol server for the French Names Australia datasets.

## Scope

The server exposes:

- 671 toponym records from the Baudin and d'Entrecasteaux expeditions;
- 125 events from the Baudin expedition timeline;
- latitude and longitude for every toponym;
- complete French and English characteristics;
- complete French and English history;
- structured, exhaustive statistics over the matching corpus.

The JSON files in `data/` remain the sources of truth. The MCP server does not call an LLM and does not modify the datasets.

## Endpoint

Local development:

```text
http://localhost:3000/api/mcp
```

Production, after deployment:

```text
https://french-names-australia.vercel.app/api/mcp
```

The endpoint uses stateless Streamable HTTP with JSON responses.

## Tools

| Tool | Purpose |
| --- | --- |
| `search_toponyms` | Search names, Indigenous names, characteristics, and history in French or English. |
| `get_toponym` | Retrieve one complete, untruncated record by code. |
| `find_nearby_toponyms` | Find records around a latitude and longitude using Haversine distance. |
| `analyze_toponyms` | Calculate exhaustive statistics, field coverage, distinct counts, and geographic summaries. |
| `search_timeline` | Search timeline events by text, date, vessel, and interpolation status. |
| `get_dataset_summary` | Inspect corpus size, sources, coordinate bounds, and integrity invariants. |

Detailed result lists are paginated. Pagination never limits `analyze_toponyms`: statistics always use every matching record and return `truncated: false`.

## Resources

```text
fna://dataset/summary
fna://toponyms/{code}/{language}
```

Example:

```text
fna://toponyms/Baudin001/both
```

Supported languages are `fr`, `en`, and `both`.

## Local development

Install dependencies and run the tests:

```bash
npm install
npm test
```

Start the local Vercel environment:

```bash
vercel dev
```

The website remains available at `http://localhost:3000` and the MCP endpoint at `http://localhost:3000/api/mcp`.

## MCP Inspector

Start the official inspector:

```bash
npx @modelcontextprotocol/inspector
```

In the inspector, select Streamable HTTP and enter:

```text
http://localhost:3000/api/mcp
```

Use **List Tools**, then call `get_dataset_summary` or `analyze_toponyms`.

## Client configuration

The generic configuration for a Streamable HTTP compatible client is:

```json
{
  "mcpServers": {
    "french-names-australia": {
      "url": "https://french-names-australia.vercel.app/api/mcp"
    }
  }
}
```

Do not use the production URL until the MCP route has been deployed and verified.

## Query examples

Search the French history fields:

```json
{
  "query": "relations scientifiques",
  "language": "fr",
  "fields": ["history"],
  "limit": 50
}
```

Find records around a coordinate:

```json
{
  "latitude": -38.85044,
  "longitude": 146.07164,
  "radiusKm": 100,
  "language": "both",
  "limit": 100
}
```

Count the complete corpus by expedition and state:

```json
{
  "groupBy": ["expedition", "state"],
  "distinctBy": ["code"]
}
```

## Security

- All tools are marked read-only, non-destructive, and idempotent.
- There is no arbitrary SQL, filesystem path, or URL input.
- Inputs are validated with Zod and detailed lists are capped at 200 records per page.
- Unknown browser origins and host headers are rejected.
- Server-side MCP clients may connect without an `Origin` header.
- The current MVP does not implement authentication because it exposes public academic data only.
- Configure `MCP_ALLOWED_ORIGINS` and `MCP_ALLOWED_HOSTS` as comma-separated environment variables if additional domains are required.

Before a public production launch, configure monitoring and reasonable traffic protection in Vercel.
