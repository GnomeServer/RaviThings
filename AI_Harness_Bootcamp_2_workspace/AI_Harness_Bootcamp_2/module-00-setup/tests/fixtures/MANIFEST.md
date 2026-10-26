# Fixture manifest

Each failing fixture is the canonical brief with exactly one substitution.
The checker must reject it, and must name the listed check.

| Fixture | Must fail on |
|---|---|
| `fail/no-title.md` | title line |
| `fail/too-few-sections.md` | section count |
| `fail/too-short.md` | word count 500-900 |
| `fail/too-long.md` | word count 500-900 |
| `fail/wrong-commodity.md` | commodity |
| `fail/wrong-origin.md` | origin |
| `fail/wrong-clinic.md` | destination |
| `fail/missing-thursday.md` | thursday |
| `fail/missing-friday.md` | friday |
| `fail/wrong-hours.md` | documentation hours |
| `fail/missing-contact.md` | contact line |
| `fail/requested-wrong.md` | requested 40 |
| `fail/on-hand-changed-to-19.md` | on-hand 27 |
| `fail/wrong-pen.md` | pen 4 |
| `fail/claims-release.md` | custody not release |
| `fail/missing-owner.md` | release owner |
| `fail/assigns-vehicle.md` | no vehicle |
| `fail/approves-permit.md` | no permit |
| `fail/confirms-receipt.md` | no receipt |
| `fail/claims-supportable.md` | supportability unknown |
| `fail/expect-window.md` | prohibited sentence |
| `fail/hs3-assigned.md` | HS-3 |
| `fail/stages-for-truck.md` | no delivery promise |
| `fail/writes-go.md` | no GO |
| `fail/invented-clock-time.md` | no invented clock time |
| `fail/public-distribution.md` | no prohibited distribution |

| Fixture | Must pass |
|---|---|
| `pass/canonical.md` | every check |
| `pass/paraphrase.md` | every check, using different wording |