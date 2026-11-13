import { readFile, writeFile, mkdir, appendFile } from 'node:fs/promises';
import { pathToFileURL } from 'node:url';
import { GitHubReader } from './api.mjs';
import { collect } from './collect.mjs';
import { assess, changeKind } from './assessment.mjs';
import { validate, validateReport } from './validate.mjs';
import { receipt } from './state.mjs';
import { digest } from './fingerprint.mjs';

export async function toolDigest() {
  const names = ['api', 'assessment', 'branch_evidence', 'collect', 'fingerprint', 'snapshot', 'state', 'validate'];
  const files = [...names.map(name => `./${name}.mjs`),
    '../../.github/ai-maintainer/report.schema.json', '../../.github/ai-maintainer/state.schema.json'];
  return digest(await Promise.all(files.map(file => readFile(new URL(file, import.meta.url), 'utf8'))));
}

export async function configuration() {
  const read = async name => JSON.parse(await readFile(new URL(`../../.github/ai-maintainer/${name}.json`, import.meta.url), 'utf8'));
  return { policy: await read('policy'), branches: await read('branches'),
    reportSchema: await read('report.schema'), stateSchema: await read('state.schema') };
}

export async function run(env = process.env) {
  if (!/^[1-9]\d{0,8}$/.test(env.SNAPSHOT_ITEM ?? '')) throw new Error('Invalid item number');
  const { policy, branches, reportSchema, stateSchema } = await configuration();
  const reader = new GitHubReader({ token: env.GH_TOKEN, maxPages: policy.limits.pages, maxBytes: policy.limits.responseBytes });
  const input = await collect(reader, Number(env.SNAPSHOT_ITEM), branches, policy);
  const report = validateReport(reportSchema, assess(input, policy, branches, {
    collectedAt: new Date().toISOString(), toolRevision: env.SNAPSHOT_TOOL_SHA,
    toolDigest: await toolDigest(),
    runId: env.GITHUB_RUN_ID ?? 'local', runAttempt: Number(env.GITHUB_RUN_ATTEMPT ?? 1),
  }));
  let previous = null;
  if (env.SNAPSHOT_PREVIOUS) {
    const data = await readFile(env.SNAPSHOT_PREVIOUS);
    if (data.length > 2000000) throw new Error('Previous report too large');
    previous = validateReport(reportSchema, JSON.parse(data.toString('utf8')));
  }
  const state = validate(stateSchema, receipt(report));
  const reportJson = JSON.stringify(report, null, 2) + '\n';
  if (Buffer.byteLength(reportJson) > 2000000) throw new Error('Report too large');
  const output = env.SNAPSHOT_OUTPUT ?? 'snapshot-output';
  await mkdir(output, { recursive: true });
  // Exclusive writes prevent silently replacing a receipt from a prior run.
  await writeFile(`${output}/report.json`, reportJson, { flag: 'wx' });
  await writeFile(`${output}/state.json`, JSON.stringify(state, null, 2) + '\n', { flag: 'wx' });
  const summary = `## BILRESA read-only snapshot / Podklady pouze pro čtení\n\n`
    + `Item / Položka: #${report.item.number}\n\n`
    + `Complete / Úplné: ${report.complete}. Change / Změna: ${changeKind(previous, report)}.\n\n`
    + `Fingerprint: \`${report.analysisFingerprint}\`\n\n`
    + `AI: 0 calls / volání, 0 AIC. Future monthly limit / Budoucí měsíční limit: 500 AIC.\n\n`
    + `Human review required; no publication or coding authorized. / Vyžaduje kontrolu správce; bez oprávnění publikovat či měnit kód.\n`;
  await writeFile(`${output}/summary.md`, summary, { flag: 'wx' });
  if (env.GITHUB_STEP_SUMMARY) await appendFile(env.GITHUB_STEP_SUMMARY, summary);
  return report.complete ? 0 : 2;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  try { process.exitCode = await run(); }
  catch { console.error('Snapshot failed; no inference or public write was attempted. Check read access, input and schema.'); process.exitCode = 1; }
}
