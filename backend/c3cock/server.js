const http = require("node:http");
const fs = require("node:fs/promises");
const path = require("node:path");

const PORT = Number(process.env.PORT || 8102);
const DATA_DIR = path.join(__dirname, "data");
const STATE_FILE = path.join(DATA_DIR, "editor-state.json");

const DEFAULTS = {
  title: "Cages your pet actually likes.",
  lead: "Modular, hand-finished habitats for hamsters, parrots, reptiles, and the small mammals that own the house. Designed around the animal inside, not just the room outside. Built in Karlsruhe. Shipped to wherever the pet is.",
  banner: "",
  chaos: 1,
  hue: "green",
  time: "day",
};

const HUES = new Set(["green", "red", "blue", "purple", "amber"]);
const TIMES = new Set(["day", "night"]);

function clip(value, max) {
  return String(value || "").replace(/[\u0000-\u001f\u007f]/g, " ").trim().slice(0, max);
}

function sanitize(input = {}) {
  return {
    title: clip(input.title || DEFAULTS.title, 120) || DEFAULTS.title,
    lead: clip(input.lead || DEFAULTS.lead, 600) || DEFAULTS.lead,
    banner: clip(input.banner || "", 180),
    chaos: Math.max(0.25, Math.min(3, Number(input.chaos) || DEFAULTS.chaos)),
    hue: HUES.has(input.hue) ? input.hue : DEFAULTS.hue,
    time: TIMES.has(input.time) ? input.time : DEFAULTS.time,
  };
}

async function readState() {
  try {
    const raw = await fs.readFile(STATE_FILE, "utf8");
    const parsed = JSON.parse(raw);
    return {
      ...sanitize(parsed),
      updatedAt: parsed.updatedAt || new Date(0).toISOString(),
    };
  } catch {
    return writeState(DEFAULTS);
  }
}

async function writeState(input) {
  await fs.mkdir(DATA_DIR, { recursive: true });
  const state = {
    ...sanitize(input),
    updatedAt: new Date().toISOString(),
  };
  const tmp = `${STATE_FILE}.tmp`;
  await fs.writeFile(tmp, `${JSON.stringify(state, null, 2)}\n`, "utf8");
  await fs.rename(tmp, STATE_FILE);
  return state;
}

function sendJson(res, status, body) {
  const payload = JSON.stringify(body);
  res.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Content-Length": Buffer.byteLength(payload),
    "Cache-Control": "no-store",
  });
  res.end(payload);
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let body = "";
    req.on("data", (chunk) => {
      body += chunk;
      if (body.length > 16384) {
        reject(new Error("Request body too large"));
        req.destroy();
      }
    });
    req.on("end", () => resolve(body));
    req.on("error", reject);
  });
}

const server = http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url, `http://${req.headers.host || "localhost"}`);

    if (req.method === "GET" && url.pathname === "/api/health") {
      sendJson(res, 200, { ok: true });
      return;
    }

    if (req.method === "GET" && url.pathname === "/api/state") {
      sendJson(res, 200, await readState());
      return;
    }

    if (req.method === "POST" && url.pathname === "/api/state") {
      const body = await readBody(req);
      const parsed = body ? JSON.parse(body) : {};
      const state = await writeState(parsed.state || parsed);
      sendJson(res, 200, state);
      return;
    }

    sendJson(res, 404, { error: "Not found" });
  } catch (error) {
    sendJson(res, 400, { error: error.message || "Bad request" });
  }
});

server.listen(PORT, "127.0.0.1", () => {
  console.log(`c3cock editor API listening on 127.0.0.1:${PORT}`);
});
