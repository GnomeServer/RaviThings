// n8n Code v2, Run Once for All Items. Validation only; routing belongs to nodes.
const items = $input.all();
const columns = ['lot', 'permit', 'gate_window', 'input_disposition', 'resource_exception', 'pending_status'];
const sourceColumns = columns.slice(0, -1);
const sourceItems = $('Read CSV').all();
const seen = new Set();
const hold = (message) => { throw new Error(`HOLD: ${message}`); };
if (!items.length) hold('Upload a nonempty batch with the required CSV header.');
if (sourceItems.length !== items.length) hold('Pending rule must preserve every Read CSV row.');
let pending;
return items.map((item, index) => {
  const row = item.json;
  const where = `source row ${index + 1}`;
  const source = sourceItems[index].json;
  if (!source || Object.keys(source).length !== sourceColumns.length ||
      Object.keys(source).some((key, i) => key !== sourceColumns[i])) {
    hold(`${where}: Read CSV must contain exactly the ordered fields ${sourceColumns.join(',')}; do not supply pending_status in the source.`);
  }
  if (!row || Object.keys(row).length !== columns.length ||
      Object.keys(row).some((key, i) => key !== columns[i])) {
    hold(`${where}: expected ordered fields ${columns.join(',')}; remove extra fields and restore missing fields.`);
  }
  for (const key of columns) {
    if (typeof row[key] !== 'string') hold(`${where}: ${key} must be text.`);
  }
  if (sourceColumns.some(key => row[key] !== source[key])) hold(`${where}: Pending rule changed a source value; retain every original field.`);
  if (!row.lot.trim() || /[,"\x00-\x1f\x7f]/.test(row.lot)) hold(`${where}: lot must be nonempty and contain no comma, quote, or ASCII control character.`);
  if (seen.has(row.lot)) hold(`${where}: duplicate lot ${JSON.stringify(row.lot)}; use unique lots.`);
  seen.add(row.lot);
  if (!['NEW', 'CHANGED', 'CANCELLED', 'UNCHANGED'].includes(row.input_disposition)) hold(`${where}: invalid input_disposition.`);
  if (!['', 'RACK_CONFLICT'].includes(row.resource_exception)) hold(`${where}: invalid resource_exception.`);
  if (row.input_disposition === 'CANCELLED' && row.permit !== 'WITHDRAWN') hold(`${where}: CANCELLED requires permit WITHDRAWN.`);
  if (!['OPEN', 'NOT_AUTHORIZED'].includes(row.pending_status)) hold(`${where}: pending_status must be OPEN or NOT_AUTHORIZED.`);
  if (index && row.pending_status !== pending) hold(`${where}: pending_status must be uniform across the batch.`);
  pending = row.pending_status;
  return { json: { ...row, _row: index }, pairedItem: { item: index } };
});
