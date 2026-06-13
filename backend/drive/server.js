const http = require("node:http");
const fs = require("node:fs/promises");
const path = require("node:path");

const root = __dirname;
const dataFile = path.join(root, "data", "leaderboard.json");
const port = Number(process.env.PORT) || 8097;
const mime = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
};

async function readBody(request) {
  let body = "";
  for await (const chunk of request) {
    body += chunk;
    if (body.length > 4096) throw new Error("Body too large");
  }
  return body;
}

async function loadScores() {
  try {
    return JSON.parse(await fs.readFile(dataFile, "utf8"));
  } catch (error) {
    if (error.code === "ENOENT") return [];
    throw error;
  }
}

async function saveScores(scores) {
  await fs.mkdir(path.dirname(dataFile), { recursive: true });
  await fs.writeFile(dataFile, JSON.stringify(scores, null, 2));
}

function send(response, status, body, type = "application/json; charset=utf-8") {
  response.writeHead(status, {
    "content-type": type,
    "cache-control": "no-store",
  });
  response.end(body);
}

async function handleApi(request, response, pathname) {
  if (pathname !== "/api/leaderboard") return false;

  if (request.method === "GET") {
    const scores = await loadScores();
    send(response, 200, JSON.stringify(scores.slice(0, 10)));
    return true;
  }

  if (request.method === "POST") {
    const payload = JSON.parse(await readBody(request));
    const name = String(payload.name || "Driver").trim().slice(0, 18) || "Driver";
    const time = Number(payload.time);

    if (!Number.isFinite(time) || time < 5000 || time > 600000) {
      send(response, 400, JSON.stringify({ error: "Invalid lap time" }));
      return true;
    }

    const scores = await loadScores();
    scores.push({ name, time: Math.round(time), date: new Date().toISOString() });
    scores.sort((a, b) => a.time - b.time);
    await saveScores(scores.slice(0, 50));
    send(response, 201, JSON.stringify(scores.slice(0, 10)));
    return true;
  }

  send(response, 405, JSON.stringify({ error: "Method not allowed" }));
  return true;
}

async function serveStatic(response, pathname) {
  const requested = pathname === "/" ? "/index.html" : pathname;
  const filePath = path.normalize(path.join(root, requested));

  if (!filePath.startsWith(root) || filePath.includes(`${path.sep}data${path.sep}`)) {
    send(response, 403, "Forbidden", "text/plain; charset=utf-8");
    return;
  }

  try {
    const body = await fs.readFile(filePath);
    response.writeHead(200, {
      "content-type": mime[path.extname(filePath)] || "application/octet-stream",
      "cache-control": requested.endsWith(".html") || requested.endsWith(".js") ? "no-store" : "public, max-age=60",
    });
    response.end(body);
  } catch (error) {
    send(response, 404, "Not found", "text/plain; charset=utf-8");
  }
}

http
  .createServer(async (request, response) => {
    try {
      const url = new URL(request.url, "http://localhost");
      if (await handleApi(request, response, url.pathname)) return;
      await serveStatic(response, url.pathname);
    } catch (error) {
      send(response, 500, JSON.stringify({ error: "Server error" }));
    }
  })
  .listen(port, "127.0.0.1", () => {
    console.log(`Gulasch Drive listening on ${port}`);
  });
