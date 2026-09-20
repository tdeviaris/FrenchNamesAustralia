# French Names Australia MCP server

This repository contains a read-only Model Context Protocol server for the French Names Australia datasets.

## Scope

The server exposes:

- 1021 toponym records from the Baudin, d'Entrecasteaux, and Flinders expeditions;
- 1875 dated route positions for the three expeditions, plus 7 vessel trajectories;
- 2086 day entries from the five transcribed onboard journals;
- 125 events from the Baudin expedition timeline;
- 73 bilingual remarkable dates covering the three expeditions;
- latitude and longitude for every located toponym;
- complete French and English characteristics and history;
- 343 French translations of Flinders quotations and 143 Hakluyt attributions;
- structured, exhaustive statistics over the matching corpus.

The JSON and GeoJSON files in `data/` remain the sources of truth. The MCP server does not call an LLM and does not modify the datasets.

### Known data caveats

- 32 toponyms carry no coordinates (7 Baudin, 25 Flinders). They are returned with `located: false`, excluded from every geographic filter, and listed under `invariants.unlocatedCodes`.
- The published route tables sometimes record a position under a collective label, which does not name the same hulls throughout the voyage. The server resolves those labels and never returns one as a vessel. See **Collective labels** below.
- `data/retour_naturaliste.json` and `data/flinders_carte_releves.json` are already folded into the route GeoJSON files, which the server treats as the single source for routes.
- State codes are spelled inconsistently across corpora (`Tas` and `QLD`). All state matching ignores case.

## Endpoint

The endpoint is live, public, and needs no key:

```text
https://www.frenchplacenames.au/api/mcp
https://french-names-australia.vercel.app/api/mcp
```

While developing, `npm run mcp:dev` serves the same handler at `http://localhost:3333/api/mcp`, and `vercel dev` at `http://localhost:3000/api/mcp`.

The endpoint uses stateless Streamable HTTP with JSON responses. Since it is already public, **a deployment publishes whatever the repository holds** — check `npm test` and `npm run mcp:smoke` before shipping.

## Tools

| Tool | Purpose |
| --- | --- |
| `search_toponyms` | Search names, Indigenous names, characteristics, history, French quotations, attributions, and Flinders classification, in French or English. |
| `get_toponym` | Retrieve one complete, untruncated record by code, quotation and attribution included. |
| `find_nearby_toponyms` | Find records around a latitude and longitude using Haversine distance. |
| `analyze_toponyms` | Calculate exhaustive statistics, field coverage, distinct counts, and geographic summaries. |
| `search_route_positions` | Search the daily route positions by expedition, vessel, date, area, and route qualifier. |
| `get_route_summary` | Aggregate the routes by expedition, vessel, year, section, or route table. |
| `search_journals` | Full-text search across the five transcribed journals. |
| `get_journal_day` | Read one ISO date across every journal, route position, timeline event, and milestone. |
| `search_timeline` | Search Baudin timeline events by text, date, vessel, and interpolation status. |
| `list_remarkable_dates` | List the milestone dates of the three expeditions, in French and English. |
| `get_dataset_summary` | Inspect corpus size, sources, coordinate and date bounds, and integrity invariants. |

Detailed result lists are paginated. Pagination never limits `analyze_toponyms`, `get_route_summary`, or `get_journal_day`: they always use every matching record and return `truncated: false`.

### Route qualifiers

### Vessels

Every position carries:

| Field | Meaning |
| --- | --- |
| `navires` | The hulls the reading actually places. This is the authoritative field. |
| `navire` | Those hulls as one label, for example `le Géographe et le Naturaliste`. |
| `navireSource` | The label as the published route table wrote it, kept for traceability. |
| `navireCollectif` | Whether that source label was a collective one. |

The `vessel` filter matches `navires` and `navireSource`, ignoring case and accents. Asking for `le Géographe` therefore returns every reading that places it, not only the days it held its own table.

### Collective labels

`les corvettes` is a misleading label: it does not designate the same pair from one end of the voyage to the other. The server resolves it exactly as `map.html` does when it draws the routes:

1. Until 18 November 1802, when the Naturaliste left Port Jackson for France, it means the Géographe and the Naturaliste. After that date it means the Géographe and the Casuarina, bought on the spot.
2. When a companion holds its own table on the same day, it was surveyed separately, so the collective position is the flagship's alone.

The Recherche and the Espérance sailed in company for the whole d'Entrecasteaux expedition; the tables record a single position for both, and every one of those positions names the two ships.

Resolved, the readings place the hulls as follows:

| Hull | Readings | Own tables |
| --- | --- | --- |
| le Naturaliste | 702 | 387 |
| le Géographe | 695 | 202 |
| la Recherche | 535 | — |
| l'Espérance | 535 | — |
| le Casuarina | 215 | 70 |
| l'Investigator | 158 | 158 |
| le Cumberland | 25 | 25 |
| le Porpoise | 5 | 5 |

Group `get_route_summary` by `coque` to count one row per ship, a shared reading counting for each; by `navire` for the reconciled pairs; by `navireSource` to go back to the published tables.

`search_route_positions` accepts a `flags` object built from these qualifiers, each a boolean:

`extrapole`, `mouillage`, `contournement`, `renfloue`, `de_conserve`, `releve_corrige`, `releve_carte`.

### Journal sources

`baudin`, `baudin_bnf`, `breton`, `anonyme`, `geographe`.

`baudin_bnf` is the transcription of the BnF manuscript; each entry carries its `entete`, its republican date, and the `etat` of the reading.

## Resources

```text
fna://dataset/summary
fna://toponyms/{code}/{language}
fna://routes/{expedition}
fna://journals/{date}
```

Examples:

```text
fna://toponyms/Flinders055/both
fna://routes/Flinders
fna://journals/1802-04-08
```

Supported languages are `fr`, `en`, and `both`. Supported expeditions are `Baudin`, `Entrecasteaux`, and `Flinders`.

## Test environment

Four npm scripts. None of them needs Vercel, a network, or an API key.

```bash
npm install
npm test            # 30 tests over the datasets, the queries, and the MCP transport
npm run mcp:smoke   # calls every tool and resource once, and reports
npm run mcp:dev     # HTTP endpoint on http://localhost:3333/api/mcp
npm run mcp:stdio   # stdio endpoint, for local MCP clients
npm run mcp:inspect # the official MCP Inspector, wired to the stdio endpoint
```

`npm run mcp:dev` mounts the very same handler that Vercel deploys as `api/mcp.js`, behind a plain Node HTTP server. Origin and host checks, transport, and tools are identical to production, so what passes locally holds once deployed. Pass `--port` to move it:

```bash
npm run mcp:dev -- --port 4000
```

`npm run mcp:smoke` is the quickest way to see the whole surface answer at once. It prints, per tool, the response time, the weight of the payload in a context window, and a one-line reading of the result:

```text
  ok   get_dataset_summary        5 ms     5 Ko  1021 toponymes, 1875 positions, 2086 jours de journal
  ok   search_route_positions     4 ms     3 Ko  695 relevés placent le Géographe
  ok   get_route_summary          5 ms     6 Ko  le Naturaliste 702, le Géographe 695, l'Espérance 535, …
```

It runs in memory by default. Point it at a running endpoint, local or deployed, to test the network path:

```bash
npm run mcp:smoke -- --url http://localhost:3333/api/mcp
npm run mcp:smoke -- --url https://www.frenchplacenames.au/api/mcp
```

Exit code 1 on any failure, so it fits a CI step.

### By hand

```bash
curl -s -X POST http://localhost:3333/api/mcp \
  -H 'content-type: application/json' \
  -H 'accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

### MCP Inspector

```bash
npm run mcp:inspect
```

The inspector opens in the browser, already connected over stdio. To inspect the HTTP endpoint instead, run `npm run mcp:dev` in one terminal, `npx @modelcontextprotocol/inspector` in another, choose **Streamable HTTP**, and enter `http://localhost:3333/api/mcp`.

### With Vercel

`vercel dev` still works and serves the website alongside the endpoint, at `http://localhost:3000/api/mcp`. It is the right check before deploying; `npm run mcp:dev` is the faster loop while developing.

## Calling the server from an LLM

The server is public and needs no key. Two transports are available, and the right one depends on the client:

| Transport | Endpoint | For |
| --- | --- | --- |
| Streamable HTTP | `https://www.frenchplacenames.au/api/mcp` | Remote clients: Claude.ai, ChatGPT, the Anthropic and OpenAI APIs, anything hosted |
| stdio | `node mcp/bin/stdio.js` | Local clients on a machine holding a clone: Claude Desktop, Claude Code, IDEs |

Prefer HTTP whenever the client supports it: no clone, no Node, and every client sees the same deployed version.

### Claude Code

```bash
claude mcp add --transport http french-names-australia https://www.frenchplacenames.au/api/mcp
```

From a clone, over stdio:

```bash
claude mcp add french-names-australia -- node /absolute/path/to/FrenchNamesAustralia/mcp/bin/stdio.js
```

### Claude Desktop, and any client taking an `mcpServers` block

Remote, in `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "french-names-australia": {
      "url": "https://www.frenchplacenames.au/api/mcp"
    }
  }
}
```

Local, from a clone:

```json
{
  "mcpServers": {
    "french-names-australia": {
      "command": "node",
      "args": ["/absolute/path/to/FrenchNamesAustralia/mcp/bin/stdio.js"]
    }
  }
}
```

The path must be absolute: the client does not start in the repository.

### VS Code

In `.vscode/mcp.json`:

```json
{
  "servers": {
    "french-names-australia": {
      "type": "http",
      "url": "https://www.frenchplacenames.au/api/mcp"
    }
  }
}
```

### Claude API, from your own code

The MCP connector needs two halves in the same request: the server under `mcp_servers`, and a matching toolset under `tools`. Passing only the first is a validation error. Beta header `mcp-client-2025-11-20`.

```python
import anthropic

client = anthropic.Anthropic()

response = client.beta.messages.create(
    model="claude-opus-5",
    max_tokens=16000,
    betas=["mcp-client-2025-11-20"],
    mcp_servers=[{
        "type": "url",
        "url": "https://www.frenchplacenames.au/api/mcp",
        "name": "french-names-australia",
    }],
    tools=[{"type": "mcp_toolset", "mcp_server_name": "french-names-australia"}],
    messages=[{
        "role": "user",
        "content": "Où était le Géographe le 8 avril 1802, et que dit le journal de ce jour-là ?",
    }],
)
```

Not available on Amazon Bedrock, Vertex AI, or Microsoft Foundry.

### OpenAI API, from your own code

```javascript
const response = await openai.responses.create({
  model: 'gpt-4.1',
  input: "Combien de toponymes Flinders a-t-il laissés en Tasmanie ?",
  tools: [{
    type: 'mcp',
    server_label: 'french_names_australia',
    server_url: 'https://www.frenchplacenames.au/api/mcp',
    require_approval: 'never',
  }],
});
```

### Pointing a client at a local build

Any of the HTTP configurations above accepts `http://localhost:3333/api/mcp` once `npm run mcp:dev` is running. Localhost is allowed by the origin and host checks. A hosted LLM, on the other hand, cannot reach your machine: testing an unreleased change from Claude.ai or the OpenAI API means deploying it first.

### What to tell the model

The server already describes itself: the `instructions` it returns on connection state the corpora, the vessel reconciliation, and which tool to prefer. Worth adding on your side is only what the server cannot know — that quotations and attributions exist for Flinders alone, and that narrative fields come in French and English.

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

Find the Flinders toponyms named from the Investigator's crew:

```json
{
  "expedition": "Flinders",
  "query": "Investigator",
  "fields": ["classification"],
  "limit": 100
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

Every position of the Espérance, which is also every position of the Recherche:

```json
{
  "vessel": "l'Espérance"
}
```

Every reading that places the Géographe, its own tables and the collective ones alike:

```json
{
  "vessel": "le Géographe"
}
```

One row per hull, across the three expeditions:

```json
{
  "groupBy": ["coque"]
}
```

Where the Géographe lay at anchor during April 1802:

```json
{
  "vessel": "le Géographe",
  "dateFrom": "1802-04-01",
  "dateTo": "1802-04-30",
  "flags": { "mouillage": true }
}
```

Compare the three expeditions year by year:

```json
{
  "groupBy": ["expedition", "year"]
}
```

Read one day across every source:

```json
{
  "date": "1802-04-08"
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

## Footprint

Loading every dataset takes about 280 ms and roughly 120 MB of heap on a cold start. The two Natural Earth basemap files in `data/` are never loaded by the server.
