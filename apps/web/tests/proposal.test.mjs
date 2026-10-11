import test from 'node:test';
import assert from 'node:assert/strict';
import { validateProposal } from '../src/lib/proposal.ts';
test('proposal validation matches Core PDF size and media contract', () => {
  const file = { name: 'proposal.PDF', type: 'application/pdf', size: 15 * 1024 * 1024 };
  assert.equal(validateProposal(file), null);
  assert.match(validateProposal({ ...file, size: file.size + 1 }), /15 MiB/);
  assert.match(validateProposal({ ...file, size: 0 }), /1 byte/);
  assert.match(validateProposal({ ...file, name: 'photo.png' }), /PDF/);
  assert.match(validateProposal({ ...file, type: 'image/png' }), /PDF/);
});
