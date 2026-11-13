import { analysisFingerprint, digest } from './fingerprint.mjs';
import { sourceEvidence, symbolComparisons, safePath, sha } from './branch_evidence.mjs';

export function assess(input, policy, branches, provenance) {
  if (policy.stage !== 'I' || policy.aiEnabled !== false || policy.publicResponsesEnabled !== false
    || policy.codingEnabled !== false || policy.monthlyBudgetAic !== 500) throw new Error('Stage I policy required');
  const evidence = input.sources.map(sourceEvidence);
  const checks = input.checks.filter(c => c.head_sha === input.refs.prHead?.sha).map(c => ({
    id: c.id, name: policy.requiredChecks.includes(c.name) ? c.name : 'advisory',
    appId: c.app?.id ?? 0, revision: c.head_sha, status: c.status, conclusion: c.conclusion,
  }));
  const requiredChecksPass = input.kind === 'pull_request' && policy.requiredChecks.every(name => {
    const matches = checks.filter(c => c.name === name && c.appId === policy.checkAppId);
    return matches.length === 1 && matches[0].status === 'completed' && matches[0].conclusion === 'success';
  });
  const policyDigest = digest({ policy, branches, toolDigest: provenance.toolDigest });
  const related = input.related.map(p => ({ number: p.number, state: p.state,
    merged: p.merged === true, head: p.head.sha, base: p.base.sha,
    url: `https://github.com/${branches.repository}/pull/${p.number}`,
    selection: p.selection, relationship: 'candidate-not-semantic-proof' }));
  const report = {
    schemaVersion: 1, stage: 'I', repositoryId: branches.repositoryId,
    item: { id: input.item.id, number: input.item.number, kind: input.kind, state: input.item.state,
      url: `https://github.com/${branches.repository}/${input.kind === 'issue' ? 'issues' : 'pull'}/${input.item.number}` },
    provenance, policyDigest, refs: input.refs,
    analysisFingerprint: analysisFingerprint(input, policyDigest),
    evidenceFingerprint: digest({ evidence, checks, related, ancestry: input.ancestry, missing: input.missing }),
    complete: input.missing.length === 0,
    assessment: 'human-assessment-required',
    evidence, comparisons: symbolComparisons(evidence), related, ancestry: input.ancestry,
    files: input.files.filter(f => safePath(f.filename) && sha(f.sha)).map(f => ({
      path: f.filename, previousPath: f.previous_filename && safePath(f.previous_filename) ? f.previous_filename : null,
      status: f.status, sha: f.sha, additions: f.additions, deletions: f.deletions,
    })),
    validation: { implementation: 'not-adjudicated', static: 'source-observations-only',
      unit: 'not-run', ci: requiredChecksPass ? 'required-checks-pass-at-head' : 'not-established',
      hardware: 'not-established', released: 'not-adjudicated', checks },
    missing: [...new Set(input.missing)].sort(),
    risks: ['Lexical matches and ancestry do not prove behavior or a duplicate.',
      'Source links may contain untrusted or sensitive content; no source text is republished.',
      'CI evidence is limited to the recorded head SHA and GitHub Actions App.',
      'No runtime tests or hardware checks were executed by this snapshot.'],
    nextAction: 'owner-review-evidence', ownerApprovalRequired: true,
    budget: { currency: 'AIC', monthlyLimit: 500, spent: 0, reserved: 0, inferenceCalls: 0 },
  };
  if (report.files.length !== input.files.length) {
    report.complete = false; report.missing.push('files:unsupported-metadata');
  }
  return report;
}

// Only a scheduling hint. Neither a supplied report nor an Actions cache may
// authorize inference, publication, or mutate the future budget ledger.
export function changeKind(previous, report) {
  if (!report.complete) return 'incomplete';
  if (!previous || !previous.complete || previous.repositoryId !== report.repositoryId
    || previous.item.id !== report.item.id) return 'new-evidence';
  if (previous.analysisFingerprint !== report.analysisFingerprint) return 'analysis-input-changed';
  return previous.evidenceFingerprint === report.evidenceFingerprint ? 'unchanged' : 'evidence-only';
}
