import { repoPath, ReadError } from './api.mjs';
import { sha, safePath } from './branch_evidence.mjs';
import { digest, humanComments } from './fingerprint.mjs';

function itemState(item) {
  return digest({ id: item.id, title: item.title, body: item.body, state: item.state,
    updated: item.updated_at, comments: item.comments, labels: item.labels,
    head: item.head?.sha ?? null, base: item.base?.sha ?? null });
}

export async function collect(reader, number, branches, policy) {
  if (!Number.isSafeInteger(number) || number < 1) throw new ReadError('invalid-item-number');
  const input = { repository: await reader.get(repoPath('')), refs: {},
    comments: [], files: [], related: [], sources: [], absences: [], checks: [], ancestry: [], missing: [] };
  if (input.repository.id !== branches.repositoryId || input.repository.full_name !== branches.repository
    || input.repository.private) throw new ReadError('repository-identity-mismatch');
  // Authentication/rate-limit failures stop; missing bounded evidence is explicit.
  const optional = async (key, task, fallback) => {
    try { return await task(); } catch (error) {
      if (!(error instanceof ReadError) || ['http-401', 'http-403'].includes(error.code)) throw error;
      input.missing.push(`${key}:${error.code}`);
      return fallback;
    }
  };
  const issue = await reader.get(repoPath(`/issues/${number}`));
  const isPr = Boolean(issue.pull_request);
  input.item = isPr ? { ...await reader.get(repoPath(`/pulls/${number}`)), labels: issue.labels } : issue;
  input.kind = isPr ? 'pull_request' : 'issue';
  input.comments = await optional('comments', () => reader.list(repoPath(`/issues/${number}/comments`)), []);
  if (isPr) {
    input.comments.push(...await optional('review-comments', () => reader.list(repoPath(`/pulls/${number}/comments`)), []));
    input.comments.push(...await optional('reviews', () => reader.list(repoPath(`/pulls/${number}/reviews`)), []));
    input.files = await optional('files', () => reader.list(repoPath(`/pulls/${number}/files`)), []);
    if (input.files.length !== input.item.changed_files) input.missing.push('files:count-mismatch');
    if (!sha(input.item.head.sha) || !sha(input.item.base.sha)
      || input.item.base.repo.id !== branches.repositoryId) throw new ReadError('invalid-pr-refs');
    input.refs.prBase = { ref: input.item.base.ref, sha: input.item.base.sha };
    input.refs.prHead = { ref: `pull/${number}/head`, sha: input.item.head.sha };
  }
  for (const role of ['main', 'development']) {
    const commit = await reader.get(repoPath(`/commits/${encodeURIComponent(branches[role])}`));
    if (!sha(commit.sha)) throw new ReadError('invalid-revision');
    input.refs[role] = { ref: branches[role], sha: commit.sha };
  }
  const release = await optional('stable-release', () => reader.get(repoPath('/releases/latest')), null);
  if (release && !release.draft && !release.prerelease && typeof release.tag_name === 'string') {
    const commit = await optional('stable-commit', () => reader.get(repoPath(`/commits/${encodeURIComponent(release.tag_name)}`)), null);
    if (sha(commit?.sha)) input.refs.stable = { ref: release.tag_name, sha: commit.sha };
    else input.missing.push('stable:unresolved');
  } else input.missing.push('stable:unavailable');

  const timeline = await optional('timeline', () => reader.list(repoPath(`/issues/${number}/timeline`)), []);
  const linked = new Set(timeline.filter(e => e.event === 'cross-referenced'
    && e.source?.issue?.repository_url === `https://api.github.com/repos/${branches.repository}`)
    .map(e => e.source.issue.number));
  const texts = [input.item.body, ...input.comments.filter(c => c.user?.type === 'User').map(c => c.body)].join('\n');
  // Bare #N is a local reference, not evidence that the work solves the issue.
  for (const match of texts.matchAll(/(?:^|\s)#([1-9]\d*)\b/g)) linked.add(Number(match[1]));
  const pulls = await optional('pull-catalog', () => reader.list(repoPath('/pulls?state=all&sort=updated&direction=desc')), []);
  const needle = new RegExp(`(?:^|\\s)#${number}\\b|github\\.com/${branches.repository}/(?:issues|pull)/${number}(?:\\b)`, 'i');
  const terms = value => new Set((value.toLowerCase().match(/[a-z_]{4,}/g) ?? [])
    .filter(t => !['feature', 'binding', 'with', 'that', 'this', 'from', 'when', 'into', 'only', 'have'].includes(t)));
  const itemTerms = terms(input.item.title);
  const sharedTerms = p => [...terms(p.title)].filter(t => itemTerms.has(t)).length >= 2;
  const candidates = pulls.filter(p => p.number !== number && (linked.has(p.number)
    || needle.test(p.body ?? '') || sharedTerms(p) || p.state === 'open'));
  if (candidates.length > policy.limits.relatedPulls) input.missing.push('related-pulls:limit');
  for (const candidate of candidates.slice(0, policy.limits.relatedPulls)) {
    const pr = await optional(`pull-${candidate.number}`, () => reader.get(repoPath(`/pulls/${candidate.number}`)), null);
    if (!pr) continue;
    pr.selection = linked.has(pr.number) || needle.test(pr.body ?? '') ? 'explicit-reference'
      : sharedTerms(pr) ? 'shared-title-terms' : 'open-inventory';
    input.related.push(pr);
    if (pr.merged && sha(pr.merge_commit_sha)) {
      for (const [role, revision] of Object.entries(input.refs).filter(([r]) => r !== 'prHead' && r !== 'prBase')) {
        const compare = await optional(`ancestry-${pr.number}-${role}`, () => reader.get(repoPath(`/compare/${pr.merge_commit_sha}...${revision.sha}?per_page=1`)), null);
        input.ancestry.push({ number: pr.number, role, commit: pr.merge_commit_sha,
          revision: revision.sha, ancestor: compare ? ['ahead', 'identical'].includes(compare.status) : null });
      }
    }
  }

  const paths = [...new Set([...policy.evidencePaths, ...input.files.flatMap(f =>
    [f.filename, f.previous_filename].filter(Boolean))])];
  const trees = new Map();
  for (const revision of Object.values(input.refs)) {
    if (trees.has(revision.sha)) continue;
    const tree = await optional(`tree-${revision.sha}`, () => reader.get(repoPath(`/git/trees/${revision.sha}?recursive=1`)), null);
    if (!tree || tree.truncated !== false || !Array.isArray(tree.tree) || !sha(tree.sha)
      || tree.tree.length > 100000) {
      input.missing.push(`tree-${revision.sha}:unavailable-or-truncated`);
      trees.set(revision.sha, null);
    } else trees.set(revision.sha, new Map(tree.tree.map(entry => [entry.path, entry])));
  }
  if (paths.length > policy.limits.sourcePaths) input.missing.push('source-paths:limit');
  for (const path of paths.slice(0, policy.limits.sourcePaths)) {
    if (!safePath(path)) { input.missing.push('source-path:unsupported'); continue; }
    for (const [role, revision] of Object.entries(input.refs)) {
      const tree = trees.get(revision.sha);
      if (!tree) continue;
      const entry = tree.get(path);
      if (!entry) {
        input.absences.push({ role, path, revision: revision.sha, basis: 'complete-git-tree' });
        continue;
      }
      if (entry.type !== 'blob' || !['100644', '100755'].includes(entry.mode) || !sha(entry.sha)) {
        input.missing.push(`source-${role}-${path}:unsupported-tree-entry`); continue;
      }
      const source = await optional(`source-${role}-${path}`, () => reader.get(repoPath(`/contents/${path}?ref=${revision.sha}`)), null);
      if (!source) continue;
      if (source.type !== 'file' || source.encoding !== 'base64' || source.sha !== entry.sha
        || source.size > policy.limits.sourceBytes) {
        input.missing.push(`source-${role}-${path}:unsupported-or-large`); continue;
      }
      const bytes = Buffer.from(source.content, 'base64');
      if (bytes.length !== source.size || bytes.length > policy.limits.sourceBytes || bytes.includes(0)) {
        input.missing.push(`source-${role}-${path}:invalid-content`); continue;
      }
      input.sources.push({ role, path, revision: revision.sha, content: bytes.toString('utf8') });
    }
  }
  if (isPr) input.checks = await optional('checks', () => reader.list(
    repoPath(`/commits/${input.refs.prHead.sha}/check-runs?filter=latest`), 'check_runs'), []);

  // Detect a moving snapshot. This is still a point-in-time diagnostic, never
  // an authorization to write based on stale evidence.
  const finalIssue = await reader.get(repoPath(`/issues/${number}`));
  const finalItem = isPr ? { ...await reader.get(repoPath(`/pulls/${number}`)), labels: finalIssue.labels } : finalIssue;
  if (itemState(input.item) !== itemState(finalItem) || itemState(issue) !== itemState(finalIssue)) {
    input.missing.push('item:changed-during-collection');
  }
  const finalComments = await optional('final-comments', () => reader.list(repoPath(`/issues/${number}/comments`)), []);
  if (isPr) {
    finalComments.push(...await optional('final-review-comments', () => reader.list(repoPath(`/pulls/${number}/comments`)), []));
    finalComments.push(...await optional('final-reviews', () => reader.list(repoPath(`/pulls/${number}/reviews`)), []));
  }
  if (digest(humanComments(input.comments)) !== digest(humanComments(finalComments))) {
    input.missing.push('comments:changed-during-collection');
  }
  for (const role of ['main', 'development', ...(input.refs.stable ? ['stable'] : [])]) {
    const current = await reader.get(repoPath(`/commits/${encodeURIComponent(input.refs[role].ref)}`));
    if (current.sha !== input.refs[role].sha) input.missing.push(`${role}:changed-during-collection`);
  }
  if (input.refs.stable) {
    const currentRelease = await optional('final-stable-release', () => reader.get(repoPath('/releases/latest')), null);
    if (currentRelease?.tag_name !== input.refs.stable.ref || currentRelease?.prerelease || currentRelease?.draft) {
      input.missing.push('stable-release:changed-during-collection');
    }
  }
  return input;
}
