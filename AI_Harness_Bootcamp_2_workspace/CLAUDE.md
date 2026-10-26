# AI Harness Bootcamp — authoring rules

Constraints for anyone (human or AI) creating or revising course content in this repository.

## Course progression rule

Every project assumes learners can already do everything required in the earlier projects. Earlier capabilities may return as prerequisites, operating constraints, or evidence standards, but they are not new learning objectives and must not be retaught as though the class is seeing them for the first time. Give a short reminder or link back at the point of use; reserve project time for the next capability.

Write each project's mastery claim and objectives by answering:

> **What can the learner now do that they could not do before this project?**

Apply these tests whenever a project is created or revised:

1. **Capability-delta test:** complete the sentence "Before this project, the learner could ___. After this project, the learner can ___." The second clause must name a meaningful new capability, not a new file, tool, scenario, or repetition count.
2. **Prerequisite test:** if an earlier project already taught the skill, state it as assumed knowledge or a required quality bar. Do not count it again as an objective.
3. **Dependency test:** each new objective must use at least one earlier capability and extend it into work the learner could not previously perform.
4. **Evidence test:** files, installations, checkboxes, logs, reflections, and transfer entries may prove or reinforce learning. They are not objectives by themselves.
5. **Progression test:** the mastery claim must add one clear capability to the course arc without restating an earlier mastery claim in different words.

Applied to `LEARNING_OBJECTIVES.md` and `modules/core/`: an earlier skill may stay in a project's requirements as a prerequisite, but repeating it does not earn the new capability. If a requirement could move unchanged to an earlier project, it is not a new objective — state it as assumed knowledge, or rewrite it around what this project adds.

Remediation is the exception. If learners cannot perform a prerequisite, repair it explicitly as prerequisite recovery without redefining it as the current project's new content.

## Learner-facing content

Use detailed explanations, behind-the-scenes discussion, orientation, rationale, recaps, worked examples, diagrams, screenshots, supplementary guides, and handouts when they help the learner. Choose the format that serves the task rather than a fixed page template. Explain unfamiliar terms instead of blacklisting identifier-shaped words. Keep claims about execution tied to observed evidence: narration, proposed commands, and generated answers do not prove that work ran or that a person accepted it.

The bootcamp is ungraded. Do not add learner scores, qualification decisions, scoring rubrics, or exercise-grading guidance. Technical checks and work decisions may still return `PASS` or `HOLD`.

## Repository shape

The website is the course. Edit the owning maintainer source under `AI_Harness_Bootcamp_2/` and publish HTML through `scripts/build_course.py`; do not create a second raw-Markdown navigation site. Additional canonical explanatory/reference pages, prompt sheets, and accessible or downloadable handouts may live under the owning module when explicitly registered in `course.json`. Raw learner resources need not be limited to files edited during an exercise. `course.json` owns the publication allowlist; never allowlist or serve private/staff sources or answer keys. Serve only generated `site/`, never the repository root or staff sources. See [`README.md`](README.md) for the path map and verification commands.

## Reformation scenario memory

Mission-thread doctrine and the ten session project specs live in `MISSION_THREAD_SCENARIOS.md`. Read that file before researching mission threads, Cold Lantern, or a Reformation morning or afternoon scenario. Re-open a listed source only when the question is not answered there.
