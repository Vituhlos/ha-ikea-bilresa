import test from 'node:test';
import assert from 'node:assert/strict';
import { GitHubReader, repoPath } from '../../tools/ai_maintainer/api.mjs';

const response = (body, status = 200, headers = {}) => new Response(JSON.stringify(body), { status, headers });

test('reader only GETs fixed repository, disables redirects and never follows pagination URLs', async () => {
  const calls = [];
  const reader = new GitHubReader({ token: 'test-secret', fetchImpl: async (url, options) => {
    calls.push({ url, options }); return response([], 200, { Link: '<https://evil.test>; rel="next"' });
  } });
  assert.deepEqual(await reader.list(repoPath('/issues/70/comments')), []);
  assert.equal(calls[0].options.method, 'GET');
  assert.equal(calls[0].options.redirect, 'error');
  for (const path of ['https://evil.test', '/repos/other/repo/issues', repoPath('/../../other/repo'),
    repoPath('/../ha-ikea-bilresa-other/issues'), repoPath('/%2e%2e/secrets'), repoPath('/foo#bar')]) {
    await assert.rejects(reader.get(path), /forbidden-route/);
  }
  assert.equal(calls.length, 1);
});

test('all pages are read, including the final empty page of an exact multiple', async () => {
  const pages = [];
  const reader = new GitHubReader({ fetchImpl: async url => {
    const page = Number(new URL(url).searchParams.get('page')); pages.push(page);
    return response(page <= 2 ? Array.from({length:100}, (_, i) => page * 100 + i) : []);
  } });
  assert.equal((await reader.list(repoPath('/pulls/71/files'))).length, 200);
  assert.deepEqual(pages, [1,2,3]);
});

test('pagination ceilings and check-run total mismatches fail closed', async () => {
  const reader = new GitHubReader({ maxPages: 1, fetchImpl: async () => response(Array(100).fill({})) });
  await assert.rejects(reader.list(repoPath('/pulls/71/files')), /page-limit/);
  const checks = new GitHubReader({ fetchImpl: async () => response({ total_count: 2, check_runs: [{}] }) });
  await assert.rejects(checks.list(repoPath('/commits/abc/check-runs'), 'check_runs'), /incomplete-pagination/);
});

test('429 and server errors retry at most twice and respect Retry-After', async () => {
  const sleeps = []; let count = 0;
  const reader = new GitHubReader({ sleep: async ms => sleeps.push(ms), fetchImpl: async () => {
    count++; return response({}, count < 3 ? 429 : 200, { 'Retry-After': '2' });
  } });
  await reader.get(repoPath('')); assert.equal(count, 3); assert.deepEqual(sleeps, [2000,2000]);
  count = 0; reader.fetchImpl = async () => { count++; return response({}, 503); };
  await assert.rejects(reader.get(repoPath('')), /retry-budget-exhausted/); assert.equal(count, 3);
  reader.fetchImpl = async () => response({}, 429, { 'Retry-After': '120' });
  await assert.rejects(reader.get(repoPath('')), /retry-budget-exhausted/);
});

test('401/403 never retry; network and JSON errors cannot leak response bodies or tokens', async () => {
  for (const status of [401,403]) {
    let count = 0;
    const reader = new GitHubReader({ fetchImpl: async () => { count++; return response('secret', status); } });
    await assert.rejects(reader.get(repoPath('')), new RegExp(`http-${status}`)); assert.equal(count, 1);
  }
  const reader = new GitHubReader({ fetchImpl: async () => { throw new Error('secret'); } });
  await assert.rejects(reader.get(repoPath('')), /network-error/);
  reader.fetchImpl = async () => new Response('secret-not-json');
  await assert.rejects(reader.get(repoPath('')), /invalid-json/);
});

test('oversized responses are rejected before parsing', async () => {
  const reader = new GitHubReader({ maxBytes: 10, fetchImpl: async () => response('a'.repeat(100)) });
  await assert.rejects(reader.get(repoPath('')), /response-too-large/);
});

test('a body-stream transport failure is a bounded ReadError with no upstream message', async () => {
  const reader = new GitHubReader({ fetchImpl: async () => new Response(new ReadableStream({
    start(controller) { controller.enqueue(new TextEncoder().encode('{')); },
    pull(controller) { controller.error(new Error('private-transport-detail')); },
  })) });
  await assert.rejects(reader.get(repoPath('/issues/70')), error =>
    error.constructor.name === 'ReadError' && error.code === 'network-error' && !error.message.includes('private'));
});
