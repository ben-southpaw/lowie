// Lowie Worn counter: one shared font, kept in one Durable Object.
//
// The page connects over a WebSocket, sends the letters it typed, and hears
// everyone else's. Plain HTTP routes do the same for clients without sockets.
//
//   GET  /api/state   current edition, counts, typists, people here now
//   POST /api/press   { l: "letters", u: "client id" }
//   GET  /api/ws      WebSocket: send { t: "p", l, u }, receive state and presses

import { DurableObject } from "cloudflare:workers";

const LETTERS = "abcdefghijklmnopqrstuvwxyz";
const H = 60;            // must match the page: a letter is half worn at 60 presses
const MAX_BATCH = 140;   // the page's textarea limit

const num = (v, d) => { const n = Number(v); return Number.isFinite(n) && n > 0 ? Math.floor(n) : d };
function limits(env) {
  const endWear = Math.min(0.95, Number(env.END_WEAR) || 0.8);
  return {
    endCount: num(env.END_COUNT, Math.round(endWear * H / (1 - endWear))),  // 240 presses at 80% worn
    perLetterDay: num(env.PER_LETTER_DAY, 40),
    perDay: num(env.PER_DAY, 600),
  };
}
const cleanLetters = s => typeof s === "string" ? s.toLowerCase().replace(/[^a-z]/g, "").slice(0, MAX_BATCH) : "";
const cleanUid = s => typeof s === "string" && /^[a-z0-9]{8,40}$/i.test(s) ? s : null;
const today = () => new Date().toISOString().slice(0, 10);

async function sha(text) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(buf)].slice(0, 12).map(b => b.toString(16).padStart(2, "0")).join("");
}

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    const origin = req.headers.get("Origin") || "";
    const allowed = (env.ALLOWED_ORIGINS || "").split(",").map(s => s.trim()).filter(Boolean);
    const known = allowed.includes(origin);
    const cors = known ? {
      "Access-Control-Allow-Origin": origin, "Vary": "Origin",
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type", "Access-Control-Max-Age": "86400",
    } : { "Access-Control-Allow-Origin": "*" };

    if (req.method === "OPTIONS") return new Response(null, { status: known ? 204 : 403, headers: cors });
    if (!url.pathname.startsWith("/api/")) return new Response("Lowie Worn counter. The page lives at https://ben-southpaw.github.io/lowie/worn/", { status: 404 });

    // Reading the counts is public. Writing needs a page we know.
    const writes = url.pathname === "/api/ws" || req.method === "POST";
    if (writes && !known) return new Response("Origin not allowed", { status: 403, headers: cors });

    const stub = env.FONT.get(env.FONT.idFromName("lowie"));
    const res = await stub.fetch(req);
    if (res.status === 101) return res;
    const out = new Response(res.body, res);
    for (const [k, v] of Object.entries(cors)) out.headers.set(k, v);
    return out;
  },
};

export class Font extends DurableObject {
  constructor(ctx, env) {
    super(ctx, env);
    this.lim = limits(env);
    const sql = this.sql = ctx.storage.sql;
    sql.exec("CREATE TABLE IF NOT EXISTS counts (letter TEXT PRIMARY KEY, n INTEGER NOT NULL)");
    sql.exec("CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT NOT NULL)");
    sql.exec("CREATE TABLE IF NOT EXISTS typists (uid TEXT PRIMARY KEY)");
    sql.exec("CREATE TABLE IF NOT EXISTS quota (day TEXT NOT NULL, who TEXT NOT NULL, letter TEXT NOT NULL, n INTEGER NOT NULL, PRIMARY KEY (day, who, letter))");
    sql.exec("CREATE TABLE IF NOT EXISTS editions (edition INTEGER PRIMARY KEY, started INTEGER NOT NULL, ended INTEGER NOT NULL, counts TEXT NOT NULL, typists INTEGER NOT NULL)");
    if (!this.meta("edition")) {
      this.setMeta("edition", "1");
      this.setMeta("started", String(Date.now()));
      this.setMeta("salt", crypto.randomUUID());
    }
  }

  meta(k) { const r = this.sql.exec("SELECT v FROM meta WHERE k = ?", k).toArray(); return r.length ? r[0].v : null }
  setMeta(k, v) { this.sql.exec("INSERT INTO meta (k, v) VALUES (?, ?) ON CONFLICT (k) DO UPDATE SET v = excluded.v", k, v) }

  counts() {
    const out = {};
    for (const r of this.sql.exec("SELECT letter, n FROM counts")) out[r.letter] = r.n;
    return out;
  }
  here(except) { return this.ctx.getWebSockets().filter(ws => ws !== except && ws.readyState === 1).length }
  state(except) {
    return {
      edition: Number(this.meta("edition")),
      started: Number(this.meta("started")),
      counts: this.counts(),
      typists: this.sql.exec("SELECT COUNT(*) AS n FROM typists").one().n,
      here: this.here(except),
      endCount: this.lim.endCount,
      past: this.sql.exec("SELECT edition, started, ended, typists FROM editions ORDER BY edition").toArray(),
    };
  }

  // A visitor is a hash of their IP and the day, salted. Raw IPs are never stored,
  // and yesterday's hashes are deleted, so nobody can be followed across days.
  async who(ip) { return sha(this.meta("salt") + "|" + today() + "|" + (ip || "unknown")) }

  press(letters, who, uid) {
    const day = today(), { perLetterDay, perDay, endCount } = this.lim;
    this.sql.exec("DELETE FROM quota WHERE day < ?", day);
    const used = {}; let total = 0;
    for (const r of this.sql.exec("SELECT letter, n FROM quota WHERE day = ? AND who = ?", day, who)) { used[r.letter] = r.n; total += r.n }
    const add = {}; let accepted = "";
    for (const ch of letters) {
      if (total >= perDay) break;
      if ((used[ch] || 0) + (add[ch] || 0) >= perLetterDay) continue;
      add[ch] = (add[ch] || 0) + 1; total++; accepted += ch;
    }
    for (const [L, n] of Object.entries(add)) {
      this.sql.exec("INSERT INTO quota (day, who, letter, n) VALUES (?, ?, ?, ?) ON CONFLICT (day, who, letter) DO UPDATE SET n = n + excluded.n", day, who, L, n);
      this.sql.exec("INSERT INTO counts (letter, n) VALUES (?, ?) ON CONFLICT (letter) DO UPDATE SET n = n + excluded.n", L, n);
    }
    if (accepted && uid) this.sql.exec("INSERT OR IGNORE INTO typists (uid) VALUES (?)", uid);

    // An edition ends when every letter is worn past the line. Then the font starts fresh.
    let ended = null;
    const c = this.counts();
    if (accepted && [...LETTERS].every(L => (c[L] || 0) >= endCount)) {
      const ed = Number(this.meta("edition")), started = Number(this.meta("started")), now = Date.now();
      const typists = this.sql.exec("SELECT COUNT(*) AS n FROM typists").one().n;
      this.sql.exec("INSERT INTO editions (edition, started, ended, counts, typists) VALUES (?, ?, ?, ?, ?)", ed, started, now, JSON.stringify(c), typists);
      this.sql.exec("DELETE FROM counts");
      this.sql.exec("DELETE FROM typists");
      this.setMeta("edition", String(ed + 1));
      this.setMeta("started", String(now));
      ended = ed;
    }
    return { accepted, capped: accepted.length < letters.length, ended };
  }

  broadcast(msg, except) {
    const s = JSON.stringify(msg);
    for (const ws of this.ctx.getWebSockets()) if (ws !== except) { try { ws.send(s) } catch (e) {} }
  }

  async fetch(req) {
    const url = new URL(req.url), ip = req.headers.get("CF-Connecting-IP");
    const json = (o, status = 200) => new Response(JSON.stringify(o), { status, headers: { "Content-Type": "application/json", "Cache-Control": "no-store" } });

    if (url.pathname === "/api/ws") {
      if (req.headers.get("Upgrade") !== "websocket") return new Response("Expected a WebSocket", { status: 426 });
      const pair = new WebSocketPair(), [client, server] = Object.values(pair);
      this.ctx.acceptWebSocket(server);
      server.serializeAttachment({ ip });
      server.send(JSON.stringify(Object.assign({ t: "state" }, this.state())));
      this.broadcast({ t: "here", here: this.here() }, server);
      return new Response(null, { status: 101, webSocket: client });
    }
    if (url.pathname === "/api/state" && req.method === "GET") return json(this.state());
    if (url.pathname === "/api/press" && req.method === "POST") {
      let body = null; try { body = await req.json() } catch (e) {}
      const letters = cleanLetters(body && body.l);
      if (!letters) return json({ error: "No letters" }, 400);
      const r = this.press(letters, await this.who(ip), cleanUid(body.u));
      this.after(r, null);
      return json(Object.assign({ accepted: r.accepted.length, capped: r.capped }, this.state()));
    }
    return json({ error: "Not found" }, 404);
  }

  after(r, sender) {
    if (r.ended) this.broadcast(Object.assign({ t: "edition", ended: r.ended }, this.state()));
    else if (r.accepted) {
      const st = this.state();
      this.broadcast({ t: "p", l: r.accepted, counts: st.counts, typists: st.typists, here: st.here, edition: st.edition }, sender);
    }
  }

  async webSocketMessage(ws, raw) {
    if (typeof raw !== "string" || raw.length > 1000) return;
    let m = null; try { m = JSON.parse(raw) } catch (e) { return }
    if (!m || m.t !== "p") return;
    const letters = cleanLetters(m.l); if (!letters) return;
    const { ip } = ws.deserializeAttachment() || {};
    const r = this.press(letters, await this.who(ip), cleanUid(m.u));
    const st = this.state();
    try { ws.send(JSON.stringify({ t: "ack", id: m.id, accepted: r.accepted.length, capped: r.capped, counts: st.counts, typists: st.typists, here: st.here, edition: st.edition })) } catch (e) {}
    this.after(r, ws);
  }
  async webSocketClose(ws) {
    try { ws.close() } catch (e) {}
    this.broadcast({ t: "here", here: this.here(ws) }, ws);
  }
  async webSocketError(ws) { this.broadcast({ t: "here", here: this.here(ws) }, ws) }
}
