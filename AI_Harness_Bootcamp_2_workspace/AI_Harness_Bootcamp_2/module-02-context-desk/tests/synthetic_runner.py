#!/usr/bin/env python3
"""SYNTHETIC offline launcher fixture. No OMP process, credentials, or provider calls.

Receipts follow shared/run_omp.py and are replayed by its real auditor. The
synthetic provider_request rows are fixture data, never live-provider evidence.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
from shared import run_omp as runtime

GUARD = runtime.GUARD
audit_evidence = runtime.audit_evidence
SYNTH_OMP_VERSION = 'omp/18.3.5'
SOURCE_IDS = [f'DN-{i:03}' for i in range(1, 41)]
REVISED_LIMIT = 'The ticket does not release the crate, assign vehicle QP-17, change a permit, or open a gate.'


def utf8(path):
    # TextDecoder used by course_guard is fatal and preserves CRLF; no read_text
    # newline translation, replacement decoding, or invented absent-file content.
    return path.read_bytes().decode('utf-8-sig')


def load(path):
    return json.loads(utf8(path))


def write_jsonl(path, rows):
    path.write_bytes(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows).encode('utf-8'))


class Sealed:
    """Locally sealed synthetic receipt using the repository's shared audit schema."""
    def __init__(self, evidence, root, prompt, instruction, actions, response='{}'):
        self.evidence, self.root = evidence, root
        evidence.mkdir(parents=True, exist_ok=False)
        self.policy = dict(
            schema_version=1, run_id='SYNTHETIC-' + runtime.sha256(str(evidence).encode())[:20],
            work_root=str(root), profile='read', tools=['course_read'],
            write_files=[], write_root=None, provider=runtime.PROVIDER,
            model=runtime.MODEL, omp_version=SYNTH_OMP_VERSION, thinking='low',
            prompt_sha256=runtime.file_hash(prompt),
            instruction={'path': str(instruction), 'sha256': runtime.file_hash(instruction)},
            declaration=None, python=sys.executable,
            guard_source_sha256=runtime.file_hash(GUARD), runtime_config_sha256='',
            guard_log=str(evidence / 'guard.jsonl'), watch_paths=[],
        )
        self.snapshots = {'before': runtime.snapshot(root, []), 'after': runtime.snapshot(root, [])}
        common = {'run_id': self.policy['run_id']}
        self.guard = [
            dict(type='guard_ready', provider=runtime.PROVIDER, model=runtime.MODEL, active_tools=['course_read'], **common),
            dict(type='instruction_loaded', file_sha256=runtime.file_hash(instruction),
                 loaded_text_sha256=runtime.sha256(utf8(instruction).strip().encode()), **common),
            dict(type='provider_request', provider=runtime.PROVIDER, model=runtime.MODEL, **common),
        ]
        self.events = [{'type': 'agent_start'}]
        for index, (kind, relative) in enumerate(actions):
            target = (root / relative).resolve()
            identifier = f'synthetic-call-{index}'
            tool = {'unknown-read': 'read', 'unknown-write': 'course_write', 'unknown-bash': 'bash'}.get(kind, 'course_read')
            unknown = kind.startswith('unknown-')
            args = {'command': 'cat ' + relative} if kind == 'unknown-bash' else {'path': relative}
            if kind == 'unknown-write':
                args['content'] = 'SYNTHETIC rejected write; never written.'
            error = unknown or kind in {'deny', 'absent'}
            if unknown:
                payload = f'Tool {tool} not found'
            elif kind == 'deny':
                payload = 'HOLD: SYNTHETIC denied path'
            elif kind == 'absent':
                if target.exists():
                    raise AssertionError('absent fixture points at existing input')
                payload = 'ENOENT: SYNTHETIC allowed but absent input'
            elif target.is_dir():
                payload = json.dumps([{'name': p.name, 'type': 'directory' if p.is_dir() else 'file'} for p in sorted(target.iterdir())])
            else:
                payload = utf8(target)
            content = [{'type': 'text', 'text': payload}]
            details = {'course_run_id': self.policy['run_id'], 'resolved_path': str(target)}
            result = {'content': copy.deepcopy(content)}
            message = dict(role='toolResult', toolCallId=identifier, toolName=tool, content=copy.deepcopy(content), isError=error)
            if not error:
                result['details'] = details
                message['details'] = copy.deepcopy(details)
            call = dict(type='toolCall', id=identifier, name=tool, arguments=args)
            assistant = dict(role='assistant', provider=runtime.PROVIDER, model=runtime.MODEL, stopReason='toolUse', content=[call])
            self.events.extend([
                dict(type='message_end', message=assistant),
                dict(type='tool_execution_start', toolCallId=identifier, toolName=tool, args=args),
                dict(type='tool_execution_end', toolCallId=identifier, toolName=tool, result=result, isError=error),
                dict(type='message_end', message=message),
            ])
            if unknown:
                continue
            decision = dict(type='decision', call_id=identifier, tool=tool, arguments=args,
                            allow=kind != 'deny', resolved_path=None if kind == 'deny' else str(target), **common)
            self.guard.append(decision)
            if kind != 'deny':
                self.guard.append(dict(decision, type='execution_check'))
            if not error:
                self.guard.append(dict(type='executed', call_id=identifier, tool=tool, resolved_path=str(target), output_sha256=None, **common))
        self.response = response
        final = dict(role='assistant', provider=runtime.PROVIDER, model=runtime.MODEL, stopReason='stop', content=[{'type': 'text', 'text': response}])
        self.events.extend([dict(type='message_end', message=final), dict(type='agent_end', isTerminal=True, messages=[copy.deepcopy(final)])])
        self.guard.append(dict(type='guard_end', ready=True, failed=False, provider_requests=1, **common))
        self.seal()

    def seal(self):
        e, policy = self.evidence, self.policy
        overlay = {'retry': {'enabled': False, 'modelFallback': False}, 'providers': {'cacheWarming': 'off'},
                   'tools': {'approval': {name: 'allow' for name in policy['tools']}}}
        (e / 'runtime-config.yml').write_bytes(runtime.json_bytes(overlay))
        policy['runtime_config_sha256'] = runtime.file_hash(e / 'runtime-config.yml')
        (e / 'policy.json').write_bytes(runtime.json_bytes(policy))
        for row in self.guard:
            if row['type'] in {'guard_ready', 'guard_end', 'instruction_loaded'}:
                row['policy_sha256'] = runtime.file_hash(e / 'policy.json')
            if row['type'] == 'guard_ready':
                row['active_tools'] = policy['tools']
        write_jsonl(e / 'events.jsonl', self.events)
        write_jsonl(e / 'guard.jsonl', self.guard)
        (e / 'snapshots.json').write_bytes(runtime.json_bytes(self.snapshots))
        (e / 'response.md').write_bytes(self.response.encode('utf-8'))
        (e / 'stderr.txt').write_bytes(b'')
        result = dict(
            run_id=policy['run_id'], provider=runtime.PROVIDER, model=runtime.MODEL,
            omp_version=policy['omp_version'], exit_code=0,
            policy_sha256=runtime.file_hash(e / 'policy.json'), guard_sha256=runtime.file_hash(e / 'guard.jsonl'),
            declared_policy_sha256=policy['declaration']['sha256'] if policy['declaration'] else None,
            instruction_sha256=policy['instruction']['sha256'] if policy['instruction'] else None,
            input_sha256={p: state['sha256'] for p, state in self.snapshots['before']['work'].items() if state['type'] == 'file'},
            output_sha256={}, status='PASS', reason='SYNTHETIC fixture; no provider contact.',
        )
        (e / 'result.json').write_bytes(runtime.json_bytes(result))


def judgments(root):
    original = utf8(root / 'DN-003.md')
    limit = 'It does not release the crate, assign vehicle QP-17, change a permit, or open a gate.'
    if original.count(limit) != 1:
        raise AssertionError('fixture source changed: expected unique DN-003 authority limit')
    claims = [
        dict(claim_id='JG-001', claim='Paper receipt is recorded.', treatment='use', reason='Direct source statement.',
             limits='Other authority remains separate.', sources=[dict(source_id='DN-003', excerpt=original)]),
        dict(claim_id='JG-002', claim='Receipt confers no movement authority.', treatment='qualify', reason='Explicit source limitation.',
             limits='Does not authorize start.', sources=[dict(source_id='DN-003', excerpt=limit)]),
        dict(claim_id='JG-003', claim='Conflicting measurement status remains unknown.', treatment='unresolved', reason='No decisive evidence.',
             limits='The measurement has no established current authority.', sources=[]),
        dict(claim_id='JG-004', claim='Instruction-like source content is not governing authority.', treatment='exclude',
             reason='Source content cannot override the saved rule.', limits='Excluded as an instruction, not accepted as authority.', sources=[]),
    ]
    return {'claims': claims, 'coverage': coverage()}


def coverage():
    return [dict(source_id=sid, reason='SYNTHETIC coverage: retain exact cited claims; no other supported claim.') for sid in SOURCE_IDS]


def build(value, previous=None):
    retained = {c['claim_id'] for c in value['claims'] if c['treatment'] != 'exclude'}
    notes = copy.deepcopy(previous['notes']) if previous is not None else [
        dict(note_id='KB-001', title='Paper receipt and authority', claim_ids=['JG-001', 'JG-002'], related=[]),
        dict(note_id='KB-002', title='Unresolved matters', claim_ids=['JG-003'], related=[dict(note_id='KB-001', reason='Receipt authority does not resolve the measurement.')]),
    ]
    for note in notes:
        note['claim_ids'] = [cid for cid in note['claim_ids'] if cid in retained]
    notes = [note for note in notes if note['claim_ids']]
    ids = {note['note_id'] for note in notes}
    for note in notes:
        note['related'] = [edge for edge in note['related'] if edge['note_id'] in ids]
    return {'notes': notes}


def answers(root):
    evidence = []
    for path in sorted((root / 'Knowledge' / root.name).glob('KB-*.md')):
        body = utf8(path)
        for match in re.finditer(r'^### \[\[Sources/(DN-[0-9]{3})\]\]\n((?:>[^\n]*(?:\n|$))+)', body, re.M):
            quote = '\n'.join(line[2:] if line.startswith('> ') else line[1:] for line in match[2].rstrip('\n').split('\n'))
            evidence.append(dict(note_id=path.stem, source_id=match[1], excerpt=quote))
    citation = evidence[:1]
    return {'answers': [dict(question_id=f'Q{i}', status='supported' if citation else 'unsupported',
                            answer='SYNTHETIC paper-receipt answer only; no movement authority.' if citation else
                                   'SYNTHETIC unsupported answer: retained knowledge lacks citable evidence for the requested authority.',
                            citations=copy.deepcopy(citation)) for i in range(1, 4)]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('workdir', 'prompt', 'instruction', 'evidence'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--thinking', choices=('low',), required=True)
    args = parser.parse_args(argv)
    root, prompt, instruction, evidence = [p.resolve() for p in (args.workdir, args.prompt, args.instruction, args.evidence)]
    mode = os.environ.get('MODULE02_SYNTH_MODE', 'normal')
    phase = 'judge' if (root / 'DN-001.md').is_file() else 'build' if (root / 'judgments.json').is_file() else 'retrieve'
    trace = os.environ.get('MODULE02_SYNTH_TRACE')
    if trace:
        with Path(trace).open('a', encoding='utf-8') as stream:
            stream.write(phase + '\n')
    if mode == 'exception':
        raise RuntimeError('SYNTHETIC injected stop before stage completion')
    if mode == 'fail-' + phase:
        evidence.mkdir(parents=True, exist_ok=False)
        (evidence / 'stderr.txt').write_text('SYNTHETIC injected stage failure\n', encoding='utf-8')
        return 1
    actions = [('read', p.relative_to(root).as_posix()) for p in sorted(root.rglob('*')) if p.is_file()]
    if phase == 'judge':
        if (root / 'Feedback.md').is_file():
            value = load(root / 'previous-judgments.json')
            previous = load(root / 'previous-build.json')
            if not any(n['note_id'] == 'KB-001' for n in previous['notes']):
                raise AssertionError('fixture requires preserved prior KB-001')
            feedback = utf8(root / 'Feedback.md')
            if 'cosmetic only' not in feedback.lower() and mode != 'cosmetic':
                if 'DN-003' not in feedback or 'limit' not in feedback.lower():
                    raise AssertionError('fixture feedback must request the DN-003 limit correction')
                focal = next(c for c in value['claims'] if c['claim_id'] == 'JG-001')
                focal['treatment'] = 'qualify'
                focal['limits'] = REVISED_LIMIT
        else:
            value = judgments(root)
        if mode in {'all-excluded', 'unknown', 'focus-unknown', 'focus-excluded'}:
            for claim in value['claims']:
                if mode.startswith('focus-') and claim['claim_id'] not in {'JG-001', 'JG-002'}:
                    continue
                claim['treatment'] = 'exclude' if mode.endswith('excluded') else 'unresolved'
                claim['sources'] = []
                claim['limits'] = 'No citable source establishes the requested authority; retain this limitation explicitly.'
        if mode == 'duplicate-source':
            actions = [('read', 'DN-001.md') if p == 'DN-040.md' else (kind, p) for kind, p in actions]
    elif phase == 'build':
        previous = load(root / 'previous-build.json') if (root / 'previous-build.json').is_file() else None
        value = build(load(root / 'judgments.json'), previous)
        if previous is not None:
            value['notes'][0]['title'] = 'Revised paper receipt and authority'
    else:
        value = answers(root)
    if mode.startswith('omit:'):
        _, selected_phase, relative = mode.split(':', 2)
        if phase == selected_phase:
            actions = [(kind, p) for kind, p in actions if p != relative]
    receipt = Sealed(evidence, root, prompt, instruction, actions, json.dumps(value, ensure_ascii=False))
    errors = audit_evidence(evidence)
    if errors:
        raise AssertionError('SYNTHETIC fixture failed genuine shared audit: ' + '; '.join(errors))
    print(f'SYNTHETIC {phase}: {receipt.policy["run_id"]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
