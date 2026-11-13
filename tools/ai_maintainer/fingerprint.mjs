import { createHash } from 'node:crypto';

export function canonical(value) {
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
  if (value && typeof value === 'object') {
    return `{${Object.keys(value).sort().map(k => `${JSON.stringify(k)}:${canonical(value[k])}`).join(',')}}`;
  }
  return JSON.stringify(value);
}

export const digest = value => createHash('sha256').update(canonical(value)).digest('hex');
const text = value => (value ?? '').replace(/\r\n/g, '\n').trim();

export function humanComments(comments) {
  return comments.filter(c => c.user?.type === 'User').map(c => ({
    id: c.id, body: text(c.body), author: c.user.id,
    // Review dismissal and inline context can change the meaning of the same text.
    state: c.state ?? null, commit: c.commit_id ?? null, path: c.path ?? null,
    line: c.line ?? null,
  })).sort((a, b) => a.id - b.id);
}

export function analysisFingerprint(input, policyDigest) {
  return digest({
    repository: input.repository.id, item: input.item.id,
    title: text(input.item.title), body: text(input.item.body), state: input.item.state,
    labels: (input.item.labels ?? []).map(l => l.name).sort(),
    comments: humanComments(input.comments), refs: input.refs,
    related: input.related.filter(p => p.selection !== 'open-inventory').map(p => ({ number: p.number, state: p.state,
      merged: p.merged, head: p.head.sha, base: p.base.sha,
      title: text(p.title), body: text(p.body) })).sort((a, b) => a.number - b.number),
    files: input.files.map(f => ({ path: f.filename, previous: f.previous_filename ?? null,
      sha: f.sha, status: f.status })).sort((a, b) => a.path < b.path ? -1 : a.path > b.path ? 1 : 0),
    policyDigest,
  });
}

// Stable across branch movement. A future coding controller still needs a
// trusted approval and a reconciled task ledger; this hash grants no authority.
export function codingKey(repositoryId, issueId, approvedScope, target) {
  if (!approvedScope?.trim() || !['main', 'agent/panel-0.6.1'].includes(target)) {
    throw new Error('Invalid coding identity');
  }
  return digest({ repositoryId, issueId, approvedScope, target });
}
