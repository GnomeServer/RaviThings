# Superseded evidence

These files record the v1 oracle running against the v1 Reference (SHA-256 `a162ca34…`). Both have
been replaced. They are kept so the change is auditable, not as evidence about the module as it
stands. `reference/AMENDMENTS.md` records what changed and why.

The v1 suite reported `PASS 171 / FAIL 0` on a module tree that contained three of its own absolute
failures, two learner files no scan read, an unpublished module, and a step that dirtied the clone
the next step required clean. That result is the reason the v2 oracle carries a mutation corpus.
