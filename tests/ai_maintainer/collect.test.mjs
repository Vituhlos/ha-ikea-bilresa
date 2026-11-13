import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { fixture, fixtureReader } from './helpers.mjs';
import { collect } from '../../tools/ai_maintainer/collect.mjs';
import { configuration } from '../../tools/ai_maintainer/snapshot.mjs';
import { ReadError } from '../../tools/ai_maintainer/api.mjs';

const { branches, policy } = await configuration();

for (const number of [70,9,71]) test(`collector replays real #${number} metadata and source excerpts without running fork code`, async () => {
  const input = await fixture(number);
  const actual = await collect(fixtureReader(input), number, branches, policy);
  assert.deepEqual(actual.refs, input.refs);
  assert.equal(actual.missing.length, 0);
  assert.equal(actual.sources.length, input.sources.length);
  assert.equal(actual.files.length, input.files.length);
});

test('missing branch and wrong/private repository stop collection', async () => {
  const input = await fixture(70);
  for (const repo of [{ ...input.repository, id: 1 }, { ...input.repository, private: true }]) {
    await assert.rejects(collect(fixtureReader(input, r => r.endsWith('ha-ikea-bilresa') ? repo : undefined), 70, branches, policy), /identity-mismatch/);
  }
  await assert.rejects(collect(fixtureReader(input, r => { if (r.endsWith('/commits/main')) throw new ReadError('http-404'); }), 70, branches, policy), /http-404/);
  await assert.rejects(collect(fixtureReader(input), '70;echo attack', branches, policy), /invalid-item/);
});

test('missing pages, excessive files and oversized/binary/symlink sources remain incomplete', async () => {
  const input = await fixture(71);
  for (const override of [
    r => r.endsWith('/files') ? input.files.slice(0,2) : undefined,
    r => { if (r.endsWith('/files')) throw new ReadError('page-limit'); },
    r => r.includes('/contents/') ? { type: 'symlink' } : undefined,
    r => r.includes('/contents/') ? { type: 'file', sha: 'a'.repeat(40), encoding: 'base64', size: 800001 } : undefined,
    r => r.includes('/contents/') ? { type: 'file', sha: 'a'.repeat(40), encoding: 'base64', size: 1, content: 'AA==' } : undefined,
  ]) {
    const actual = await collect(fixtureReader(input, override), 71, branches, policy);
    assert.ok(actual.missing.length > 0);
  }
  const small = await collect(fixtureReader(input), 71, branches, { ...policy, limits: { ...policy.limits, sourcePaths: 1, relatedPulls: 0 } });
  assert.ok(small.missing.includes('source-paths:limit'));
  assert.ok(small.missing.includes('related-pulls:limit'));
});

test('read denial never degrades into a successful partial report', async () => {
  const input = await fixture(70);
  await assert.rejects(collect(fixtureReader(input, r => { if (r.includes('/contents/')) throw new ReadError('http-403'); }), 70, branches, policy), /http-403/);
});

test('force-push and comment edits during collection are detected', async () => {
  const input = await fixture(71); let prReads = 0; let commentReads = 0;
  const actual = await collect(fixtureReader(input, route => {
    if (route.endsWith('/pulls/71') && ++prReads > 1) return { ...input.item, head: { ...input.item.head, sha: 'b'.repeat(40) } };
    if (route.endsWith('/issues/71/comments') && ++commentReads > 1) return [{ id: 999, user: {id:1,type:'User'}, body:'edited' }];
  }), 71, branches, policy);
  assert.ok(actual.missing.includes('item:changed-during-collection'));
  assert.ok(actual.missing.includes('comments:changed-during-collection'));
});

test('workflow is owner-only manual on main, read-only, pinned and data-only inputs', async () => {
  const workflow = await readFile(new URL('../../.github/workflows/ai-maintainer-snapshot.yml', import.meta.url), 'utf8');
  assert.match(workflow, /workflow_dispatch:/);
  assert.doesNotMatch(workflow, /pull_request_target:|issue_comment:|schedule:|\bpush:|\bwrite\b/);
  assert.match(workflow, /github\.ref == 'refs\/heads\/main'/);
  assert.match(workflow, /github\.triggering_actor == 'Vituhlos'/);
  assert.match(workflow, /persist-credentials: false/);
  assert.match(workflow, /SNAPSHOT_ITEM: \$\{\{ inputs.item \}\}/);
  assert.doesNotMatch(workflow, /run:.*\$\{\{/);
  const actions = [...workflow.matchAll(/uses: ([^\n]+)/g)];
  assert.equal(actions.length, 4);
  for (const action of actions) assert.match(action[1], /@[a-f0-9]{40}/);
});
