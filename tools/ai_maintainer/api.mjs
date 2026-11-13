const ROOT = 'https://api.github.com';
const REPO = '/repos/Vituhlos/ha-ikea-bilresa';

export class ReadError extends Error {
  constructor(code) { super(code); this.code = code; }
}

// The only network primitive: GET, fixed origin/repository, no redirects,
// no arbitrary URLs from issue text, patches or pagination headers.
export class GitHubReader {
  constructor({ token, fetchImpl = fetch, sleep = ms => new Promise(r => setTimeout(r, ms)),
    maxPages = 30, maxBytes = 5000000 } = {}) {
    Object.assign(this, { token, fetchImpl, sleep, maxPages, maxBytes });
  }

  async get(path) {
    if (!path.startsWith(`${REPO}/`) && path !== REPO) throw new ReadError('forbidden-route');
    const url = new URL(path, ROOT);
    if (url.origin !== ROOT || (url.pathname !== REPO && !url.pathname.startsWith(`${REPO}/`)) || /[\\#]/.test(path)
      || /%2e|%2f|%5c/i.test(url.pathname.replace(/%2F/gi, ''))) {
      throw new ReadError('forbidden-route');
    }
    for (let attempt = 0; attempt < 3; attempt++) {
      let response;
      try {
        response = await this.fetchImpl(url.href, { method: 'GET', redirect: 'error',
          signal: AbortSignal.timeout(30000), headers: {
            Accept: 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28',
            ...(this.token ? { Authorization: `Bearer ${this.token}` } : {}),
          } });
      } catch { throw new ReadError('network-error'); }
      if (response.status === 401 || response.status === 403) throw new ReadError(`http-${response.status}`);
      if (response.status === 429 || response.status >= 500) {
        const retry = response.headers.get('retry-after');
        const delay = retry === null ? 1000 * 2 ** attempt
          : /^\d+$/.test(retry) ? Number(retry) * 1000 : Date.parse(retry) - Date.now();
        await response.body?.cancel();
        if (attempt === 2 || !Number.isFinite(delay) || delay > 30000) throw new ReadError('retry-budget-exhausted');
        await this.sleep(Math.max(0, delay));
        continue;
      }
      if (!response.ok) throw new ReadError(`http-${response.status}`);
      const chunks = [];
      let size = 0;
      for await (const chunk of response.body) {
        size += chunk.length;
        if (size > this.maxBytes) throw new ReadError('response-too-large');
        chunks.push(chunk);
      }
      try { return JSON.parse(Buffer.concat(chunks).toString('utf8')); }
      catch { throw new ReadError('invalid-json'); }
    }
  }

  async list(path, key = null) {
    const result = [];
    for (let page = 1; page <= this.maxPages; page++) {
      const data = await this.get(`${path}${path.includes('?') ? '&' : '?'}per_page=100&page=${page}`);
      const entries = key ? data[key] : data;
      if (!Array.isArray(entries)) throw new ReadError('invalid-page');
      result.push(...entries);
      if (entries.length < 100) {
        if (key && Number.isInteger(data.total_count) && result.length !== data.total_count) {
          throw new ReadError('incomplete-pagination');
        }
        return result;
      }
    }
    throw new ReadError('page-limit');
  }
}

export const repoPath = suffix => `${REPO}${suffix}`;
