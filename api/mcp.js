import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js';

import { createFrenchNamesMcpServer } from '../mcp/server.js';

const STATIC_ALLOWED_ORIGINS = new Set([
  'https://french-names-australia.vercel.app',
  'https://www.frenchplacenames.au',
  'https://frenchplacenames.au',
  'https://www.frenchplacenames.com',
  'https://frenchplacenames.com',
]);

const STATIC_ALLOWED_HOSTS = new Set([
  'french-names-australia.vercel.app',
  'www.frenchplacenames.au',
  'frenchplacenames.au',
  'www.frenchplacenames.com',
  'frenchplacenames.com',
]);

function configuredValues(name) {
  return String(process.env[name] ?? '')
    .split(',')
    .map((value) => value.trim())
    .filter(Boolean);
}

function isAllowedOrigin(origin) {
  if (!origin) return true;
  if (STATIC_ALLOWED_ORIGINS.has(origin)) return true;
  if (configuredValues('MCP_ALLOWED_ORIGINS').includes(origin)) return true;
  try {
    const url = new URL(origin);
    return ['localhost', '127.0.0.1', '[::1]'].includes(url.hostname);
  } catch {
    return false;
  }
}

function isAllowedHost(hostHeader) {
  if (!hostHeader) return false;
  const host = hostHeader.toLocaleLowerCase('en').replace(/:\d+$/, '');
  if (['localhost', '127.0.0.1', '[::1]'].includes(host)) return true;
  if (STATIC_ALLOWED_HOSTS.has(host)) return true;
  const configuredHosts = configuredValues('MCP_ALLOWED_HOSTS').map((value) =>
    value.toLocaleLowerCase('en'),
  );
  if (configuredHosts.includes(host)) return true;
  return Boolean(process.env.VERCEL_URL && host === process.env.VERCEL_URL.toLocaleLowerCase('en'));
}

function setCorsHeaders(req, res) {
  const origin = req.headers.origin;
  if (origin && isAllowedOrigin(origin)) {
    res.setHeader('Access-Control-Allow-Origin', origin);
    res.setHeader('Vary', 'Origin');
  }
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader(
    'Access-Control-Allow-Headers',
    'Content-Type, Authorization, MCP-Protocol-Version, MCP-Session-Id, Last-Event-Id',
  );
  res.setHeader(
    'Access-Control-Expose-Headers',
    'MCP-Protocol-Version, MCP-Session-Id, Last-Event-Id',
  );
}

function jsonRpcError(res, status, code, message) {
  res.status(status).json({
    jsonrpc: '2.0',
    error: { code, message },
    id: null,
  });
}

export default async function handler(req, res) {
  setCorsHeaders(req, res);

  if (!isAllowedOrigin(req.headers.origin)) {
    jsonRpcError(res, 403, -32000, 'Origin not allowed');
    return;
  }

  const forwardedHost = String(req.headers['x-forwarded-host'] ?? '').split(',')[0].trim();
  const host = forwardedHost || req.headers.host;
  if (!isAllowedHost(host)) {
    jsonRpcError(res, 403, -32000, 'Host not allowed');
    return;
  }

  if (req.method === 'OPTIONS') {
    res.status(204).end();
    return;
  }

  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST, OPTIONS');
    jsonRpcError(res, 405, -32000, 'Method not allowed');
    return;
  }

  const server = createFrenchNamesMcpServer();
  const transport = new StreamableHTTPServerTransport({
    sessionIdGenerator: undefined,
    enableJsonResponse: true,
  });
  let closed = false;
  const close = async () => {
    if (closed) return;
    closed = true;
    await transport.close().catch(() => undefined);
    await server.close().catch(() => undefined);
  };

  res.on('close', close);

  try {
    await server.connect(transport);
    await transport.handleRequest(req, res, req.body);
  } catch (error) {
    console.error('MCP request failed:', error);
    if (!res.headersSent) {
      jsonRpcError(res, 500, -32603, 'Internal MCP server error');
    }
  } finally {
    if (res.writableEnded) await close();
  }
}
