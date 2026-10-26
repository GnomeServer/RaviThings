# Round 1 — voice review (2026-10-02)

Reviewer: read-only voice reviewer agent on the Module 10 worktree. Findings are reproduced verbatim; the closing list records what changed in revision 2.

## 1. Fix the inverted min_confidence example in the gate-setting rule

AI_Harness_Bootcamp_2/module-10-typed-decisions/shared/MODULE_10_LAB.md:335

MODULE_10_LAB.md:335 says that if a wrong answer had declared confidence 0.85, "a gate below 0.86 would not have caught it". In chalk.py:330 the router sends a message to REVIEW when declared < min_confidence. So 0.85 is caught by any gate of 0.86 or higher (any gate above 0.85) and slips through at 0.85 or lower. The sentence gets the comparison backwards and contradicts the instruction that follows it. Replacement: "The router sends a message to REVIEW when its weakest declared confidence is below `min_confidence`. If a wrong answer in the sample had declared confidence `0.85`, any gate of `0.85` or lower lets it through, so set the gate above the highest declared confidence of any answer that was wrong, or set it to `1.0` if declared confidence earned no trust."

## 2. Define how a yes/no answer becomes a declared confidence

AI_Harness_Bootcamp_2/module-10-typed-decisions/shared/MODULE_10_LAB.md:182

MODULE_10_LAB.md:328 applies min_confidence across request and authority, and line 313 reads declared confidence off the agreement report. But yes/no answers carry only p (line 182, questions.json answer_shape). The code converts p to |2p-1| (chalk.py:210-211, used at 252 and 328), and the page never says so. A learner sees p=0.85 for authority and the report prints 0.7. They cannot reconcile the numbers, and they may think 0.85 is above a 0.8 gate when the router treats it as 0.7. Replacement for line 182: "A **yes-or-no** question is answered with `p`, the probability that the answer is yes. `0.95` means almost certainly yes; `0.5` means the model cannot tell. For gates and comparisons, the declared confidence of a yes-or-no answer is its distance from 0.5, doubled: `p` of `0.85` or `0.15` both count as confidence `0.7`."

## 3. Stop the Decision template inviting both decision tokens

AI_Harness_Bootcamp_2/module-10-typed-decisions/shared/MODULE_10_LAB.md:379

The template at MODULE_10_LAB.md:379 asks for "PASS FOR CLASS REVIEW or HOLD, and the condition that would change it". The verifier (verify_decisions.py:149-152) holds unless exactly one of the strings PASS FOR CLASS REVIEW and HOLD appears in that section. A learner who follows the template literally writes, for example, "PASS FOR CLASS REVIEW. It would become HOLD if…". That fails with a message the learner cannot connect to their sentence. Replacement: "(Write exactly one of PASS FOR CLASS REVIEW or HOLD. Then state the condition that would change it without repeating either phrase, for example 'This changes if the desk lead rejects CL-0nn.')"

## 4. Make the authority rule identical in the desk rules and the question

AI_Harness_Bootcamp_2/module-10-typed-decisions/shared/case/DESK_RULES.md:29

DESK_RULES.md:29 counts approval only as the word "approved" in a message *from* the administrative officer, or a K3-REQ reference. The authority instruction in questions.json:47 and the label bullet in MODULE_10_LAB.md (~line 222) accept any message that "cite[s] approval by the Clinic K-3 administrative officer". A careful reader can take that as a ward nurse writing "the AO approved this". Under the question, that message is yes; under the desk rule, it is no. That makes the labels and the model's answers diverge for reasons outside the model. Replacement for the question instructions: "Is this message from the Clinic K-3 administrative officer and does it say approved, or does it carry a requisition reference of the form K3-REQ followed by a number? A message from anyone else that reports the officer's approval does not count, nor does a reference for another clinic, a nurse officer's own approval, an OR lead's need, a vendor's offer, or a note that calls itself approved."

## 5. Make the REVIEW route meaning cover MIXED sizes

AI_Harness_Bootcamp_2/module-10-typed-decisions/shared/case/DESK_RULES.md:45

Router rule 4 (MODULE_10_LAB.md:326) sends a request with MIXED sizes to REVIEW. The routes table in DESK_RULES.md (around line 49) defines REVIEW only as "a message the model could not type cleanly, or one it answered with low declared confidence", and the handoff template repeats that. A MIXED answer is a clean typed answer, so a learner reading routing-1.csv sees a route the rules say cannot occur. Replacement for the REVIEW meaning: "A request for two or more sizes in one message, a message the model could not type cleanly, or one it answered with low declared confidence. A person reads it."

## 6. Remove 'write the requirement line' from step 8

AI_Harness_Bootcamp_2/module-10-typed-decisions/shared/MODULE_10_LAB.md:20

Step 8 at MODULE_10_LAB.md:20 says "Decide the review queue, write the requirement line, and run the final check". The router writes requirement-N.json in step 7. Step 8 only summarizes it in the handoff, so a learner may look for a separate requirement-line command or file. Replacement: "8. Decide the review queue, write the handoff, and run the final check."

## 7. Remove the duplicate 'cancellation' exclusion from the request question

AI_Harness_Bootcamp_2/module-10-typed-decisions/shared/controls/questions.json:15

questions.json:15 lists "a cancellation" and "a permit note" among non-requests. "Permit note" is not defined anywhere in the learner files. The cancellation clause can be read two ways. A correction that cancels one size and restates another is both a cancellation and a "changed or restated requirement", so a careful labeller can answer it either way. Replacement fragment: "A message that only cancels an earlier request, with no new requirement, is not a request; a message that cancels and restates is a request. A report, a stock count, a thank-you, a receipt confirmation, a status question, a vendor's offer, a note about a vehicle or road permit, and a request for a different clinic are not requests."

## Reviewer summary

The commands and Expected lines match the scripts. The gate-setting rule is the problem: it reverses the router's comparison and never defines how a yes/no answer gets a declared confidence. Separately, the handoff template steers learners into a Decision section that the verifier rejects, and the authority rule is worded two incompatible ways.

## Closed in revision 2

- Inverted `min_confidence` example: corrected to the router's comparison.
- Yes-or-no confidence undefined: `|2p − 1|` stated at first use.
- Decision template inviting both tokens: rewritten.
- Authority rule worded two ways: one rule in the desk rules, the question, and the lab.
- `REVIEW` meaning missing `MIXED`: table updated.
- Step 8 `write the requirement line`: removed.
- `permit note` and the cancellation ambiguity: request question reworded.
