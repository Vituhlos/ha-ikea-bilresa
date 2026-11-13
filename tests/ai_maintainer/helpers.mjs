import { readFile } from 'node:fs/promises';
import { ReadError } from '../../tools/ai_maintainer/api.mjs';

export async function fixture(number) {
  const sources = JSON.parse(await readFile(new URL('./fixtures/sources.json', import.meta.url), 'utf8'));
  const input = JSON.parse(await readFile(new URL(`./fixtures/${number}.json`, import.meta.url), 'utf8'));
  input.sources = input.sources.map(s => ({ role: s.role, ...sources[s.key] }));
  return input;
}

export function fixtureReader(input, override = () => undefined) {
  const item = input.item;
  const get = async route => {
    const changed = override(route);
    if (changed !== undefined) return structuredClone(changed);
    const url = new URL(route, 'https://api.github.com');
    const path = decodeURIComponent(url.pathname.replace('/repos/Vituhlos/ha-ikea-bilresa', ''));
    if (path === '') return structuredClone(input.repository);
    if (path === `/issues/${item.number}`) return structuredClone({ ...item, ...(input.kind === 'pull_request' ? { pull_request: {} } : {}) });
    if (path === `/pulls/${item.number}`) return structuredClone(item);
    if (path === '/releases/latest') return { tag_name: input.refs.stable.ref, draft: false, prerelease: false };
    if (path.startsWith('/commits/')) {
      const ref = Object.values(input.refs).find(r => r.ref === path.slice('/commits/'.length));
      if (ref) return { sha: ref.sha };
    }
    if (path.startsWith('/contents/')) {
      const source = input.sources.find(s => s.path === path.slice('/contents/'.length) && s.revision === url.searchParams.get('ref'));
      if (!source) throw new ReadError('http-404');
      const buffer = Buffer.from(source.content);
      return { type: 'file', sha: 'a'.repeat(40), encoding: 'base64', size: buffer.length, content: buffer.toString('base64') };
    }
    if (path.startsWith('/compare/')) {
      const [commit, revision] = path.slice('/compare/'.length).split('...');
      const a = input.ancestry.find(a => a.commit === commit && a.revision === revision);
      if (a) return { status: a.ancestor ? 'ahead' : 'diverged' };
    }
    const related = input.related.find(p => path === `/pulls/${p.number}`);
    if (related) return structuredClone(related);
    throw new Error(`Unexpected fixture route: ${path}`);
  };
  const list = async route => {
    const changed = override(route);
    if (changed !== undefined) return structuredClone(changed);
    if (route.endsWith(`/issues/${item.number}/comments`)) return structuredClone(input.comments);
    if (route.includes('/timeline') || route.endsWith('/reviews') || route.endsWith(`/pulls/${item.number}/comments`)) return [];
    if (route.endsWith(`/pulls/${item.number}/files`)) return structuredClone(input.files);
    if (route.includes('/check-runs')) return structuredClone(input.checks);
    if (route.includes('/pulls?')) return structuredClone(input.related);
    throw new Error('Unexpected fixture list');
  };
  return { get, list };
}
