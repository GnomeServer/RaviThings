# Round 1 — technical review (2026-10-02)

Reviewer: read-only technical reviewer agent on the Module 10 worktree. Findings are reproduced verbatim; the closing list records what changed in revision 2.

## 1. Verify agreement against the answers file the learner actually used

AI_Harness_Bootcamp_2/module-10-typed-decisions/shared/verify/verify_decisions.py:115

Severity: blocker on the documented recovery path. The `agreement()` check is hardcoded to `shared["answers"]["answers-1.json"]`. The lab's validation Recovery (MODULE_10_LAB.md:287) tells the learner to validate `decide-2` into `answers-2.json` and to use `answers-2.json` wherever the page says `answers-1.json`. On that path `answers-1.json` never exists, because `validate_answers.py` writes nothing on HOLD. I reproduced it with `synthetic_bundle.Bundle`: I removed `answers-1`, `agreement-1`, `routing-1` and `requirement-1`, added a `decide-2` receipt, wrote `answers-2.json`, built `agreement-1.json` from `answers-2`, and routed from `answers-2`. The real verifier then printed `HOLD agreement: missing field 'answers-1.json'`, and the final result was 1 hold. A learner who follows the page exactly can never reach PASS, and nothing on the page explains how to repair it. Smallest fix: compare against the answers file that `requirement-{final}.json` names, as `routing()` already does, or against the lowest-numbered verified answers file. For example: `source = min(shared["answers"], key=lambda n: int(n.split("-")[1].split(".")[0]))`, then use `shared["answers"][source]` and name it in the HOLD text.

## 2. Refuse to validate a receipt whose launcher result is HOLD

AI_Harness_Bootcamp_2/module-10-typed-decisions/scripts/validate_answers.py:20

Severity: major. `validate_answers.py` reads only `response.md`. It never checks `result.json` (`status`/`exit_code`), so it accepts the reply from a run the launcher already held (EXIT=1). The lab's EXIT=1 Recovery (MODULE_10_LAB.md:263) says to keep `decide-1` and use `decide-2`. The next fence (lines 274/280) still hardcodes `"$E/decide-1"`, so the learner validates the held receipt into `answers-1.json`. The verifier then audits every `out/answers-*.json` (verify_decisions.py:99-111). I reproduced this with the bundle by giving `decide-1` an audit error: the result was 4 holds (`HOLD answers: decide-1: …`, then `agreement`, `routing` and `handoff` all held). Because the page forbids deleting or editing evidence, the attempt can never pass. The same trap applies in the stretch if a held `decide-2` reply is valid JSON. Smallest fix, in `validate_answers.py` after the reply is read: `result = chalk.load_json(receipt / "result.json"); if result.get("status") != "PASS": raise chalk.Hold(f"{receipt.name} is a held launcher run ({result.get('reason')}); validate the next PASS receipt")`. Also add one clause to line 263: “…and validate `E/decide-2` instead of `E/decide-1` in the next step.”

## 3. Report a downstream skip, not 'missing field', when answers held

AI_Harness_Bootcamp_2/module-10-typed-decisions/shared/verify/verify_decisions.py:98

Severity: minor. If the answers check holds, `shared["answers"]` is set to `{}` before the HOLD is raised. Line 102 runs first, so the key `"answers"` exists. `agreement()` then raises `KeyError('answers-1.json')`, which is not in the downstream-key list on line 67, so the verifier prints `HOLD agreement: missing field 'answers-1.json'`. I observed this in the CLI walkthrough and in the held-receipt reproduction. The learner reads it as a missing file or field rather than as a consequence of the earlier HOLD. Smallest fix: assign `shared["answers"]` only after the loop finishes (build a local dict, then `shared["answers"] = local`). The existing "not checked because an earlier check held" branch then fires.

## 4. Candidate finder drops sentence-final numbers; lab claims 'every number'

AI_Harness_Bootcamp_2/module-10-typed-decisions/scripts/chalk.py:23

Severity: minor. The `NUMBER` lookahead `(?![\w:.-])` rejects any digit run followed by a period, and backtracking cannot rescue it, so a number at the end of a sentence disappears. Hyphenated word numbers are also missed. In the shipped case, `build_state` gives no candidate for `7.5` in CL-013 ("fine on 7.5."), CL-038 ("20 boxes size 7.5.") or CL-034 ("7.0."), none for `3` in CL-039 ("covers ward 3."), and none for eighteen, thirty-two or twenty-six in CL-001; CL-001 gets only `nine boxes`. Probes show the same: "item 3." yields []; "1,200 gloves" splits into two candidates; "12-15 boxes" yields []. MODULE_10_LAB.md:156 tells learners the builder "finds every number in each message", which is false on their own state. No requested quantity in this case falls at a sentence end, so routing is unaffected. Smallest fix (wording; keeps 68 candidates, the answer key and the tests): change line 156 to “finds each number followed by more words in the same sentence (and the number words one to ten)”. The code alternative `(?![\w:-]|\.\d)` yields 73 candidates and would require updating the Expected line and the key.

## 5. Name duplicated message IDs in the answers-order HOLD

AI_Harness_Bootcamp_2/module-10-typed-decisions/scripts/chalk.py:138

Severity: minor. When the reply repeats one message (41 entries, all 40 IDs present), `missing` and `extra` are both empty and the duplicates sit next to each other, so the sort test returns True. The learner then sees `HOLD: answers must cover exactly the forty messages in state order; missing [], unexpected [], order kept: True`, which contradicts itself. I reproduced this with `answers[:5] + [answers[4]] + answers[5:]`. Smallest fix: compute `duplicates = sorted({i for i in got_ids if got_ids.count(i) > 1})` and add `, duplicated {duplicates[:3]}` to the message, evaluating `order kept` only when there are no duplicates.

## 6. Accept an uppercase JSON fence tag consistently with the lab's note: rule

AI_Harness_Bootcamp_2/module-10-typed-decisions/scripts/chalk.py:193

Severity: minor. The lab (line 283) says a fenced reply is accepted with a `note:` line. `parse_reply`'s pattern `r"```(?:json)?\s*\n(.*?)\n```"` is case-sensitive, so a reply fenced as ```JSON is held with the misleading reason "the reply does not start with a JSON object; prose around the document is a violation". I observed this with `parse_reply('```JSON\n{"a":1}\n```')`; the lowercase tag, a bare fence and CRLF fences all pass. Smallest fix: add `re.I`, i.e. `re.fullmatch(r"```(?:json)?\s*\n(.*?)\n```", stripped, re.S | re.I)`.

## Reviewer summary

I ran every lab fence in order on macOS from a fresh `prepare_work.py 10` work copy, using a key-derived receipt in place of a live run. Each Expected line matched the printed output: 68 candidates, `wrote 10 sample entries`, `LABELS FROZEN`, 280 typed answers, the AGREEMENT/ROUTED/STABILITY lines, and the launcher PASS text. The launcher flags match `run_omp.py` (read profile by default, `--instruction` resolved). The verifier's REFORMATION path and imports, the `requirement-N` parsing, the routing CSV round-trip and all 30 mutation anchors check out; `test_adequacy` passed with 0 survivors. Two defects block a learner from reaching PASS. First, the verifier hardcodes `answers-1.json` in its agreement check, so the lab's own recovery path (using `answers-2`) always holds. Second, `validate_answers` accepts a held launcher receipt, and once that answers file exists the final check can never pass.

## Closed in revision 2

- Hard-coded `answers-1.json`: fixed as above.
- Held launcher receipts validated: `validate_answers.py` refuses `result.status != PASS`; oracle check and mutation added.
- Cascade message: `shared['answers']` assigned after the loop.
- `every number` claim: lab wording corrected.
- Duplicate IDs: named in the HOLD.
- Upper-case fence tag: accepted.
