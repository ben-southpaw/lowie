// Run against `wrangler dev` started with small limits:
//   npx wrangler dev --port 8787 --var END_COUNT:3 --var PER_LETTER_DAY:5 --var PER_DAY:200
//   node test.mjs
// Starts from whatever state the dev server holds, so it checks differences, not absolutes.
const BASE = process.env.BASE || "http://localhost:8787";
const ORIGIN = "http://localhost:8788";
let fails = 0;
const ok = (cond, msg) => { console.log((cond ? "ok   " : "FAIL ") + msg); if (!cond) fails++ };

function open(uid) {
  return new Promise((res, rej) => {
    const ws = new WebSocket(BASE.replace("http", "ws") + "/api/ws?u=" + uid, { headers: { Origin: ORIGIN } });
    const inbox = [];
    ws.onmessage = e => inbox.push(JSON.parse(e.data));
    ws.onopen = () => res({ ws, inbox, uid, send: l => ws.send(JSON.stringify({ t: "p", l, u: uid })) });
    ws.onerror = rej;
  });
}
const wait = ms => new Promise(r => setTimeout(r, ms));
const until = async (f, ms = 3000) => { const t = Date.now(); while (Date.now() - t < ms) { const v = f(); if (v) return v; await wait(30) } return null };

// Origin rules
let r = await fetch(BASE + "/api/press", { method: "POST", headers: { "Content-Type": "application/json", Origin: "https://evil.example" }, body: JSON.stringify({ l: "e" }) });
ok(r.status === 403, "POST from an unknown origin is refused");
r = await fetch(BASE + "/api/state");
ok(r.status === 200, "GET state is public");
const s0 = await r.json();

// Live presses
const a = await open("visitoraaaa1"), b = await open("visitorbbbb2");
const first = await until(() => a.inbox.find(m => m.t === "state"));
ok(first && first.edition === s0.edition, "socket opens with the current state");
ok(await until(() => a.inbox.find(m => m.t === "here" && m.here >= 2)), "first socket hears the second arrive");

a.send("q");
const ack = await until(() => a.inbox.find(m => m.t === "ack"));
ok(ack && ack.accepted === 1, "press is acknowledged");
const heard = await until(() => b.inbox.find(m => m.t === "p" && m.l === "q"));
ok(heard, "other socket hears the press");
ok(!a.inbox.find(m => m.t === "p"), "sender does not hear its own press back");
ok(heard && (heard.counts.q || 0) === (s0.counts.q || 0) + 1, "count went up by one");

// Daily cap: 5 per letter per visitor (both test sockets share one IP, so one visitor)
a.inbox.length = 0;
a.send("zzzzzzzzzz");
const ack2 = await until(() => a.inbox.find(m => m.t === "ack"));
ok(ack2 && ack2.capped && ack2.accepted <= 5, `cap holds (accepted ${ack2 && ack2.accepted} of 10)`);

// Bad input is ignored, not counted
a.inbox.length = 0;
a.ws.send("not json"); a.ws.send(JSON.stringify({ t: "p", l: "123 !!" }));
await wait(300);
ok(!a.inbox.find(m => m.t === "ack"), "junk messages get no ack");

// Edition rollover: END_COUNT 3, so three of every letter ends edition 1
b.inbox.length = 0;
const ed = (await (await fetch(BASE + "/api/state")).json()).edition;
const all = "abcdefghijklmnopqrstuvwxyz";
const c = await open("visitorcccc3");
c.send(all + all + all);
const roll = await until(() => b.inbox.find(m => m.t === "edition"));
if (roll) {
  ok(roll.edition === ed + 1 && roll.ended === ed, `edition ${ed} ended, edition ${roll.edition} started`);
  ok(Object.keys(roll.counts).length === 0, "new edition starts with no wear");
  ok(roll.past.some(p => p.edition === ed), "ended edition is archived");
} else {
  ok(false, "edition rollover (the daily cap may already be spent; restart wrangler dev with a fresh --persist-to)");
}

// Visitors
const st = first;
ok(st && st.you > 0, "socket learns its own visitor number");
const raw = JSON.stringify(a.inbox) + JSON.stringify(await (await fetch(BASE + "/api/state")).json());
ok(!raw.includes("visitoraaaa1") && !raw.includes("visitorbbbb2"), "client ids never leave the server");
const d = await open("visitordddd4");
const dst = await until(() => d.inbox.find(m => m.t === "state"));
const later = await (await fetch(BASE + "/api/state")).json();
const va = later.visitors.find(v => v.n === st.you), vd = later.visitors.find(v => v.n === (dst && dst.you));
ok(va && va.presses >= 1 && va.here === true, "a typist is listed with their presses, here now");
ok(vd && vd.presses === 0, "a visitor who only looked is listed with no presses");
ok(later.seen >= 4 && later.typedBy >= 2, "totals count visitors and typists");
ok(await until(() => a.inbox.find(m => m.t === "here" && Array.isArray(m.visitors))), "arrivals broadcast the visitor list");
const extra = [];
for (let i = 0; i < 10; i++) extra.push(await open("capvisitor" + String(i).padStart(4, "0") + Math.random().toString(36).slice(2, 8)));
const yous = await Promise.all(extra.map(x => until(() => x.inbox.find(m => m.t === "state"))));
ok(yous.some(m => m && m.you == null), "one IP cannot add unlimited new visitors in a day");
extra.forEach(x => x.ws.close());

[a, b, c, d].forEach(x => x.ws.close());
await wait(200);
console.log(fails ? `${fails} failed` : "all passed");
process.exit(fails ? 1 : 0);
