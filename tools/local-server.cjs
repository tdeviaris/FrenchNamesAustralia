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

const server = http.createServer((req, res) => {
  const urlPath = decodeURIComponent((req.url || "/").split("?")[0]);
  let relativePath = urlPath === "/" ? "/index.html" : urlPath;
  let fullPath = path.join(base, relativePath);

  fs.stat(fullPath, (statErr, stats) => {
    if (!statErr && stats.isDirectory()) {
      fullPath = path.join(fullPath, "index.html");
    }

    fs.readFile(fullPath, (readErr, data) => {
      if (readErr) {
        res.statusCode = 404;
        res.setHeader("Content-Type", "text/plain; charset=utf-8");
        res.end(
          "Error response\nError code: 404\n\nMessage: File not found.\n\nError code explanation: 404 - Nothing matches the given URI.\n"
        );
        return;
      }

      const ext = path.extname(fullPath).toLowerCase();
      res.statusCode = 200;
      res.setHeader("Content-Type", mime[ext] || "application/octet-stream");
      res.end(data);
    });
  });
});

server.listen(PORT, HOST, () => {
  console.log(`Local server running at http://${HOST}:${PORT}/`);
});
