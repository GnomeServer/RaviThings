import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';

// Execute the shipped Code bodies, with only their n8n input/binary contract.
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
const validate = new AsyncFunction('$input', '$', await readFile(new URL('../reference/historical/controls/validate-batch.js', import.meta.url), 'utf8'));
const checker = JSON.parse(await readFile(new URL('../reference/historical/controls/receipt-checker.json', import.meta.url), 'utf8'));
const compare = new AsyncFunction('$input', checker.nodes.find(node => node.name === 'Compare complete files').parameters.jsCode);
const row = (lot = 'A', overrides = {}) => ({ lot, permit: 'APPROVED', gate_window: 'OPEN', input_disposition: 'NEW', resource_exception: '', pending_status: 'OPEN', ...overrides });
const batch = (rows, source = rows.map(({ pending_status, ...original }) => original)) => validate.call(
  {}, { all: () => rows.map(json => ({ json })) }, () => ({ all: () => source.map(json => ({ json })) }),
);
const bytes = value => Buffer.isBuffer(value) ? value : Buffer.from(value, 'utf8');
const hash = value => createHash('sha256').update(bytes(value)).digest('hex');
const header = 'lot,route,status\n';
const base = `${header}A,pass,READY\nB,hold,OPEN\n`;
const changed = `${header}A,pass,READY\nB,reject,NOT_AUTHORIZED\n`;
const deltaHeader = 'lot,before_route,before_status,after_route,after_status\n';
const delta = `${deltaHeader}B,hold,OPEN,reject,NOT_AUTHORIZED\n`;
async function check(actual = base, { baseline = base, mode = 'exact', prediction, json = {}, omit = [] } = {}) {
  const buffers = { baseline: bytes(baseline), actual: bytes(actual) };
  if (prediction !== undefined) buffers.delta = bytes(prediction);
  const binary = Object.fromEntries(Object.keys(buffers).filter(key => !omit.includes(key)).map(key => [key, { fileName: `${key}.csv`, data: 'NOT_LEGACY_BASE64' }]));
  const input = { json: { mode, baseline_sha256: hash(baseline), actual_sha256: hash(actual), ...json }, binary };
  const result = await compare.call({ helpers: { async getBinaryDataBuffer(index, field) {
    assert.equal(index, 0);
    assert.ok(Object.hasOwn(buffers, field));
    return buffers[field];
  } } }, { all: () => [input] });
  assert.equal(result.length, 1);
  assert.equal(typeof result[0].json.reason, 'string');
  return result[0].json;
}
const hold = async (actual, options) => {
  const report = await check(actual, options);
  assert.equal(report.result, 'HOLD');
  assert.ok(report.reason.length);
  return report;
};

test('batch preserves source values and order under both uniform policy settings', async () => {
  for (const pending_status of ['OPEN', 'NOT_AUTHORIZED']) {
    const source = [
      row('A', { pending_status, permit: 'APPROVED ' }),
      row('B', { pending_status, permit: 'something new', input_disposition: 'CHANGED', resource_exception: 'RACK_CONFLICT' }),
      row('C', { pending_status, permit: '', input_disposition: 'UNCHANGED' }),
      row('D', { pending_status, input_disposition: 'CANCELLED', permit: 'WITHDRAWN' }),
    ];
    const snapshot = structuredClone(source);
    const result = await batch(source);
    assert.deepEqual(source, snapshot);
    assert.deepEqual(result, source.map((json, i) => ({ json: { ...json, _row: i }, pairedItem: { item: i } })));
  }
});

test('batch rejects a source policy column even after Edit Fields overwrites it', async () => {
  await assert.rejects(batch([row()], [row('A', { pending_status: 'NOT_AUTHORIZED' })]), /HOLD:/);
});

test('batch rejects source-value replacement and dropped source rows', async () => {
  const { pending_status, ...original } = row('A', { permit: 'PENDING' });
  await assert.rejects(batch([row()], [original]), /HOLD:/);
  await assert.rejects(batch([row()], [original, { ...original, lot: 'B' }]), /HOLD:/);
});

const invalidBatches = {
  empty: [], duplicate: [row(), row()],
  'empty lot': [row('')], 'blank lot': [row('  ')],
  'comma lot': [row('A,B')], 'quote lot': [row('A"B')],
  'CR lot': [row('A\rB')], 'LF lot': [row('A\nB')], 'NUL lot': [row('A\0B')],
  'tab lot': [row('A\tB')], 'DEL lot': [row('A\x7fB')],
  'extra field': [{ ...row(), route: 'pass' }],
  'missing field': [Object.fromEntries(Object.entries(row()).filter(([key]) => key !== 'permit'))],
  'reordered schema': [Object.fromEntries(Object.entries(row()).reverse())],
  'bad disposition': [row('A', { input_disposition: 'new' })],
  'bad exception': [row('A', { resource_exception: 'rack_conflict' })],
  'cancelled active permit': [row('A', { input_disposition: 'CANCELLED' })],
  'bad pending': [row('A', { pending_status: 'READY' })],
  'mixed pending': [row(), row('B', { pending_status: 'NOT_AUTHORIZED' })],
};
for (const key of Object.keys(row())) invalidBatches[`nonstring ${key}`] = [row('A', { [key]: 1 })];
for (const [name, rows] of Object.entries(invalidBatches)) test(`batch HOLD: ${name}`, async () => {
  await assert.rejects(batch(rows), /HOLD:/);
});

test('exact reports complete byte equality, counts, sizes, names, and native hashes', async () => {
  const report = await check();
  assert.equal(report.result, 'PASS');
  assert.equal(report.raw_byte_equal, true);
  assert.equal(report.row_count_checked, 2);
  assert.equal(report.unchanged_count, 2);
  assert.equal(report.changed_count, 0);
  assert.equal(report.baseline_size, Buffer.byteLength(base));
  assert.equal(report.actual_size, Buffer.byteLength(base));
  assert.equal(report.baseline_name, 'baseline.csv');
  assert.equal(report.actual_name, 'actual.csv');
  assert.equal(report.baseline_sha256, hash(base));
  assert.equal(report.actual_sha256, hash(base));
});

test('predicted change passes with exact before/after and complete accounting', async () => {
  const report = await check(changed, { mode: 'predicted-change', prediction: delta });
  assert.equal(report.result, 'PASS');
  assert.equal(report.raw_byte_equal, false);
  assert.equal(report.row_count_checked, 2);
  assert.equal(report.changed_count, 1);
  assert.deepEqual(JSON.parse(report.changed_ids), ['B']);
  assert.equal(report.unchanged_count, 1);
});

test('native-style BOM and quoted CRLF receipts pass when their framing is preserved', async () => {
  const baseline = '\uFEFF"lot","route","status"\r\n"A","hold","OPEN"\r\n';
  const actual = baseline.replace('"hold","OPEN"', '"reject","NOT_AUTHORIZED"');
  assert.equal((await check(baseline, { baseline })).result, 'PASS');
  assert.equal((await check(actual, { baseline, mode: 'predicted-change', prediction: `${deltaHeader}A,hold,OPEN,reject,NOT_AUTHORIZED\n` })).result, 'PASS');
});

test('header-only delta means zero changes, including header-only receipts', async () => {
  assert.equal((await check(base, { mode: 'predicted-change', prediction: deltaHeader })).result, 'PASS');
  const report = await check(header, { baseline: header, mode: 'predicted-change', prediction: deltaHeader });
  assert.equal(report.result, 'PASS');
  assert.equal(report.row_count_checked, 0);
});

const receiptChanges = {
  'same-count replacement': base.replace('B,hold', 'C,hold'),
  reordered: `${header}B,hold,OPEN\nA,pass,READY\n`,
  missing: `${header}A,pass,READY\n`,
  extra: `${base}C,pass,READY\n`,
  duplicate: base.replace('B,hold', 'A,hold'),
  'undeclared semantic change': changed,
  'LF to CRLF': base.replaceAll('\n', '\r\n'),
  'added BOM': `\uFEFF${base}`,
  'quoted header': base.replace('lot,route,status', '"lot","route","status"'),
  'quoted unchanged field': base.replace('A,pass', '"A",pass'),
  'missing trailing newline': base.slice(0, -1),
  'extra blank record': `${base}\n`,
};
for (const [name, actual] of Object.entries(receiptChanges)) test(`comparison HOLD: ${name}`, async () => {
  await hold(actual);
  await hold(actual, { mode: 'predicted-change', prediction: deltaHeader });
});

const wrongPredictions = {
  'wrong before': delta.replace('B,hold,OPEN', 'B,pass,READY'),
  'wrong after': delta.replace('reject,NOT_AUTHORIZED', 'hold,RESOURCE_CONFLICT'),
  'duplicate prediction': `${delta}B,hold,OPEN,reject,NOT_AUTHORIZED\n`,
  'absent lot': delta.replace('B,hold', 'Z,hold'),
  'reordered header': delta.replace('before_route,before_status', 'before_status,before_route'),
  'missing column': delta.replace(',after_status', ''),
  'extra column': delta.replace('after_status\n', 'after_status,extra\n'),
  'invalid pair': delta.replace('reject,NOT_AUTHORIZED', 'pass,OPEN'),
  'control character': delta.replace('B,hold', 'B\0,hold'),
};
for (const [name, prediction] of Object.entries(wrongPredictions)) test(`prediction HOLD: ${name}`, async () => {
  await hold(changed, { mode: 'predicted-change', prediction });
});

test('declared no-op and a predicted change that never occurs both HOLD', async () => {
  await hold(base, { mode: 'predicted-change', prediction: `${deltaHeader}B,hold,OPEN,hold,OPEN\n` });
  await hold(base, { mode: 'predicted-change', prediction: delta });
  await hold(changed, { mode: 'predicted-change' });
});

test('predicted rows cannot conceal BOM, quote, header, or terminator changes', async () => {
  for (const actual of [changed.replaceAll('\n', '\r\n'), `\uFEFF${changed}`, changed.replace('B,reject', '"B",reject'), changed.replace('reject,NOT_AUTHORIZED', '"reject",NOT_AUTHORIZED'), changed.slice(0, -1)]) {
    await hold(actual, { mode: 'predicted-change', prediction: delta });
  }
});

const malformedReceipts = {
  'invalid UTF8': Buffer.concat([Buffer.from(base), Buffer.from([0xc0, 0xaf])]),
  'truncated UTF8': Buffer.concat([Buffer.from(base), Buffer.from([0xe2, 0x82])]),
  'extra schema': base.replace('lot,route,status', 'lot,route,status,extra'),
  'missing schema': base.replace('lot,route,status', 'lot,route'),
  'reordered schema': base.replace('lot,route,status', 'route,lot,status'),
  'missing value': base.replace('A,pass,READY', 'A,pass'),
  'extra value': base.replace('A,pass,READY', 'A,pass,READY,x'),
  'empty ID': base.replace('A,pass', ',pass'),
  'blank ID': base.replace('A,pass', ' ,pass'),
  'control ID': base.replace('A,pass', 'A\t,pass'),
  'control value': base.replace('READY', 'READY\0'),
  'invalid pair': base.replace('pass,READY', 'pass,OPEN'),
  'unclosed quote': `${header}"A,pass,READY`,
  'quote in bare field': base.replace('A,pass', 'A",pass'),
  'text after quote': base.replace('A,pass', '"A"x,pass'),
  'bare CR': base.replaceAll('\n', '\r'),
};
for (const [name, receipt] of Object.entries(malformedReceipts)) test(`invalid receipt HOLD even when bytes match: ${name}`, async () => {
  await hold(receipt, { baseline: receipt });
});

test('file identity accepts arbitrary bytes and records original digest without parsing CSV', async () => {
  const file = Buffer.from([0, 255, 1, 128]);
  const initial = await check(file, { baseline: file, mode: 'file-identity' });
  assert.equal(initial.result, 'PASS');
  assert.equal(initial.identity_check, 'initial_record_only');
  assert.equal(initial.expected_sha256, '');
  assert.equal(initial.row_count_checked, 0);
  const verified = await check(file, { baseline: file, mode: 'file-identity', json: { expected_sha256: initial.baseline_sha256 } });
  assert.equal(verified.result, 'PASS');
  assert.equal(verified.identity_check, 'matched');
  const replacement = Buffer.from([0, 255, 2, 128]);
  const mismatch = await hold(replacement, { baseline: replacement, mode: 'file-identity', json: { expected_sha256: initial.baseline_sha256 } });
  assert.equal(mismatch.raw_byte_equal, true);
  assert.equal(mismatch.expected_sha256, initial.baseline_sha256);
  assert.equal(mismatch.identity_check, 'mismatch');
  await hold(replacement, { baseline: file, mode: 'file-identity' });
});

test('invalid mode, native hash, and expected digest inputs produce HOLD reports', async () => {
  await hold(base, { mode: 'EXACT' });
  for (const key of ['baseline_sha256', 'actual_sha256', 'expected_sha256']) {
    await hold(base, { json: { [key]: 'bad' } });
    await hold(base, { json: { [key]: 123 } });
  }
  await hold(base, { json: { actual_sha256: '0'.repeat(64) } });
});

test('fundamentally missing required binary fails explicitly', async () => {
  for (const field of ['baseline', 'actual']) await assert.rejects(check(base, { omit: [field] }), /HOLD:/);
});

test('valid UTF8 lots and all allowed receipt pairs pass without normalization', async () => {
  const receipt = `${header}é,pass,READY\n東京,hold,OPEN\nC,hold,RESOURCE_CONFLICT\nD,reject,NOT_AUTHORIZED`;
  const report = await check(receipt, { baseline: receipt });
  assert.equal(report.result, 'PASS');
  assert.equal(report.row_count_checked, 4);
});

test('malformed delta encoding and empty predictions HOLD', async () => {
  for (const prediction of ['', Buffer.concat([Buffer.from(delta), Buffer.from([0xff])]), delta.replace('B,hold', ',hold')]) {
    await hold(changed, { mode: 'predicted-change', prediction });
  }
});

test('comparison rejects multiple input items with a structured report', async () => {
  const buffer = bytes(base);
  const item = { json: { mode: 'exact', baseline_sha256: hash(base), actual_sha256: hash(base) }, binary: { baseline: { fileName: 'b.csv' }, actual: { fileName: 'a.csv' } } };
  const [result] = await compare.call({ helpers: { getBinaryDataBuffer: async () => buffer } }, { all: () => [item, item] });
  assert.equal(result.json.result, 'HOLD');
  assert.ok(result.json.reason);
});
