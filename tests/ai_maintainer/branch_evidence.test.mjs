import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { pythonSymbols, sourceEvidence, symbolComparisons } from '../../tools/ai_maintainer/branch_evidence.mjs';

test('real panel API nested unsubscribe functions stay distinct across all five roles', async () => {
  const content = await readFile(new URL('../../custom_components/ikea_bilresa/panel_api.py', import.meta.url), 'utf8');
  const evidence = ['stable','main','development','prBase','prHead'].map(role => sourceEvidence({
    role, path: 'custom_components/ikea_bilresa/panel_api.py', revision: 'a'.repeat(40), content,
  }));
  const comparisons = symbolComparisons(evidence);
  assert.equal(comparisons.filter(c => c.symbol.endsWith('._unsubscribe')).length, 2);
  assert.ok(comparisons.every(c => c.versions.length === 5));
});

test('multiline signatures and repeated scoped definitions keep unique stable identities', () => {
  const symbols = pythonSymbols('class C:\n    def outer(\n        self,\n    ):\n        def inner():\n            pass\n    def value(self):\n        return 1\n    def value(self):\n        return 2\ndef outer():\n    def inner():\n        pass\n');
  assert.ok(symbols.some(s => s.name === 'C.outer.inner'));
  assert.ok(symbols.some(s => s.name === 'outer.inner'));
  assert.equal(new Set(symbols.map(s => s.name)).size, symbols.length);
});

test('property getter/setter occurrences remain bounded per source role', () => {
  const content = 'class C:\n    @property\n    def value(self):\n        return 1\n    @value.setter\n    def value(self, new):\n        pass\n';
  const evidence = ['stable','main','development','prBase','prHead'].map(role => sourceEvidence({
    role, path: 'example.py', revision: 'a'.repeat(40), content,
  }));
  const comparisons = symbolComparisons(evidence);
  assert.equal(comparisons.length, 2);
  assert.ok(comparisons.every(c => c.versions.length === 5));
});
