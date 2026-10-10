import test from 'node:test';
import assert from 'node:assert/strict';
import { sourceUrl } from '../src/lib/source-url.ts';
test('untrusted citation links only permit absolute HTTP sources', () => {
  assert.equal(sourceUrl('https://example.org/a.pdf'), 'https://example.org/a.pdf');
  for (const raw of ['javascript:alert(1)', 'data:text/html,abc', '/relative', '', null]) assert.equal(sourceUrl(raw), null);
});
