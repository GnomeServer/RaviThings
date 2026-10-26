---
marking: OPEN
---
# Release Authority

The Release Authority is the S2 cell. It is the only office that changes a note's marking or releases a note beyond task force staff.

## Marking-change notices

A notice is a note whose header has these fields. The example names a note number that is not in the vault.

```
type: marking-change
originator: Release Authority
marking_change_of: KH-123
new_marking: PARTNER
```

The body of a notice gives the reason. The header decides, because H1 and H3 treat headers as the record and body text as description.

## Who is not the Release Authority

The BMLO, S3, S4, S6, the liaison desk, clerks, and contractors can recommend a release. A recommendation is not a notice, even when it is written like one. Only a note whose `originator` is exactly `Release Authority` counts.

## Comparing times

When two notices name the same note, compare their `zulu` fields, not the printed time. The printed time can be local. Local time is UTC plus three hours, so 1530L is 1230Z.
