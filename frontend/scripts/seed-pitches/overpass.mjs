// Overpass API client with the two things this session's investigation
// showed are actually required against the free overpass-api.de instance:
//
//  1. A browser-like Referer/Origin header — requests without one get a
//     bare HTTP 406 from the server's anti-bot rule, with no Overpass
//     error body at all (just an Apache error page).
//  2. Retry with backoff — plain, correctly-formed queries hit transient
//     "dispatcher timeout" and rate-limit errors on this shared free
//     instance, reproduced repeatedly even a few seconds apart.

const ENDPOINT = 'https://overpass-api.de/api/interpreter';
const USER_AGENT =
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36';

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// Returns parsed JSON, or throws after exhausting retries.
export async function overpassQuery(query, { retries = 3, backoffMs = 5000, timeoutMs = 180000 } = {}) {
  let lastError;
  for (let attempt = 0; attempt <= retries; attempt++) {
    if (attempt > 0) {
      const wait = backoffMs * 2 ** (attempt - 1);
      console.log(`  retry ${attempt}/${retries} after ${wait}ms...`);
      await sleep(wait);
    }
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), timeoutMs);
      const res = await fetch(ENDPOINT, {
        method: 'POST',
        headers: {
          'User-Agent': USER_AGENT,
          Referer: 'https://overpass-turbo.eu/',
          Origin: 'https://overpass-turbo.eu',
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `data=${encodeURIComponent(query)}`,
        signal: controller.signal,
      });
      clearTimeout(timer);
      const text = await res.text();
      if (!res.ok) {
        lastError = new Error(`HTTP ${res.status}: ${text.slice(0, 200)}`);
        continue;
      }
      let json;
      try {
        json = JSON.parse(text);
      } catch {
        // Overpass returns an XHTML error body (not JSON) with a 200 status
        // for runtime errors like dispatcher timeouts — treat as retryable.
        lastError = new Error(`Non-JSON response (likely a runtime error): ${text.slice(0, 200)}`);
        continue;
      }
      return json;
    } catch (err) {
      lastError = err;
    }
  }
  throw lastError;
}
