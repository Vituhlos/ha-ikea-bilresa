import { digest } from './fingerprint.mjs';

export const sha = value => typeof value === 'string' && /^[a-f0-9]{40}$/.test(value);
export function safePath(value) {
  return typeof value === 'string' && value.length <= 240
    && /^[A-Za-z0-9_.\/-]+$/.test(value)
    && value.split('/').every(p => p && p !== '.' && p !== '..');
}

// This is an index, not a Python parser or a claim of semantic equivalence.
// Hash exact method text to spot identical implementations across divergent branches.
export function pythonSymbols(content) {
  const lines = content.replace(/\r\n/g, '\n').split('\n');
  const symbols = [];
  let className = '';
  for (let i = 0; i < lines.length; i++) {
    const cls = /^class ([A-Za-z_]\w*)/.exec(lines[i]);
    if (cls) className = cls[1];
    const match = /^( *)(?:async )?def ([A-Za-z_]\w*)\(/.exec(lines[i]);
    if (!match) continue;
    const indent = match[1].length;
    let end = i + 1;
    while (end < lines.length && (!lines[end].trim() || lines[end].search(/\S/) > indent)) end++;
    const body = lines.slice(i, end).join('\n').trimEnd();
    symbols.push({ name: `${indent && className ? className + '.' : ''}${match[2]}`,
      line: i + 1, endLine: end, digest: digest(body) });
  }
  return symbols;
}

export function sourceEvidence(source) {
  const { role, path, revision, content } = source;
  const symbols = path.endsWith('.py') ? pythonSymbols(content) : [];
  // Narrow, auditable lexical observations; never issue-number verdicts.
  const patterns = {
    first_notch_zero: /if notches <= 1[^\n]*:\s*return 0(?:\.0)?/g,
    later_batch_transition: /if self\._commanded_epoch == self\._scroll_epoch:\s*return self\._transition/g,
    scroll_report_ignored: /"scroll_report_ignored"/g,
    zero_bound_or_fallback: /_as_float\(state\.attributes\.get\("(?:min|max|min_temp|max_temp)"\)\) or [\d.]+/g,
    explicit_none_bound: /if (?:min_t|max_t|min_n|max_n) is None/g,
  };
  const observations = [];
  if (path === 'custom_components/ikea_bilresa/binding.py') {
    for (const [rule, pattern] of Object.entries(patterns)) {
      for (const match of content.matchAll(pattern)) {
        observations.push({ rule, line: content.slice(0, match.index).split('\n').length });
      }
    }
  }
  return { role, path, revision, digest: digest(content), symbols, observations,
    url: `https://github.com/Vituhlos/ha-ikea-bilresa/blob/${revision}/${path}` };
}

export function symbolComparisons(evidence) {
  const byPath = new Map();
  for (const file of evidence) {
    for (const symbol of file.symbols) {
      const key = `${file.path}:${symbol.name}`;
      if (!byPath.has(key)) byPath.set(key, { path: file.path, symbol: symbol.name, versions: [] });
      byPath.get(key).versions.push({ role: file.role, revision: file.revision,
        digest: symbol.digest, line: symbol.line });
    }
  }
  return [...byPath.values()].filter(s => s.versions.length > 1);
}
