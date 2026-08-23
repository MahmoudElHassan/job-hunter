/**
 * Vercel serverless: delete one row from data/Job_Listings.csv on main.
 *
 * Env (set in Vercel project settings):
 *   DELETE_KEY   — passphrase prompted from the cover-letter UI
 *   GITHUB_TOKEN — fine-grained PAT with contents:write on this repo
 *   GITHUB_REPO  — optional, default MahmoudElHassan/job-hunter
 *
 * Body JSON: { "id": "JOB-…", "key": "<DELETE_KEY>" }
 */
const ALLOWED_ORIGINS = [
  "https://mahmoudelhassan.github.io",
  "http://localhost:3000",
  "http://127.0.0.1:3000",
  "http://localhost:5500",
  "http://127.0.0.1:5500",
];

const CSV_PATH = "data/Job_Listings.csv";

function corsHeaders(origin) {
  const allow = ALLOWED_ORIGINS.includes(origin) ? origin : ALLOWED_ORIGINS[0];
  return {
    "Access-Control-Allow-Origin": allow,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "86400",
  };
}

function parseCsvRows(text) {
  const lines = text.replace(/^\uFEFF/, "").split(/\r?\n/);
  if (!lines.length) return { header: "", rows: [] };
  const header = lines[0];
  const rows = [];
  for (let i = 1; i < lines.length; i++) {
    const line = lines[i];
    if (!line.trim()) continue;
    // id is the first column; handle quoted values
    let id = "";
    if (line.startsWith('"')) {
      const end = line.indexOf('"', 1);
      id = end > 0 ? line.slice(1, end) : line;
    } else {
      const comma = line.indexOf(",");
      id = comma >= 0 ? line.slice(0, comma) : line;
    }
    rows.push({ id: id.trim(), line });
  }
  return { header, rows };
}

module.exports = async function handler(req, res) {
  const origin = req.headers.origin || "";
  const headers = corsHeaders(origin);

  if (req.method === "OPTIONS") {
    res.writeHead(204, headers);
    res.end();
    return;
  }

  if (req.method !== "POST") {
    res.writeHead(405, { ...headers, "Content-Type": "application/json" });
    res.end(JSON.stringify({ ok: false, error: "Method not allowed" }));
    return;
  }

  const deleteKey = process.env.DELETE_KEY || "";
  const githubToken = process.env.GITHUB_TOKEN || "";
  const repo = process.env.GITHUB_REPO || "MahmoudElHassan/job-hunter";

  if (!deleteKey || !githubToken) {
    res.writeHead(503, { ...headers, "Content-Type": "application/json" });
    res.end(
      JSON.stringify({
        ok: false,
        error:
          "Delete API not configured. Set DELETE_KEY and GITHUB_TOKEN on Vercel, " +
          "or run locally: python3 scripts/delete_listing.py JOB-xxx",
      })
    );
    return;
  }

  let body = req.body;
  if (typeof body === "string") {
    try {
      body = JSON.parse(body || "{}");
    } catch {
      body = {};
    }
  }
  body = body || {};

  const id = String(body.id || "").trim();
  const key = String(body.key || "");

  if (!id) {
    res.writeHead(400, { ...headers, "Content-Type": "application/json" });
    res.end(JSON.stringify({ ok: false, error: "Missing id" }));
    return;
  }

  if (key !== deleteKey) {
    res.writeHead(401, { ...headers, "Content-Type": "application/json" });
    res.end(JSON.stringify({ ok: false, error: "Invalid delete key" }));
    return;
  }

  try {
    const getUrl = `https://api.github.com/repos/${repo}/contents/${CSV_PATH}?ref=main`;
    const getResp = await fetch(getUrl, {
      headers: {
        Authorization: `Bearer ${githubToken}`,
        Accept: "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "job-hunter-delete-listing",
      },
    });
    if (!getResp.ok) {
      const t = await getResp.text();
      res.writeHead(502, { ...headers, "Content-Type": "application/json" });
      res.end(
        JSON.stringify({
          ok: false,
          error: `GitHub read failed (${getResp.status}): ${t.slice(0, 200)}`,
        })
      );
      return;
    }
    const file = await getResp.json();
    const csvText = Buffer.from(file.content, "base64").toString("utf8");
    const { header, rows } = parseCsvRows(csvText);
    const before = rows.length;
    const kept = rows.filter((r) => r.id !== id);
    if (kept.length === before) {
      res.writeHead(404, { ...headers, "Content-Type": "application/json" });
      res.end(JSON.stringify({ ok: false, error: `Job id not found: ${id}` }));
      return;
    }

    const newCsv = [header, ...kept.map((r) => r.line)].join("\n") + "\n";
    const putResp = await fetch(
      `https://api.github.com/repos/${repo}/contents/${CSV_PATH}`,
      {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${githubToken}`,
          Accept: "application/vnd.github+json",
          "X-GitHub-Api-Version": "2022-11-28",
          "User-Agent": "job-hunter-delete-listing",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: `chore: delete listing ${id} via cover-letter board`,
          content: Buffer.from(newCsv, "utf8").toString("base64"),
          sha: file.sha,
          branch: "main",
        }),
      }
    );
    if (!putResp.ok) {
      const t = await putResp.text();
      res.writeHead(502, { ...headers, "Content-Type": "application/json" });
      res.end(
        JSON.stringify({
          ok: false,
          error: `GitHub write failed (${putResp.status}): ${t.slice(0, 200)}`,
        })
      );
      return;
    }

    res.writeHead(200, { ...headers, "Content-Type": "application/json" });
    res.end(
      JSON.stringify({
        ok: true,
        id,
        remaining: kept.length,
      })
    );
  } catch (e) {
    res.writeHead(500, { ...headers, "Content-Type": "application/json" });
    res.end(
      JSON.stringify({
        ok: false,
        error: e && e.message ? e.message : "Unexpected error",
      })
    );
  }
};
