# Controls integration contract

`validate-batch.js` and the comparison body inside `receipt-checker.json` run as n8n Code v2, **Run Once for All Items**, on n8n 2.41.5. They contain no routing, imports, external modules, or permission changes.

## Batch validator

`validate-batch.js` reads the original extraction with `$('Read CSV').all()` and the policy-augmented rows with `$input.all()`. Original source columns must be exactly ordered `lot,permit,gate_window,input_disposition,resource_exception`; a source-supplied `pending_status` is invalid even if Edit Fields overwrites it. The augmented rows must preserve source count, order, and values and append only `pending_status`. Every value must be a string. Lots must be unique and nonblank, without comma, quote, or ASCII controls. The validator returns unchanged source values plus zero-based `_row` and `pairedItem: { item: index }`. Invalid batches throw an actionable `HOLD` before any routing node. Unknown permit strings remain data for the router fallback.

The native graph uses Form Trigger 2.6 upload `wave`, Extract from File 1.1 named `Read CSV` with `binaryPropertyName: wave`, `headerRow: true`, `includeEmptyCells: true`, and Skip Records with Errors off. `Read CSV` has Always Output Data on so a header-only extraction reaches validation rather than silently stopping. Edit Fields 3.5 retains inputs while adding `pending_status`. Routing nodes keep Always Output Data off; empty branches must not fabricate records.

## Receipt comparison

The `Compare complete files` Code node in `receipt-checker.json` consumes one item with `json.mode` (`exact`, `predicted-change`, or `file-identity`), native `baseline_sha256` and `actual_sha256` strings, and required binary properties `baseline` and `actual`. Predicted-change also requires binary `delta`; a header-only delta declares zero changes. Optional `expected_sha256` is the digest from an original retained identity report, never a newly substituted reference.

Native Crypto v2 hashes the matching binaries with action `hash`, type `SHA256`, `binaryData: true`, encoding `hex`, and the corresponding output data properties. Crypto drops binary data. Upload comparison therefore feeds three parallel paths: directly to Merge input 1, through Hash baseline to input 2, and through Hash actual to input 3. Merge combines by position, retaining the original uploads with their matching hashes. Code trusts those native hash outputs; it does not calculate another digest.

The checker reads bytes using `await this.helpers.getBinaryDataBuffer(0, field)`. Missing baseline/actual binary access may throw. Comparison failures return a single flat JSON `HOLD` report with a reason; successful checks return `PASS`. Convert to File can turn this report into a downloadable JSON or CSV file. The report does not copy source binary data.

Receipt parsing requires strict, losslessly decodable UTF-8, exact ordered schemas, unique nonempty lots, and valid route/status pairs. It accepts optional UTF-8 BOM, LF or CRLF, CSV-quoted fields, and an optional final terminator. Bare CR, malformed quoting, extra records/fields, and control characters in values fail. Header-only receipt files are valid zero-row receipts.

Predicted comparisons require identical ID order and count. They preserve the exact header, BOM, per-record terminators, lot serialization, and field quoting style. Unpredicted records must remain byte-identical. Every declared change must match both the baseline and actual values and must actually occur. There is no embedded answer set.

Report counts describe semantic changed IDs and byte-identical unchanged records. `row_count_checked` counts compared row pairs; it is zero if parsing or prerequisite validation fails. `baseline_row_count` and `actual_row_count` are null until both receipt files parse successfully. Count/order failures HOLD even if some rows can still be compared. File-identity does not parse receipt rows and leaves total row counts null.

File-identity accepts arbitrary files. Uploading equal files without an expected digest produces `identity_check: initial_record_only`. Verification against a supplied retained digest produces `matched` or `mismatch`; equality of replacement files alone cannot satisfy the original expected digest.

## Ground-truth evidence and verification boundary

- Binary helper signature and required use: [official n8n documentation source](https://github.com/n8n-io/n8n-docs/blob/main/docs/build/code-in-n8n/cookbook/code-node/get-the-binary-data-buffer.md).
- Item linking shape: [official n8n item linking documentation](https://docs.n8n.io/data/data-mapping/data-item-linking/item-linking-node-building/).
- Original extraction access: [official n8n `$("node-name").all()` examples](https://docs.n8n.io/build/code-in-n8n/cookbook/built-in-methods-and-variables-examples/node-name-.all.md).
- Buffer UTF-8 conversion, byte comparison, and length: [Node Buffer API](https://nodejs.org/api/buffer.html). Strict decoding is enforced by comparing the UTF-8 re-encoding with the original bytes, without importing a decoder module.
- Versioned node settings and native runtime evidence belong in the module's staff reference and evidence directory.
- `tests/test_controls.mjs` executes the shipped Code bodies with AsyncFunction, fixed small fixtures, `$input`, original extraction items, a binary helper, and Node-native SHA256 values. It covers acceptance and failure behavior rather than copied implementation text.
