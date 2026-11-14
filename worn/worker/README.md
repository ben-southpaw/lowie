# Lowie Worn counter

A Cloudflare Worker with one Durable Object that holds the shared font: how many times each letter has been typed, in the current edition. The page talks to it over a WebSocket and falls back to HTTP.

- **Editions.** An edition ends when every letter has had 240 presses (80% worn). The counts are archived and the font starts fresh.
- **Limits.** One visitor can add 40 presses per letter and 600 in all per day. A visitor is a salted hash of their IP and the date; raw IPs are never stored and old hashes are deleted daily.
- **Visitors.** Each browser keeps a random id. The page lists the last 40 visitors with a number, country, when, and how many letters they typed. Ids, IPs and typed text never leave the server. One IP can add 8 new visitors a day.
- **Origins.** Anyone can read `/api/state`. Writing needs a page listed in `ALLOWED_ORIGINS` in `wrangler.jsonc`.

## Run locally

```bash
npx wrangler dev --port 8787 --var END_COUNT:3 --var PER_LETTER_DAY:5
node test.mjs
bash ../build-site.sh /tmp/worn-site/worn && python3 -m http.server 8788 --directory /tmp/worn-site
```

Then open `http://localhost:8788/worn/?api=http://localhost:8787`. The `api` parameter is only honoured on localhost.

## Deploy

```bash
npx wrangler login
npx wrangler deploy
```

Put the deployed URL in the `lowie-api` meta tag at the top of `../index.html`. The Pages workflow on `main` builds the page into the specimen site at `/worn/`.
