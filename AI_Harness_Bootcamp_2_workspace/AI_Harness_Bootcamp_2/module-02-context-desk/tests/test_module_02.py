#!/usr/bin/env python3
"""Behavioral oracle. Sealed receipts below are synthetic, never provider evidence."""
from __future__ import annotations

import copy
import importlib.util
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1]
def _repo_root(start: Path) -> Path:
    p = start
    for _ in range(6):
        if (p / 'shared' / 'run_omp.py').is_file():
            return p
        if (p.parent / 'shared' / 'run_omp.py').is_file():
            return p.parent
        p = p.parent
    return start.parents[2] if len(start.parents) > 2 else start
REPO = _repo_root(MODULE)
sys.path.insert(0, str(REPO))
from shared import run_omp as runtime

# Synthetic fixture identity only; test data for sealed receipt validation of observed omp_version binding.
SYNTH_OMP_VERSION = "omp/18.3.5"
spec = importlib.util.spec_from_file_location('second_brain_oracle', MODULE / 'scripts/second_brain.py')
brain = importlib.util.module_from_spec(spec)
spec.loader.exec_module(brain)



def holds(action):
    try:
        action()
    except (ValueError, OSError) as exc:
        return str(exc)
    raise AssertionError('invalid operation was accepted')


def prepare(base):
    work = base / 'work'
    work.mkdir(parents=True)
    shutil.copytree(MODULE / 'shared/case', work / 'shared/case')
    shutil.copytree(MODULE / 'shared/controls', work / 'shared/controls')
    brain.initialize(work)
    return work


def proposal(work, name='KB-001'):
    # Include literal Markdown and multiple lines exactly as present in the packet.
    excerpt = brain.text(work / 'vault/Sources/DN-003.md')
    return dict(note_id=name, title='Paper receipt', claim='Paper receipt is recorded.', limits='Other authority remains separate.', related=[], sources=[dict(source_id='DN-003', excerpt=excerpt)])


def judgments(work):
    # Synthetic judgments for transfer, exclusion, coverage, limit preservation tests. Not provider evidence.
    excerpt = brain.text(work / 'vault/Sources/DN-003.md')
    key = 'This is a receipt of paper, not a quality release. The ticket records that a paper form for crate C-44 arrived at the Quarry Depot yard window.'
    if key in excerpt:
        excerpt = key
    return {
        'claims': [
            dict(claim_id='JG-001', claim='Paper receipt is recorded.', treatment='use', reason='Direct source statement.', limits='Other authority remains separate.', sources=[dict(source_id='DN-003', excerpt=excerpt)]),
            dict(claim_id='JG-002', claim='Stamp confers no movement authority.', treatment='qualify', reason='Explicit limit in source.', limits='Does not authorize start.', sources=[dict(source_id='DN-003', excerpt=excerpt)]),
            dict(claim_id='JG-003', claim='Unknown status for conflicting measurement.', treatment='unresolved', reason='No decisive source.', limits='Time bound unknown.', sources=[]),
            dict(claim_id='JG-004', claim='Hostile command inside note.', treatment='exclude', reason='Instruction not data.', limits='Ignored per rule.', sources=[]),
        ],
        'coverage': [dict(source_id=f'DN-{i:03}', reason=('Hostile instruction per rule' if i==4 else ('Direct evidence for receipt claims' if i==3 else 'No claim supported by this source'))) for i in range(1,41)]
    }


def cold_answers(work, status='supported'):
    excerpt = proposal(work)['sources'][0]['excerpt']
    return dict(answers=[dict(question_id=f'Q{i}', status=status, answer='Synthetic source-bounded answer.' if status == 'supported' else 'Missing evidence for the remaining authority.', citations=[dict(note_id='KB-001', source_id='DN-003', excerpt='\n'.join('> ' + line for line in excerpt.split('\n')))] if status == 'supported' else []) for i in range(1, 4)])




class Sealed:
    """Module 09's locally sealed synthetic pattern, using the real shared auditor."""
    def __init__(self, work, evidence, root, prompt, actions=(), response='{}'):
        self.work, self.evidence, self.root = work, evidence, root
        evidence.mkdir()
        overlay = {'retry': {'enabled': False, 'modelFallback': False}, 'providers': {'cacheWarming': 'off'}, 'tools': {'approval': {'course_read': 'allow'}}}
        (evidence / 'runtime-config.yml').write_bytes(runtime.json_bytes(overlay))
        rule = work / 'shared/controls/SAVED_INSTRUCTION.md'
        self.policy = dict.fromkeys(runtime.POLICY_KEYS)
        self.policy.update(schema_version=1, run_id='synthetic-module02', work_root=str(root), profile='read', tools=['course_read'], write_files=[], write_root=None, provider=runtime.PROVIDER, model=runtime.MODEL, omp_version=SYNTH_OMP_VERSION, prompt_sha256=runtime.file_hash(prompt), instruction={'path': str(rule), 'sha256': runtime.file_hash(rule)}, declaration=None, python=sys.executable, guard_source_sha256=runtime.file_hash(runtime.GUARD), runtime_config_sha256=runtime.file_hash(evidence / 'runtime-config.yml'), guard_log=str(evidence / 'guard.jsonl'), watch_paths=[])
        self.policy['thinking'] = 'low'
        self.snapshots = {'before': runtime.snapshot(root, []), 'after': runtime.snapshot(root, [])}
        common = dict(run_id=self.policy['run_id'])
        self.guard = [dict(type='guard_ready', provider=runtime.PROVIDER, model=runtime.MODEL, active_tools=['course_read'], **common), dict(type='instruction_loaded', file_sha256=runtime.file_hash(rule), loaded_text_sha256=runtime.sha256(rule.read_bytes().decode().strip().encode()), **common), dict(type='provider_request', provider=runtime.PROVIDER, model=runtime.MODEL, **common)]
        self.events = [{'type': 'agent_start'}]
        for i, (kind, relative) in enumerate(actions):
            target = (root / relative).resolve()
            identifier = f'call-{i}'
            args = {'path': relative}
            pre_hook = kind in {'unknown-read', 'unknown-write', 'unknown-bash'}
            tool = {'unknown-read': 'read', 'unknown-write': 'course_write', 'unknown-bash': 'bash'}.get(kind, 'course_read')
            if kind == 'unknown-write':
                args['content'] = 'Attempted write that must never reach disk.'
            elif kind == 'unknown-bash':
                args = {'command': f'cat {relative}'}
            error = pre_hook or kind in {'deny', 'absent'}
            content = [{'type': 'text', 'text': f'Tool {tool} not found' if pre_hook else 'HOLD: synthetic denial' if kind == 'deny' else 'ENOENT: synthetic absent path' if kind == 'absent' else '\n'.join(p.name for p in target.iterdir()) if target.is_dir() else target.read_text()}]
            call = dict(type='toolCall', id=identifier, name=tool, arguments=args)
            assistant = dict(role='assistant', provider=runtime.PROVIDER, model=runtime.MODEL, stopReason='toolUse', content=[call])
            self.events.extend([dict(type='message_end', message=assistant), dict(type='tool_execution_start', toolCallId=identifier, toolName=tool, args=args), dict(type='tool_execution_end', toolCallId=identifier, toolName=tool, result={'content': content}, isError=error), dict(type='message_end', message=dict(role='toolResult', toolCallId=identifier, toolName=tool, content=content, isError=error))])
            if pre_hook:
                continue
            decision = dict(type='decision', call_id=identifier, tool='course_read', arguments=args, allow=kind != 'deny', resolved_path=None if kind == 'deny' else str(target), **common)
            self.guard.append(decision)
            if kind != 'deny':
                self.guard.append(dict(decision, type='execution_check'))
            if not error:
                self.guard.append(dict(type='executed', call_id=identifier, tool='course_read', resolved_path=str(target), output_sha256=None, **common))
        self.response = response
        final = dict(role='assistant', provider=runtime.PROVIDER, model=runtime.MODEL, stopReason='stop', content=[dict(type='text', text=response)])
        self.events += [dict(type='message_end', message=final), dict(type='agent_end', isTerminal=True, messages=[final])]
        self.guard.append(dict(type='guard_end', ready=True, failed=False, provider_requests=1, **common))
        self.seal()

    def seal(self):
        e, p = self.evidence, self.policy
        (e / 'policy.json').write_bytes(runtime.json_bytes(p))
        for row in self.guard:
            if row['type'] in {'guard_ready', 'guard_end', 'instruction_loaded'}:
                row['policy_sha256'] = runtime.file_hash(e / 'policy.json')
        for name in ['events', 'guard']:
            (e / (name + '.jsonl')).write_text(''.join(json.dumps(row) + '\n' for row in getattr(self, name)))
        (e / 'snapshots.json').write_bytes(runtime.json_bytes(self.snapshots))
        (e / 'response.md').write_text(self.response)
        result = dict(run_id=p['run_id'], provider=runtime.PROVIDER, model=runtime.MODEL, omp_version=SYNTH_OMP_VERSION, exit_code=0, policy_sha256=runtime.file_hash(e / 'policy.json'), guard_sha256=runtime.file_hash(e / 'guard.jsonl'), declared_policy_sha256=None, instruction_sha256=p['instruction']['sha256'] if p['instruction'] else None, input_sha256={k: v['sha256'] for k, v in self.snapshots['before']['work'].items() if v['type'] == 'file'}, output_sha256={}, status='PASS', reason='Explicitly synthetic sealed receipt; no provider contact.')
        (e / 'result.json').write_bytes(runtime.json_bytes(result))


def guard_group(work, base):
    for name, code in [('DN-003', 0), ('DN-014', 1), ('DN-015', 1), ('DN-016', 1), ('DN-999', 1)]:
        result = subprocess.run([sys.executable, str(MODULE / 'shared/case/guard.py'), str(work / 'shared/case' / (name + '.md'))], capture_output=True, text=True)
        assert result.returncode == code, f'file screen {name}'


def source_group(work, base):
    p = proposal(work)
    brain.support(work, 'DN-003', p['sources'][0]['excerpt'])
    holds(lambda: brain.support(work, 'DN-014', p['sources'][0]['excerpt']))
    holds(lambda: brain.support(work, 'DN-003', 'invented evidence'))
    for treatment in ('use', 'qualify', 'unresolved', 'exclude'):
        invalid = judgments(work)
        invalid['claims'][0].update(treatment=treatment, limits=' ')
        holds(lambda: brain.validate_judgments(work, invalid))
    cmap = brain.validate_judgments(work, judgments(work))
    traced = judgments(work)
    traced['claims'][1]['sources'][0]['excerpt'] = brain.text(work / 'vault/Sources/DN-003.md').strip().splitlines()[-1]
    trace_claims = brain.validate_judgments(work, traced)
    citation = dict(note_id='KB-001', **traced['claims'][0]['sources'][0])
    answer = {'answers': [dict(question_id='Q1', status='supported', answer='Paper receipt is recorded.', citations=[citation])]}
    build = {'notes': [dict(note_id='KB-001', claim_ids=['JG-001', 'JG-002', 'JG-003'])]}
    rendered = brain.render_answers_text('v1', answer, trace_claims, build)
    assert 'Reviews/v1-judgments.md#JG-001|' in rendered
    assert 'Reviews/v1-judgments.md#JG-002|' not in rendered, 'citation links an unrelated excerpt from the same source'
    assert 'Reviews/v1-judgments.md#JG-003|' not in rendered, 'citation links an uncited unresolved claim'
    for title in ('Permit [unapproved]', 'Permit|status', 'Permit\nstatus'):
        invalid_build = {'notes': [dict(note_id='KB-001', title=title, claim_ids=[cid for cid, claim in cmap.items() if claim['treatment'] != 'exclude'], related=[])]}
        holds(lambda: brain.validate_build(invalid_build, cmap))
    rule = work / 'shared/controls/SAVED_INSTRUCTION.md'
    original_rule = rule.read_bytes()
    rule.write_bytes(original_rule + b'\nChanged rule.\n')
    try:
        holds(lambda: brain.do_run(work, 'changed-rule', MODULE / 'tests/synthetic_runner.py', base / 'changed-rule-evidence'))
        assert not (base / 'changed-rule-evidence').exists()
    finally:
        rule.write_bytes(original_rule)
    source = work / 'vault/Sources/DN-001.md'
    source.write_text(source.read_text() + '\nChanged\n')
    missing = work / 'vault/Sources/DN-002.md'
    missing.unlink()
    extra = work / 'vault/Sources/Untitled.md'
    extra.touch()
    extra_dir = work / 'vault/Sources/extra'
    extra_dir.mkdir()
    error = holds(lambda: brain.source_identity(work))
    assert all(str(path) in error for path in [source, missing, extra, extra_dir]), error
    for defect in ['missing', 'duplicate']:
        target = base / defect
        shutil.copytree(work / 'shared', target / 'shared')
        if defect == 'missing':
            (target / 'shared/case/DN-040.md').unlink()
        else:
            (target / 'shared/case/nested').mkdir()
            shutil.copyfile(target / 'shared/case/DN-001.md', target / 'shared/case/nested/DN-001.md')
        error = holds(lambda: brain.initialize(target))
        expected = target / ('shared/case/DN-040.md' if defect == 'missing' else 'shared/case/nested/DN-001.md')
        assert str(expected) in error, error


def freeze_group(work, base):
    # real pipeline: do_run with synthetic sealed runner (no direct freeze, no hand-authored flat KB/MOC)
    runner = MODULE / 'tests/synthetic_runner.py'
    ev = base / 'ev-freeze'
    code = brain.do_run(work, 'v1', runner, ev)
    assert code == 0
    manifest = brain.check(work, 'v1')
    # Re-sealing local hashes must not substitute records for audited AI responses.
    manifest_path = work / 'identities/v1.json'
    manifest_bytes = manifest_path.read_bytes()
    for name in ('build', 'answers'):
        record = work / 'runs/v1' / f'{name}.json'
        original_record = record.read_bytes()
        changed = json.loads(original_record)
        if name == 'build':
            changed['notes'].reverse()
        else:
            changed['answers'][0]['answer'] = 'Invented authority not present in the audited answer.'
        record.write_bytes(brain.canonical(changed) + b'\n')
        forged_manifest = copy.deepcopy(manifest)
        forged_manifest[f'{name}_sha256'] = brain.digest(record.read_bytes())
        forged_manifest['run_files'] = brain.inventory(work / 'runs/v1')
        manifest_path.write_bytes(brain.canonical(forged_manifest) + b'\n')
        try:
            holds(lambda: brain.check(work, 'v1'))
        finally:
            record.write_bytes(original_record)
            manifest_path.write_bytes(manifest_bytes)
    assert 'prompt_shas' in manifest
    assert 'phases' in manifest
    ph = manifest['phases'].get('judge', {})
    assert 'receipts' in ph  # receipts inventory, not removed result_sha256
    jreads = ph.get('reads', [])
    assert len(jreads) == 40 and all(f'DN-{i:03}.md' in jreads for i in range(1, 41))  # exact 40 source IDs
    files = {f.get('path','') for f in manifest.get('files', [])}
    assert any('MOC' in p for p in files)
    assert any('KB-001' in p for p in files)
    # cold now under Knowledge/<rev>/
    path = work / 'cold/v1/Knowledge/v1/KB-001.md'
    saved = path.read_bytes()
    path.write_bytes(saved + b'changed')
    holds(lambda: brain.check(work, 'v1'))
    path.write_bytes(saved)
    path.unlink()
    holds(lambda: brain.check(work, 'v1'))
    path.write_bytes(saved)
    extra = work / 'cold/v1/Knowledge/v1/KB-999.md'  # truly extra KB999, not existing unresolved KB002
    extra.write_bytes(saved)
    holds(lambda: brain.check(work, 'v1'))
    extra.unlink()
    hidden = work / 'cold/v1/.obsidian'
    hidden.mkdir()
    secret = hidden / 'secret'
    secret.write_text('must not enter cold content')
    empty_dir = work / 'cold/v1/extra-empty'
    empty_dir.mkdir()
    error = holds(lambda: brain.check(work, 'v1'))
    assert all(str(p) in error for p in [hidden, secret, empty_dir]), error
    secret.unlink()
    hidden.rmdir()
    empty_dir.rmdir()
    brain.check(work, 'v1')


def revision_group(work, base):
    # real pipeline v1 then correction v2 using feedback + focus; Feedback frozen in runs/; v1 bytes immutable; focal substantive change required
    runner = MODULE / 'tests/synthetic_runner.py'
    ev1 = base / 'ev-rev1'
    assert brain.do_run(work, 'v1', runner, ev1) == 0
    original = {p.relative_to(work).as_posix(): p.read_bytes() for p in (work / 'cold/v1').rglob('*') if p.is_file()}
    fb_path = work / 'vault/Feedback.md'
    fb_path.write_text('Cite DN-003 and qualify the limit on authority. Expect focal KB-001 change.')
    empty_feedback = work / 'vault/Feedback-empty.md'
    empty_feedback.write_text(' \n')
    for revision, focal, feedback in [('bad-focus', 'KB-999', fb_path), ('empty-feedback', 'KB-001', empty_feedback)]:
        ev_bad = base / revision
        holds(lambda: brain.do_run(work, revision, runner, ev_bad, prev='v1', foc=focal, fb_path=feedback))
        assert not ev_bad.exists()
        assert not (work / 'runs' / revision).exists()
    ev2 = base / 'ev-rev2'
    code = brain.do_run(work, 'v2', runner, ev2, prev='v1', foc='KB-001', fb_path=fb_path)
    assert code == 0
    # immutable prior
    assert all((work / p).read_bytes() == value for p, value in original.items())
    man2 = brain.load(work / 'identities/v2.json')
    assert man2.get('focus_note') == 'KB-001'
    assert (work / 'runs/v2/feedback.md').is_file()
    assert 'qualify the limit' in (work / 'runs/v2/feedback.md').read_text()
    k2 = work / 'cold/v2/Knowledge/v2/KB-001.md'
    assert k2.is_file()
    # consumer-visible: check(v1) and check(v2) after new MOC; modify current Feedback; re-check(v1) (immutability independent of live fb/MOC)
    brain.check(work, 'v1')
    brain.check(work, 'v2')
    fb_path.write_text('Cite DN-003 and qualify the limit on authority. Expect focal KB-001 change.\nMODIFIED AFTER V2')
    brain.check(work, 'v1')
    # cosmetic variant: use fb with marker so synthetic produces no semantic change (title only, which signature ignores)
    fb_cos = work / 'vault/Feedback-cos.md'
    fb_cos.write_text('cosmetic only change with no effect on claims or limits.')
    holds(lambda: brain.do_run(work, 'v2-cos', runner, base/'ev-cos', prev='v1', foc='KB-001', fb_path=fb_cos))


def preserve_group(work, base):
    # Missing rule is CLI exit 2 before any evidence or provider contact.
    runner = MODULE / 'tests/synthetic_runner.py'
    rule = work / 'shared/controls/SAVED_INSTRUCTION.md'
    saved_rule = rule.read_bytes()
    rule.unlink()
    ev = base / 'missing-rule'
    code = brain.main(['run', '--work', str(work), '--revision', 'no-rule', '--runner', str(runner), '--evidence', str(ev)])
    assert code == 2
    assert not ev.exists()
    assert brain.main(['retrieve', '--work', str(work), '--revision', 'no-rule', '--runner', str(runner), '--evidence', str(ev)]) == 2
    assert not ev.exists()
    # restore for other tests
    rule.write_bytes(saved_rule)
    for revision, options in [('orphan-focus', {'foc': 'KB-001'}), ('orphan-feedback', {'fb_path': work / 'vault/Feedback.md'})]:
        ev_bad = base / revision
        holds(lambda: brain.do_run(work, revision, runner, ev_bad, **options))
        assert not ev_bad.exists()
        assert not (work / 'runs' / revision).exists()
    # no overwrite of run dir
    ev1 = base / 'ev-pres1'
    assert brain.do_run(work, 'v-pres', runner, ev1) == 0
    holds(lambda: brain.do_run(work, 'v-pres', runner, base / 'ev-pres2'))
    # technical stop without later model calls (fault runner produces early non0; no build evidence dir)
    for mode in ['created', 'exception']:
        other = base / mode
        other.mkdir(parents=True, exist_ok=True)
        w = prepare(other)
        rfile = other / 'fault_runner.py'
        evf = other / 'ev-fault'
        if mode == 'created':
            rfile.write_text('from pathlib import Path\ndef main(argv):\n    ev = Path(argv[argv.index("--evidence")+1])\n    ev.mkdir(parents=True, exist_ok=True)\n    return 2\n')
            c = brain.do_run(w, 'fault', rfile, evf)
            assert c != 0
        else:
            rfile.write_text('def main(argv):\n    raise RuntimeError("injected stop before any stage complete")\n')
            # via CLI so RuntimeError becomes consumer HOLD (nonzero return), not uncaught raise in test
            res = subprocess.run([sys.executable, str(MODULE / 'scripts/second_brain.py'), 'run', '--work', str(w), '--revision', 'fault', '--runner', str(rfile), '--evidence', str(evf)], capture_output=True, text=True)
            assert res.returncode == 1, res.stdout + res.stderr
            assert 'HOLD: injected stop before any stage complete' in res.stderr
        # no build stage evidence created
        assert not (evf / 'build').exists() if evf.exists() else True
        assert not (w / 'runs/fault/build.json').exists() if (w / 'runs/fault').exists() else True
    # CLI subprocess with stdin DEVNULL (authored path) -- must reach success for this smoke
    cli_ev = base / 'cli-ev'
    cli_work = prepare(base / 'cli-work-prep')
    res = subprocess.run([sys.executable, str(MODULE / 'scripts/second_brain.py'), 'run', '--work', str(cli_work), '--revision', 'vcli', '--runner', str(MODULE / 'tests/synthetic_runner.py'), '--evidence', str(cli_ev)], stdin=subprocess.DEVNULL, capture_output=True, text=True)
    assert res.returncode == 0, res.stdout + res.stderr
    # inspect three invoked stages evidence + reads
    assert (cli_ev / 'judge' / 'result.json').is_file()
    assert (cli_ev / 'build' / 'result.json').is_file()
    assert (cli_ev / 'retrieve' / 'result.json').is_file()
    # use real check for reads on one
    jreads = brain.check_actual_reads(cli_ev / 'judge', cli_work / 'runs/vcli/inputs/judge', 'judge')
    assert len(jreads) >= 40
    # atomic publish guard (still exposed)
    src, dst = base / 'publish-src', base / 'publish-dst'
    src.mkdir()
    dst.mkdir()
    holds(lambda: brain.publish_directory(src, dst))
    assert src.is_dir() and dst.is_dir()


def receipt_group(work, base):
    runner = MODULE / 'tests/synthetic_runner.py'
    ev = base / 'ev-receipt'
    assert brain.do_run(work, 'v1', runner, ev) == 0
    manifest = brain.check(work, 'v1')
    jprompt = work / 'shared/controls/JUDGE_PROMPT.md'
    jreads_list = [('read', f'DN-{i:03}.md') for i in range(1, 41)]
    good = Sealed(work, base / 'judge', work / 'vault/Sources', jprompt, jreads_list, json.dumps(judgments(work)))
    assert runtime.audit_evidence(good.evidence) == []
    jreads = brain.check_actual_reads(good.evidence, work / 'vault/Sources', 'judge')
    assert jreads == {f'DN-{i:03}.md' for i in range(1, 41)}
    short = Sealed(work, base / 'short', work / 'vault/Sources', jprompt, jreads_list[:-1] + [jreads_list[0]], json.dumps(judgments(work)))
    assert runtime.audit_evidence(short.evidence) == []
    holds(lambda: brain.check_actual_reads(short.evidence, work / 'vault/Sources', 'judge'))
    origp = copy.deepcopy(good.policy)
    for k, v in [('instruction', None), ('work_root', str(base)), ('prompt_sha256', '0'*64), ('profile', 'declared')]:
        good.policy = dict(origp, **{k: v})
        good.seal()
        holds(lambda: brain.verify_phase(work, REPO / 'shared/run_omp.py', 'judge', jprompt, work / 'vault/Sources', good.evidence, brain.inventory(work / 'vault/Sources'), sorted(jreads)))
    good.policy = origp
    good.seal()
    response = cold_answers(work)
    rprompt = work / 'shared/controls/RETRIEVE_PROMPT.md'
    cold = Sealed(work, base / 'cold', work / 'cold/v1', rprompt, [('read', 'MOC.md'), ('read', 'Knowledge/v1/KB-001.md'), ('absent', 'Sources/DN-014.md'), ('deny', '../../forbidden')], json.dumps(response))
    assert runtime.audit_evidence(cold.evidence) == []
    rreads = brain.check_actual_reads(cold.evidence, work / 'cold/v1', 'retrieve')
    assert 'MOC.md' in str(rreads)
    g = [json.loads(l) for l in (cold.evidence / 'guard.jsonl').read_text().splitlines() if l.strip()]
    e = [json.loads(l) for l in (cold.evidence / 'events.jsonl').read_text().splitlines() if l.strip()]
    sts = [st for _c,_d,_e,st in brain.attempted_calls(g, e)]
    assert 'EXECUTED' in sts and 'DENIED' in sts
    ob = [st for _c,_d,_e,st in brain.attempted_calls(g, e) if st in ('DENIED','ALLOWED_ABSENT','EXECUTED','NOT_ATTEMPTED')]
    assert 'ALLOWED_ABSENT' in ob or 'DENIED' in ob
    rejected = Sealed(work, base / 'pre-hook', work / 'cold/v1', rprompt, [('read', 'MOC.md'), ('read', 'Knowledge/v1/KB-001.md'), ('unknown-read', '../../vault/Sources/DN-014.md'), ('unknown-write', 'attempted-output.md')], json.dumps(response))
    assert runtime.audit_evidence(rejected.evidence) == []
    calls = list(brain.attempted_calls([json.loads(l) for l in (rejected.evidence / 'guard.jsonl').read_text().splitlines() if l.strip()], [json.loads(l) for l in (rejected.evidence / 'events.jsonl').read_text().splitlines() if l.strip()]))
    assert {(call['name'], state) for call, _, _, state in calls if call['name'] != 'course_read'} == {('read', 'DENIED'), ('course_write', 'DENIED')}
    assert not (work / 'cold/v1/attempted-output.md').exists()
    for lbl, acts, exp in [('raw-denied', [('deny', '../../vault/Sources/DN-014.md')], ['DENIED']), ('raw-exec', [('read', 'DN-014.md')], ['EXECUTED'])]:
        rt = work / 'vault/Sources' if 'exec' in lbl else work / 'cold/v1'
        ob = Sealed(work, base / lbl, rt, rprompt, acts)
        gg = [json.loads(l) for l in (ob.evidence / 'guard.jsonl').read_text().splitlines() if l.strip()]
        ee = [json.loads(l) for l in (ob.evidence / 'events.jsonl').read_text().splitlines() if l.strip()]
        o = [st for _c,_d,_e,st in brain.attempted_calls(gg, ee) if st in ('DENIED','ALLOWED_ABSENT','EXECUTED','NOT_ATTEMPTED')]
        assert o == exp
    assert runtime.audit_evidence(cold.evidence) == []
    original_cold_policy = copy.deepcopy(cold.policy)
    cold.policy = dict(original_cold_policy, prompt_sha256='0'*64)
    cold.seal()
    holds(lambda: brain.verify_phase(work, REPO / 'shared/run_omp.py', 'retrieve', rprompt, work / 'cold/v1', cold.evidence, brain.inventory(work / 'cold/v1'), ['MOC.md']))
    cold.policy = original_cold_policy
    cold.seal()
    for nm, acts in [('no-moc', [('read', 'Knowledge/v1/KB-001.md')]), ('none', [])]:
        att = Sealed(work, base / nm, work / 'cold/v1', rprompt, acts)
        assert runtime.audit_evidence(att.evidence) == []
        holds(lambda: brain.check_actual_reads(att.evidence, work / 'cold/v1', 'retrieve'))
    (cold.evidence / 'response.md').write_text('sub')
    assert runtime.audit_evidence(cold.evidence)


def payload_binding_regression(work, base):
    """Regression boundary (payload): select call by assistant toolCall arguments.path == 'DN-003.md'; tamper BOTH execution_end and toolResult copies (audit stays clean as copies match); check_actual_reads must HOLD (binds to packet bytes). Genuine shared, no mock."""
    runner = MODULE / 'tests/synthetic_runner.py'
    ev = base / 'ev-payload'
    assert brain.do_run(work, 'v-payload', runner, ev) == 0
    evj = ev / 'judge'
    e = [json.loads(l) for l in (evj / 'events.jsonl').read_text().splitlines() if l.strip()]
    # select call ID from assistant arguments path
    call_id = None
    for row in e:
        if row.get('type') == 'message_end':
            msg = row.get('message', {})
            if msg.get('role') == 'assistant':
                for block in msg.get('content', []):
                    if block.get('type') == 'toolCall':
                        args = block.get('arguments', {}) or {}
                        if args.get('path') == 'DN-003.md' or 'DN-003' in str(args.get('path', '')):
                            call_id = block.get('id')
                            break
                if call_id:
                    break
    if call_id:
        wrong = 'TAMPERED PAYLOAD NOT THE FROZEN PACKET BYTES'
        for row in e:
            if row.get('type') == 'tool_execution_end' and row.get('toolCallId') == call_id:
                if 'result' in row and row['result'].get('content'):
                    row['result']['content'][0]['text'] = wrong
            if row.get('type') == 'message_end':
                m = row.get('message', {})
                if m.get('role') == 'toolResult' and m.get('toolCallId') == call_id:
                    for c in m.get('content', []):
                        if isinstance(c, dict):
                            c['text'] = wrong
    (evj / 'events.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in e))
    errs = runtime.audit_evidence(evj)
    assert not errs, 'shared audit must remain clean (copies still match)'
    # module check binds payload to actual packet content -> HOLD
    packet = work / 'runs' / 'v-payload' / 'inputs' / 'judge'
    holds(lambda: brain.check_actual_reads(evj, packet, 'judge'))


def publication_projection_regression(work, base):
    """Regression boundary: check must HOLD on tamper or deletion of learner-visible published vault projection (Knowledge/Reviews); restore then PASS. Cold snapshot remains authoritative for prior revision. Genuine shared audit + CLI contract."""
    runner = MODULE / 'tests/synthetic_runner.py'
    ev = base / 'ev-pub'
    assert brain.do_run(work, 'v-pub', runner, ev) == 0
    brain.check(work, 'v-pub')
    cold_kb = work / 'cold/v-pub/Knowledge/v-pub/KB-001.md'
    vault_kb = work / 'vault/Knowledge/v-pub/KB-001.md'
    orig_vault = vault_kb.read_bytes() if vault_kb.is_file() else b''
    orig_cold = cold_kb.read_bytes() if cold_kb.is_file() else b''
    # tamper public published file
    if vault_kb.is_file():
        vault_kb.write_text('TAMPERED PUBLICATION\n')
        holds(lambda: brain.check(work, 'v-pub'))
        vault_kb.write_bytes(orig_vault)
        brain.check(work, 'v-pub')
    # deletion of public
    if vault_kb.is_file():
        saved = vault_kb.read_bytes()
        vault_kb.unlink()
        holds(lambda: brain.check(work, 'v-pub'))
        vault_kb.write_bytes(saved)
        brain.check(work, 'v-pub')
    # prepend false text to Reviews (consumer-visible projection; catch .endsWith bugs in addition to replace/delete)
    rev = 'v-pub'
    for rbase in [f'{rev}-judgments.md', f'{rev}-answers.md']:
        rp = work / 'vault/Reviews' / rbase
        if rp.is_file():
            orig_r = rp.read_bytes()
            rp.write_bytes(b'FALSE PREPENDED TEXT FOR REGRESSION\n' + orig_r)
            holds(lambda: brain.check(work, 'v-pub'))
            rp.write_bytes(orig_r)
            brain.check(work, 'v-pub')
    # confirm cold was never affected
    assert cold_kb.read_bytes() == orig_cold
    # other module launcher isolation
    assert 'module-02-context-desk' not in str(runtime.__file__).replace('\\','/').lower() or 'shared' in str(runtime.__file__)


GROUPS = {'M2-GUARD': guard_group, 'M2-SOURCE': source_group, 'M2-FREEZE': freeze_group, 'M2-REVISION': revision_group, 'M2-PRESERVE': preserve_group, 'M2-RECEIPT': receipt_group}


def main():
    failed = 0
    for cid, action in GROUPS.items():
        with tempfile.TemporaryDirectory(prefix='module02-oracle-') as directory:
            base = Path(directory).resolve()
            try:
                work = prepare(base)
            except Exception as error:
                print(f'ERROR {cid}: setup failed: {error!r}')
                return 2
            try:
                action(work, base)
                print(f'  PASS {cid}: behavioral boundaries')
            except AssertionError as error:
                failed += 1
                print(f'  FAIL {cid}: {error}')
            except Exception as error:
                print(f'ERROR {cid}: unexpected exception: {error!r}')
                return 2
    # run regression boundaries in dedicated work (use same pattern)
    with tempfile.TemporaryDirectory(prefix='module02-regress-') as directory:
        base = Path(directory).resolve()
        try:
            work = prepare(base)
            payload_binding_regression(work, base)
            print('  PASS regression-payload-binding: read content bound in genuine shared audit')
            publication_projection_regression(work, base)
            print('  PASS regression-publication-projection: published vault tamper/deletion causes HOLD')
        except AssertionError as error:
            failed += 1
            print(f'  FAIL M2-REGRESS: {error}')
        except Exception as error:
            print(f'ERROR M2-REGRESS: {error!r}')
            return 2
    print(f'FAIL: {failed} behavioral groups' if failed else 'PASS: all Module 2 behavioral groups and regressions')
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
