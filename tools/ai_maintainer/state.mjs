import { digest } from './fingerprint.mjs';

// Immutable diagnostic receipt, NOT a monthly ledger. In particular, a new run
// cannot interpret spent=0 as a reset of the account's previous paid usage.
export function receipt(report) {
  return { schemaVersion: 1, stage: 'I', repositoryId: report.repositoryId,
    itemId: report.item.id, reportDigest: digest(report),
    analysisFingerprint: report.analysisFingerprint, evidenceFingerprint: report.evidenceFingerprint,
    provenance: report.provenance, authorizesSpending: false, authorizesPublication: false,
    monthlyBalance: null, budget: report.budget };
}

export function spendingDecision() {
  return { allowed: false, reason: 'stage-I-no-inference', monthlyLimitAic: 500 };
}
