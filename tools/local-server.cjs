const http = require("http");
const fs = require("fs");
const path = require("path");

const PORT = Number(process.env.PORT || 8000);
const HOST = process.env.HOST || "127.0.0.1";
const base = process.cwd();

const mime = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".gif": "image/gif",
  ".webp": "image/webp",
  ".ico": "image/x-icon",
  ".mp3": "audio/mpeg",
  ".wav": "audio/wav",
};

function resolveRequest(urlPathWithQuery) {
  const [rawPath, rawQuery] = decodeURIComponent(urlPathWithQuery || "/").split("?");
  const cleanUrlPath = rawPath || "/";
  const querySuffix = rawQuery ? `?${rawQuery}` : "";
  const initialPath = cleanUrlPath === "/" ? "/index.html" : cleanUrlPath;
  const normalized = path.normalize(initialPath).replace(/^[/\\]+/, "");
  const requestedPath = path.join(base, normalized);

  if (fs.existsSync(requestedPath) && fs.statSync(requestedPath).isFile()) {
    return { type: "file", path: requestedPath };
  }

  if (fs.existsSync(requestedPath) && fs.statSync(requestedPath).isDirectory()) {
    const indexPath = path.join(requestedPath, "index.html");
    if (fs.existsSync(indexPath) && fs.statSync(indexPath).isFile()) {
      return { type: "file", path: indexPath };
    }
  }

  // Redirect extensionless routes to explicit .html so relative assets resolve correctly.
  const noTrailingSlash = normalized.replace(/[\\/]+$/, "");
  if (noTrailingSlash && path.extname(noTrailingSlash) === "") {
    const htmlPath = path.join(base, `${noTrailingSlash}.html`);
    if (fs.existsSync(htmlPath) && fs.statSync(htmlPath).isFile()) {
      return {
        type: "redirect",
        location: `/${noTrailingSlash.replace(/\\/g, "/")}.html${querySuffix}`,
      };
    }
  }

  return { type: "not_found" };
}

const server = http.createServer((req, res) => {
  const resolved = resolveRequest(req.url || "/");

  if (resolved.type === "redirect") {
    res.statusCode = 302;
    res.setHeader("Location", resolved.location);
    res.end();
    return;
  }

  if (resolved.type !== "file") {
    res.statusCode = 404;
    res.setHeader("Content-Type", "text/plain; charset=utf-8");
    res.end(
      "Error response\nError code: 404\n\nMessage: File not found.\n\nError code explanation: 404 - Nothing matches the given URI.\n"
    );
    return;
  }

  fs.readFile(resolved.path, (readErr, data) => {
    if (readErr) {
      res.statusCode = 404;
      res.setHeader("Content-Type", "text/plain; charset=utf-8");
      res.end(
        "Error response\nError code: 404\n\nMessage: File not found.\n\nError code explanation: 404 - Nothing matches the given URI.\n"
      );
      return;
    }

    const ext = path.extname(resolved.path).toLowerCase();
    res.statusCode = 200;
    res.setHeader("Content-Type", mime[ext] || "application/octet-stream");
    res.end(data);
  });
});

server.listen(PORT, HOST, () => {
  console.log(`Local server running at http://${HOST}:${PORT}/`);
});
