import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { fixture, fixtureReader } from './helpers.mjs';
import { run, configuration } from '../../tools/ai_maintainer/snapshot.mjs';
import { validate, validateReport } from '../../tools/ai_maintainer/validate.mjs';

test('CLI writes validated report/receipt, compares a prior result and never overwrites it', async () => {
  const input = await fixture(71);
  const reader = fixtureReader(input);
  const originalFetch = globalThis.fetch;
  const prefix = join(tmpdir(), 'bilresa-snapshot-');
  const directory = await mkdtemp(prefix);
  let requests = 0;
  globalThis.fetch = async (address, options) => {
    const url = new URL(address);
    assert.equal(url.origin, 'https://api.github.com'); assert.equal(options.method, 'GET'); requests++;
    const paginated = url.searchParams.has('page');
    url.searchParams.delete('page'); url.searchParams.delete('per_page');
    const path = url.pathname + url.search;
    let data = paginated ? await reader.list(path) : await reader.get(path);
    if (path.includes('/check-runs')) data = { total_count: data.length, check_runs: data };
    return new Response(JSON.stringify(data));
  };
  try {
    const env = { SNAPSHOT_ITEM: '71', SNAPSHOT_TOOL_SHA: input.refs.main.sha,
      SNAPSHOT_OUTPUT: join(directory, 'first'), GH_TOKEN: 'test-secret' };
    assert.equal(await run(env), 0);
    const { reportSchema, stateSchema } = await configuration();
    const reportPath = join(env.SNAPSHOT_OUTPUT, 'report.json');
    const first = JSON.parse(await readFile(reportPath, 'utf8'));
    validateReport(reportSchema, first);
    const state = validate(stateSchema, JSON.parse(await readFile(join(env.SNAPSHOT_OUTPUT, 'state.json'), 'utf8')));
    assert.equal(state.budget.spent, 0);
    assert.ok(!JSON.stringify(first).includes('test-secret'));
    assert.equal(await run({ ...env, SNAPSHOT_OUTPUT: join(directory, 'second'), SNAPSHOT_PREVIOUS: reportPath }), 0);
    assert.match(await readFile(join(directory, 'second', 'summary.md'), 'utf8'), /unchanged/);
    await assert.rejects(run(env), /EEXIST/);
    assert.deepEqual(JSON.parse(await readFile(reportPath, 'utf8')), first);
    const before = requests;
    await assert.rejects(run({ ...env, SNAPSHOT_ITEM: '71; echo injected' }), /Invalid item/);
    assert.equal(requests, before);
    input.files.pop();
    assert.equal(await run({ ...env, SNAPSHOT_OUTPUT: join(directory, 'incomplete') }), 2);
    const incomplete = JSON.parse(await readFile(join(directory, 'incomplete', 'report.json'), 'utf8'));
    assert.equal(incomplete.complete, false);
  } finally {
    globalThis.fetch = originalFetch;
    assert.ok(resolve(directory).startsWith(resolve(prefix)));
    await rm(directory, { recursive: true, force: true });
  }
});
