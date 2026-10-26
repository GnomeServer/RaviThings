#!/usr/bin/env python3
"""Applied behavioral defects in disposable module copies only."""
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class Mutation:
    cid: str
    what: str
    apply: Callable[[Path], None]


def replace(old, new, relative='scripts/second_brain.py'):
    def apply(root):
        path = root / relative
        value = path.read_text()
        if value.count(old) != 1:
            raise AssertionError(f'mutation target must occur once: {old!r}')
        path.write_text(value.replace(old, new))
    return apply


MUTATIONS = [
    Mutation('M2-GUARD', 'accept hostile screened input', replace('return 0 if ok else 1', 'return 0', 'shared/case/guard.py')),
    Mutation('M2-SOURCE', 'trust changed source copy', replace("require(not changed, 'source identity changed: ' + ', '.join(str(root / p) for p in changed))", "require(True, 'source identity changed: ' + ', '.join(str(root / p) for p in changed))")),
    Mutation('M2-FREEZE', 'return success on snapshot mismatch', replace("raise ValueError('snapshot changed: ' + ', '.join(bad))", 'return manifest')),
    Mutation('M2-REVISION', 'allow unchanged focal content', replace("require(sig_new != sig_old, 'focal change is only cosmetic (prefix/whitespace/render/ids)')", "require(True, 'focal change is only cosmetic (prefix/whitespace/render/ids)')")),
    Mutation('M2-PRESERVE', 'bypass run missing-rule preflight', replace("    if not rulep.is_file():\n        print(f'HOLD: missing saved instruction: {rulep}', file=sys.stderr)\n        return 2\n    source_identity(work, live=True)", "    if False:\n        print(f'HOLD: missing saved instruction: {rulep}', file=sys.stderr)\n        return 2\n    source_identity(work, live=True)")),
    Mutation('M2-RECEIPT', 'count duplicate reads as packet coverage', replace("require({f'{d}.md' for d in DN} <= reads, 'judge must read all 40 distinct DN sources')", "require(True, 'judge must read all 40 distinct DN sources')")),
]