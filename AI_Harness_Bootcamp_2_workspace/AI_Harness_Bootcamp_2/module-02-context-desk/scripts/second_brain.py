#!/usr/bin/env python3
"""Module 02 AI handoffs: initialize, run (judge+build+freeze+retrieve), retrieve, check.

Three fresh read-only stages via shared launcher. No human admission between passes.
Reuses safe paths, source identity, atomic publish, shared auditor/launcher.
Fails closed on structure; semantic unknowns preserved. Boring, contained.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import importlib.util
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

DN = {f'DN-{i:03}' for i in range(1, 41)}
KB = r'KB-[0-9]{3}'
SECTIONS = ['Claim', 'Limits and conflicts', 'Evidence', 'Related']


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def strict(text):
    def pairs(items):
        out = {}
        for key, value in items:
            require(key not in out, f'duplicate JSON field: {key}')
            out[key] = value
        return out
    return json.loads(text, object_pairs_hook=pairs, parse_constant=lambda x: require(False, f'invalid JSON constant {x}'))


def fields(value, keys):
    require(isinstance(value, dict) and set(value) == set(keys), f'expected fields {sorted(keys)}')


def safe(path):
    path = Path(path).expanduser().absolute()
    require('..' not in path.parts, f'parent traversal is not allowed: {path}')
    for part in [*reversed(path.parents), path]:
        require(not part.is_symlink() and not part.is_junction(), f'link/junction is not allowed: {part}')
        if part.parent.is_dir():
            name = part.name
            folded = name.casefold()
            matches = [candidate for candidate in os.listdir(part.parent) if candidate.casefold() == folded]
            require(not matches or matches == [name], f'case collision or incorrect case: {part}')
    return path.resolve()


def raw(path):
    path = safe(path)
    require(path.is_file(), f'missing regular file: {path}')
    return path.read_bytes()


def text(path):
    return raw(path).decode('utf-8').replace('\r\n', '\n')


def load(path):
    return strict(text(path))


def absent(path):
    path = safe(path)
    require(not path.exists(), f'attempt already exists: {path}')
    return path


def write_new(path, data):
    path = absent(path)
    safe(path.parent).mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data)


def save(path, value):
    write_new(path, canonical(value) + b'\n')


def publish_directory(source, destination):
    """Atomic rename with kernel-enforced refusal of an existing destination."""
    absent(destination)
    if os.name == 'nt':
        source.rename(destination)
        return
    libc = ctypes.CDLL(None, use_errno=True)
    if sys.platform == 'darwin':
        rename = libc.renamex_np
        rename.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
        args = (os.fsencode(source), os.fsencode(destination), 4)
    else:
        require(hasattr(libc, 'renameat2'), 'atomic no-replace rename is unavailable on this platform')
        rename = libc.renameat2
        rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        args = (-100, os.fsencode(source), -100, os.fsencode(destination), 1)
    rename.restype = ctypes.c_int
    if rename(*args) != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), str(destination))


def tree(root):
    root = safe(root)
    require(root.is_dir(), f'missing directory: {root}')
    for path in sorted(root.iterdir()):
        safe(path)
        yield path
        if path.is_dir():
            yield from tree(path)


def inventory(root):
    root = safe(root)
    require(root.is_dir(), f'missing directory: {root}')
    entries = []
    for path in sorted(tree(root)):
        if path.is_dir():
            continue
        data = raw(path)
        entries.append(dict(path=path.relative_to(root).as_posix(), bytes=len(data), sha256=digest(data)))
    return entries


def identity_changes(expected, actual):
    before = {item['path']: item for item in expected}
    after = {item['path']: item for item in actual}
    return [path for path in sorted(before.keys() | after.keys()) if before.get(path) != after.get(path)]


def source_identity(work, live=True):
    identity = load(work / 'source-manifest.json')
    fields(identity, {'schema_version', 'files', 'root_fingerprint', 'instruction'})
    require(isinstance(identity['files'], list), 'source files must be an array')
    for entry in identity['files']:
        fields(entry, {'path', 'bytes', 'sha256'})
        require(isinstance(entry['path'], str) and type(entry['bytes']) is int and entry['bytes'] >= 0 and isinstance(entry['sha256'], str) and re.fullmatch(r'[0-9a-f]{64}', entry['sha256']), f'{work / "source-manifest.json"}: malformed source identity entry')
    fields(identity['instruction'], {'path', 'sha256'})
    instr = identity['instruction']
    require(instr['path'] == str(work / 'shared/controls/SAVED_INSTRUCTION.md') and isinstance(instr['sha256'], str) and re.fullmatch(r'[0-9a-f]{64}', instr['sha256']), 'malformed instruction identity')
    require(type(identity['schema_version']) is int and identity['schema_version'] == 1 and identity['root_fingerprint'] == digest(canonical(identity['files'])), 'source manifest identity differs')
    paths = [f['path'] for f in identity['files']]
    expected_paths = {n + '.md' for n in DN}
    bad = (set(paths) ^ expected_paths) | {p for p in paths if paths.count(p) > 1}
    require(not bad, 'missing/extra/duplicate source identities: ' + ', '.join(sorted(bad)))
    if live:
        root = work / 'vault/Sources'
        actual = inventory(root)
        changed = identity_changes(identity['files'], actual)
        changed += [p.relative_to(root).as_posix() for p in tree(root) if p.is_dir()]
        require(paths == sorted(paths), 'source identity order differs')
        originals = []
        for item in identity['files']:
            path = work / 'shared/case' / item['path']
            try:
                require(digest(raw(path)) == item['sha256'], f'original source changed: {path}')
            except (ValueError, OSError) as exc:
                originals.append(f'{path}: {exc}')
        require(not changed, 'source identity changed: ' + ', '.join(str(root / p) for p in changed))
        require(not originals, '\n'.join(originals))
    return identity


def initialize(work):
    absent(work / 'vault')
    for name in ['source-manifest.json', 'runs', 'cold', 'identities']:
        absent(work / name)
    case = safe(work / 'shared/case')
    candidates = [p for p in tree(case) if p.name.lower().startswith('dn-')]
    expected = {case / (n + '.md') for n in DN}
    bad = (expected - set(candidates)) | {p for p in candidates if p not in expected or not p.is_file()}
    require(not bad, 'missing, duplicate, or malformed DN: ' + ', '.join(str(p) for p in sorted(bad)))
    files = []
    for p in sorted(candidates):
        data = raw(p)
        files.append(dict(path=p.name, bytes=len(data), sha256=digest(data)))
    rule = work / 'shared/controls/SAVED_INSTRUCTION.md'
    rule_bytes = raw(rule)
    require(rule_bytes.decode().strip(), 'empty saved instruction')
    vault = work / 'vault'
    vault.mkdir()
    for name in ['Sources', 'Knowledge', 'Reviews']:
        (vault / name).mkdir()
    for p in candidates:
        write_new(vault / 'Sources' / p.name, raw(p))
    write_new(vault / 'MOC.md', b'# Knowledge index\n')
    write_new(vault / 'Feedback.md', raw(work / 'shared/controls/FEEDBACK_TEMPLATE.md'))
    for name in ['runs', 'cold', 'identities']:
        (work / name).mkdir()
    save(work / 'source-manifest.json', dict(schema_version=1, files=files, root_fingerprint=digest(canonical(files)), instruction=dict(path=str(rule), sha256=digest(rule_bytes))))
def phase_prompt(base_text, phase, revision, previous=None, focus=None):
    """Pure helper-owned derivation of frozen prompt bytes for a phase.
    Injects revision/previous/focus metadata only; never leaks raw source content,
    feedback text, or prior JSON bodies into any stage (esp. cold retrieve).
    Deterministic so verifier can recompute exact frozen prompt from base control.
    """
    base = base_text.rstrip('\n')
    extra = [
        '',
        f'## Frozen stage context (revision {revision})',
        f'revision: {revision}',
    ]
    if previous:
        extra.append(f'previous: {previous}')
    if focus:
        extra.append(f'focus_note: {focus}')
    if phase == 'retrieve':
        extra.append('Cold retrieve workdir supplies only MOC.md and Knowledge/<rev>/*.md. No raw sources, no Feedback.md, no previous run files. Read required focal and cited notes.')
    elif phase == 'build':
        extra.append('This build receives validated judgments (and prior build if v2) as data files. Focal note revision uses helper metadata here.')
    extra.append('')
    return base + '\n' + '\n'.join(extra) + '\n'
def replace_latest_moc(work, rev, moc_bytes):
    """Atomic replacement of live MOC with staged bytes.
    Caller must wrap the call + manifest save in try to restore old MOC bytes on error.
    """
    moc_live = work / 'vault' / 'MOC.md'
    tmp = moc_live.parent / ('.tmp-moc-replace-' + rev)
    write_new(tmp, moc_bytes)
    os.replace(tmp, moc_live)


def decode_quote(value):
    return '\n'.join(line[2:] if line.startswith('> ') else line[1:] if line.startswith('>') else line for line in value.replace('\r\n', '\n').split('\n'))


def support(work, source, excerpt):
    require(source in DN, f'unknown source: {source}')
    require(isinstance(excerpt, str) and bool(excerpt.strip()), f'empty excerpt: {source}')
    excerpt = excerpt.replace('\r\n', '\n')
    original = text(work / 'vault/Sources' / (source + '.md'))
    starts = [m.start() for m in re.finditer('(?=' + re.escape(excerpt) + ')', original)]
    require(len(starts) == 1, f'{source}: invented or ambiguous excerpt')
    start = original[:starts[0]].count('\n') + 1
    return dict(source_id=source, locator=f'L{start}-L{start + excerpt.count(chr(10))}', excerpt=excerpt, sha256=digest(excerpt.encode()))


def parse_note(data, note_id):
    require(re.fullmatch(KB, note_id), f'unsafe note ID: {note_id}')
    value = data.decode('utf-8').replace('\r\n', '\n')
    lines = value.splitlines()
    require(lines and re.fullmatch(r'# .+', lines[0]), f'{note_id}: first line must be a title')
    require('[[' not in lines[0] and '](' not in lines[0], f'{note_id}: title cannot contain links')
    headers = list(re.finditer(r'^## (.*)$', value, re.M))
    require([m[1] for m in headers] == SECTIONS, f'{note_id}: use exactly the four ordered sections')
    require(not value[len(lines[0]):headers[0].start()].strip(), f'{note_id}: content before Claim')
    parts = {m[1]: value[m.end()+1:(headers[i+1].start() if i+1 < len(headers) else len(value))].strip('\n') for i, m in enumerate(headers)}
    require(parts['Claim'].strip() and parts['Limits and conflicts'].strip(), f'{note_id}: empty claim or limits')
    evidence, current, quote = [], None, []
    def finish():
        if current is not None:
            require(quote, f'{note_id}: missing block quote for {current}')
            evidence.append(dict(source_id=current, excerpt=decode_quote('\n'.join(quote))))
    for line in parts['Evidence'].splitlines():
        match = re.fullmatch(r'### \[\[(?:Sources/)?(DN-[0-9]{3})\]\]', line)
        if match:
            finish()
            current, quote = match[1], []
        elif line.startswith('>') and current:
            quote.append(line)
        elif not current and ('Judgment provenance' in line or ('Reviews/' in line and 'judgments' in line)):
            # allow helper-rendered real wiki link to JG heading in Evidence (note->JG->source); model markup refused upstream
            pass
        else:
            require(not line.strip(), f'{note_id}: malformed Evidence line: {line}')
    finish()
    # evidence may legitimately be [] for unresolved no-source notes (eligibility from treatment, not quotes); all-excluded empty index also valid
    related = []
    for line in parts['Related'].splitlines():
        if not line.strip():
            continue
        # support revision-qualified links [[Knowledge/<rev>/KB-xxx]]
        match = re.fullmatch(r'- \[\[Knowledge/(?:[a-z][a-z0-9-]*/)?(' + KB + r')(?:\|[^\]\n]+)?\]\]', line)
        require(match, f'{note_id}: Related must use Knowledge/KB-NNN links (rev-qualified ok)')
        related.append(match[1])
    require(not any('[[' in parts[k] or '](' in parts[k] for k in ['Claim', 'Limits and conflicts']), f'{note_id}: put links in Evidence or Related')
    require(note_id not in related and len(related) == len(set(related)), f'{note_id}: duplicate/self relationship')
    return evidence, related


def navigation(root, files):
    notes = {Path(f['path']).name.replace('.md', '') for f in files if 'Knowledge/' in f['path']}
    # empty notes allowed for honest all-excluded initial (MOC has no links)
    links = set()
    for i, line in enumerate(text(root / 'MOC.md').splitlines()):
        if not line.strip() or (i == 0 and re.fullmatch(r'# .+', line)):
            continue
        match = re.fullmatch(r'- \[\[Knowledge/(?:[a-z][a-z0-9-]*/)?(' + KB + r')(?:\|[^\]\n]+)?\]\]', line)
        require(match, 'MOC.md accepts only title and Knowledge links (rev-qualified ok)')
        links.add(match[1])
    require(links <= notes, 'MOC names missing Knowledge notes')
    # derive rev from validated manifest file paths (strict Knowledge/<rev>/ )
    rev = None
    for f in files:
        if 'Knowledge/' in f.get('path', ''):
            ps = f['path'].split('/')
            if len(ps) >= 3 and ps[0] == 'Knowledge':
                rev = ps[1]
                break
    graph = {}
    for name in notes:
        require(rev, 'cannot resolve versioned note without rev in files')
        note_p = root / 'Knowledge' / rev / (name + '.md')
        require(note_p.is_file(), f'missing note {name}')
        _, related = parse_note(raw(note_p), name)
        require(set(related) <= notes, f'{name}: missing Knowledge link')
        graph[name] = related
    reached = set(links)
    while True:
        expanded = reached | {n for p in reached for n in graph.get(p, [])}
        if expanded == reached:
            break
        reached = expanded
    require(reached == notes, 'MOC does not reach every Knowledge note')


def content_files(root):
    root = safe(root)
    rev = root.name
    require(re.fullmatch(r'[a-z][a-z0-9-]*', rev), f'cold root must be valid revision: {root}')
    files = inventory(root)
    vkb = rf'Knowledge/{re.escape(rev)}/' + KB + r'\.md'
    bad = {f['path'] for f in files if not (f['path'] == 'MOC.md' or re.fullmatch(vkb, f['path']))}
    dirs = {p.relative_to(root).as_posix() for p in tree(root) if p.is_dir()}
    ok_dirs = {'Knowledge', f'Knowledge/{rev}'}
    bad |= (dirs - ok_dirs)
    require(not bad, 'cold membership differs: ' + ', '.join(str(root / p) for p in sorted(bad)))
    return files


def revision_id(value):
    require(re.fullmatch(r'[a-z][a-z0-9-]*', value), f'unsafe revision: {value}')
    return value


def check(work, revision, seen=None):
    revision_id(revision)
    seen = set() if seen is None else seen
    require(revision not in seen, 'cyclic previous')
    seen.add(revision)
    manifest = load(work / 'identities' / (revision + '.json'))
    require(type(manifest.get('schema_version')) is int and manifest['schema_version'] == 2, 'unsupported schema (clean cutover v2)')
    require(manifest.get('revision') == revision, 'manifest revision must match arg')
    fields(manifest, {'schema_version', 'revision', 'files', 'root_fingerprint', 'source_manifest_sha256', 'instruction_sha256', 'prompt_shas', 'judgments_sha256', 'build_sha256', 'answers_sha256', 'feedback_sha256', 'previous', 'previous_manifest_sha256', 'focus_note', 'phases', 'run_files', 'public_files'})
    for entry in manifest['files']:
        fields(entry, {'path', 'bytes', 'sha256'})
        rel = entry['path']
        require(re.fullmatch(r'Knowledge/' + re.escape(revision) + r'/' + KB + r'\.md', rel) or rel == 'MOC.md', f'unsafe or wrong path {rel}')
    source = source_identity(work, live=False)
    require(manifest['source_manifest_sha256'] == digest(raw(work / 'source-manifest.json')) and manifest['instruction_sha256'] == source['instruction']['sha256'], 'source/rule identity differs')
    base_js = digest(raw(work / 'shared/controls/JUDGE_PROMPT.md'))
    base_bs = digest(raw(work / 'shared/controls/BUILD_PROMPT.md'))
    base_rs = digest(raw(work / 'shared/controls/RETRIEVE_PROMPT.md'))
    require(manifest.get('prompt_shas') == {'judge': base_js, 'build': base_bs, 'retrieve': base_rs}, 'prompt_shas base controls identity')
    rdir = work / 'runs' / revision
    require((rdir / 'answers.json').is_file() and digest(raw(rdir / 'answers.json')) == manifest.get('answers_sha256'), 'answers sha differs')
    if manifest.get('previous'):
        require((rdir / 'feedback.md').is_file(), 'v2 must record feedback')
    else:
        require(manifest.get('feedback_sha256') is None, 'initial no feedback')
    root = work / 'cold' / revision
    actual = content_files(root)
    if actual != manifest['files']:
        exp = {i['path']: i for i in manifest['files']}
        cur = {i['path']: i for i in actual}
        bad = [p for p in sorted(exp.keys() | cur.keys()) if exp.get(p) != cur.get(p)]
        raise ValueError('snapshot changed: ' + ', '.join(bad))
    computed_fp = digest(canonical(actual))
    require(computed_fp == manifest.get('root_fingerprint'), 'root_fingerprint differs from recomputed')
    navigation(root, actual)
    for entry in actual:
        rel = entry['path']
        if rel == 'MOC.md':
            continue
        pubp = work / 'vault' / rel
        require(pubp.is_file() and digest(raw(pubp)) == entry['sha256'], f'published {rel} differs from cold')
    rj = work / 'vault/Reviews' / f'{revision}-judgments.md'
    ra = work / 'vault/Reviews' / f'{revision}-answers.md'
    require(rj.is_file() and ra.is_file(), 'Reviews must be published for completed')
    require((rdir / 'judgments.json').is_file() and digest(raw(rdir / 'judgments.json')) == manifest['judgments_sha256'], 'judgments sha differs')
    require((rdir / 'build.json').is_file() and digest(raw(rdir / 'build.json')) == manifest.get('build_sha256'), 'build sha differs')
    phs = manifest.get('phases', {})
    require(set(phs.keys()) == {'judge', 'build', 'retrieve'}, 'all 3 phases required')
    for ph in ['judge', 'build', 'retrieve']:
        pm = phs.get(ph) or {}
        require(pm, f'missing {ph} phase meta')
        exact_meta_keys = ['phase', 'evidence', 'work_root', 'runner', 'prompt', 'instruction', 'inputs', 'required_reads', 'reads', 'receipts', 'omp_version']
        fields(pm, exact_meta_keys)
        rdecl = pm.get('runner') or {}
        runner_p = Path(rdecl.get('path', ''))
        require(runner_p.is_file(), f'declared runner for {ph} missing or not file')
        require(digest(raw(runner_p)) == rdecl.get('sha256'), f'runner hash for {ph}')
        evp = pm.get('evidence')
        require(evp, f'missing evidence for {ph}')
        ev = Path(evp)
        if ph == 'retrieve':
            wdir = root
        else:
            wdir = rdir / 'inputs' / ph
        prompt_path = rdir / 'prompts' / f'{ph}.md'
        require(prompt_path.is_file(), f'frozen derived prompt required at {prompt_path}')
        exp_inputs = inventory(wdir) if wdir.is_dir() else []
        if ph == 'judge':
            req = [f['path'] for f in exp_inputs if f['path'].endswith('.md')]
            for ex in ['Feedback.md', 'previous-judgments.json', 'previous-build.json']:
                if (wdir / ex).is_file(): req.append(ex)
            req = sorted(set(req))
        elif ph == 'build':
            req = ['judgments.json']
            if (wdir / 'previous-build.json').is_file(): req.append('previous-build.json')
            req = sorted(set(req))
        elif ph == 'retrieve':
            req = ['MOC.md']
            if manifest.get('focus_note'):
                req.append(f'Knowledge/{revision}/{manifest["focus_note"]}.md')
            req = sorted(set(req))
        resp_text, reads, vmeta = verify_phase(work, runner_p, ph, prompt_path, wdir, ev, exp_inputs, req)
        require(vmeta == pm, 'exact vmeta == pm')
        if ph == 'build':
            j = load(rdir / 'judgments.json')
            binp = load(wdir / 'judgments.json') if (wdir / 'judgments.json').is_file() else {}
            require(j == binp, 'causal judge to build exact')
            require(raw(rdir / 'build.json') == canonical(response_json(resp_text)) + b'\n', 'build.json differs from audited response')
        if ph == 'judge':
            for d in DN:
                p = wdir / f'{d}.md'
                require(p.is_file(), f'judge packet missing {d}')
            jv = response_json(resp_text)
            require(raw(rdir / 'judgments.json') == canonical(jv) + b'\n', 'judgments.json differs from audited response')
        if ph == 'retrieve':
            av = response_json(resp_text)
            require(raw(rdir / 'answers.json') == canonical(av) + b'\n', 'answers.json differs from audited response')
            bv = load(rdir / 'build.json')
            jv = load(rdir / 'judgments.json')
            cmap = validate_judgments(work, jv)
            rendered = render_answers_text(revision, av, cmap, bv, manifest.get('focus_note'))
            require(raw(ra) == rendered.encode('utf-8'), 'exact raw render bytes answers')
            fields(av, {'answers'})
            require(len(av['answers']) == 3, 'typed answers')
            validate_retrieve(work, revision, manifest, reads, av, manifest.get('focus_note'), cmap, bv)
            for n in bv.get('notes', []):
                nid = n['note_id']
                title = n.get('title', nid)
                cids = n.get('claim_ids', [])
                rels = n.get('related', [])
                rnote = render_knowledge_note(revision, nid, title, cids, rels, cmap)
                cnote = root / 'Knowledge' / revision / (nid + '.md')
                require(cnote.is_file() and raw(cnote) == rnote.encode('utf-8'), f'rerender KB {nid}')
        if ph == 'judge':
            jv = response_json(resp_text)
            cmap = validate_judgments(work, jv)
            cov = jv.get('coverage', [])
            rendered = render_judgments_text(revision, cmap, cov)
            require(raw(rj) == rendered.encode('utf-8'), 'exact raw render bytes judgments')
            validate_build(load(rdir / 'build.json'), cmap)
    run_inv = inventory(rdir) if rdir.is_dir() else []
    require(manifest.get('run_files') == run_inv, 'run_files exact')
    pub_actual = []
    kdir = work / 'vault' / 'Knowledge' / revision
    if kdir.is_dir():
        for p in sorted(kdir.iterdir()):
            if p.is_file() and re.fullmatch(KB + r'\.md', p.name):
                d = raw(p)
                pub_actual.append(dict(path=f'Knowledge/{revision}/{p.name}', bytes=len(d), sha256=digest(d)))
    for rbase in [f'{revision}-judgments.md', f'{revision}-answers.md']:
        rp = work / 'vault/Reviews' / rbase
        if rp.is_file():
            d = raw(rp)
            pub_actual.append(dict(path=f'Reviews/{rbase}', bytes=len(d), sha256=digest(d)))
    pub_actual.sort(key=lambda x: x['path'])
    require(manifest.get('public_files') == pub_actual, 'public_files exact sorted')
    if manifest['previous'] is not None:
        prev = revision_id(manifest['previous'])
        require(digest(raw(work / 'identities' / (prev + '.json'))) == manifest['previous_manifest_sha256'], 'prev manifest')
        check(work, prev, seen)
    else:
        require(manifest.get('previous_manifest_sha256') is None and manifest.get('focus_note') is None, 'initial no prev')
    return manifest


def response_json(value):
    value = value.strip()
    if value.startswith('```'):
        m = re.fullmatch(r'```(?:json)?\n(.*)\n```', value, re.S)
        require(m, 'response must be JSON or one outer fence')
        value = m[1]
    return strict(value)
def verify_phase(work, runner_p, phase, prompt_path, wdir, evdir, expected_inputs, required_reads):
    runner_p = safe(runner_p)
    rhash = digest(raw(runner_p))
    rt = runner_module(runner_p)
    ev = safe(evdir)
    wdir = safe(wdir)
    errs = rt.audit_evidence(ev)
    require(not errs, 'audit: ' + '; '.join(errs))
    polf = ev / 'policy.json'
    resf = ev / 'result.json'
    require(polf.is_file() and resf.is_file(), 'missing policy or result')
    pol = load(polf)
    res = load(resf)
    require(pol.get('work_root') == str(wdir), 'work_root policy mismatch')
    require(pol.get('profile') == 'read', 'read-only profile required')
    require(pol.get('thinking') == 'low', 'bounded low thinking required')
    tools = pol.get('tools', [])
    require(tools == ['course_read'], 'tools exactly course_read')
    require(pol.get('write_files', []) == [], 'no writes permitted')
    require(pol.get('write_root') is None, 'write_root None')
    require(pol.get('declaration') is None, 'declaration None')
    require('mcp' not in pol and 'judge' not in pol, 'mcp/judge disallowed')
    source = source_identity(work, live=False)
    rule = safe(work / 'shared/controls/SAVED_INSTRUCTION.md')
    instr = pol.get('instruction') or {}
    require(instr.get('path') == str(rule) and instr.get('sha256') == source['instruction']['sha256'], 'instruction identity')
    prm = safe(prompt_path)
    require(digest(raw(prm)) == pol.get('prompt_sha256'), 'prompt sha mismatch')
    actual_in = inventory(wdir)
    if expected_inputs is not None:
        require(len(identity_changes(expected_inputs, actual_in)) == 0, 'inputs changed from pre-stage inventory')
    in_sh = res.get('input_sha256', {}) or {}
    for it in (expected_inputs or actual_in):
        require(in_sh.get(it['path'], it.get('sha256')) == it.get('sha256'), 'input hash match')
    require(res.get('output_sha256', {}) == {}, 'no outputs')
    ompv = res.get('omp_version')
    require(isinstance(ompv, str) and ompv.strip() and ompv == pol.get('omp_version'), 'omp_version nonempty exact policy/result match')
    reads = check_actual_reads(ev, wdir, phase)
    req = sorted(required_reads or [])
    require(set(req) <= set(reads), f'missing required reads {set(req)-set(reads)}')
    receipts = sorted(inventory(ev), key=lambda x: x['path'])
    meta = {
        'phase': phase,
        'evidence': str(ev),
        'work_root': str(wdir),
        'runner': {'path': str(runner_p), 'sha256': rhash},
        'prompt': {'path': str(prm), 'sha256': digest(raw(prm))},
        'instruction': {'path': str(rule), 'sha256': digest(raw(rule))},
        'inputs': sorted(expected_inputs or actual_in, key=lambda x: x['path']),
        'required_reads': sorted(required_reads or []),
        'reads': sorted(reads),
        'receipts': receipts,
        'omp_version': ompv,
    }
    resp = text(ev / 'response.md')
    return resp, reads, meta
def check_actual_reads(ev, workdir, phase):
    guard = []
    events = []
    if (ev / 'guard.jsonl').is_file():
        guard = [strict(l) for l in text(ev / 'guard.jsonl').splitlines() if l.strip()]
    if (ev / 'events.jsonl').is_file():
        events = [strict(l) for l in text(ev / 'events.jsonl').splitlines() if l.strip()]
    reads = set()
    tool_results = {}
    for row in events:
        if row.get('type') == 'message_end':
            msg = row.get('message', {})
            if msg.get('role') == 'toolResult':
                tid = msg.get('toolCallId')
                contents = msg.get('content', [])
                if contents and isinstance(contents, list) and contents[0].get('type') == 'text':
                    tool_results[tid] = contents[0].get('text', '')
    for call, dec, exe, state in attempted_calls(guard, events):
        if state == 'EXECUTED' and exe:
            t = Path(exe.get('resolved_path', ''))
            if t.is_absolute() and t.is_relative_to(safe(workdir)):
                rel = t.relative_to(workdir).as_posix()
                if not (workdir / rel).is_file():
                    continue
                cid = call.get('id')
                if cid and cid in tool_results:
                    actual = tool_results[cid]
                    expected = text(workdir / rel)
                    require(actual == expected, f'executed read payload for {rel} differs from frozen packet content')
                    reads.add(rel)
                else:
                    require(False, f'missing/empty/error payload for credited read {rel}')
    if phase == 'judge':
        require({f'{d}.md' for d in DN} <= reads, 'judge must read all 40 distinct DN sources')
    elif phase == 'build':
        require('judgments.json' in reads, 'build must read judgments.json handoff')
    elif phase == 'retrieve':
        require('MOC.md' in reads, 'retrieve must read MOC.md')
    return reads
def call_stage(work, runner_p, phase, prompt_name, wdir, evdir, *, expected_inputs=None, required_reads=None):
    rule = safe(work / 'shared/controls/SAVED_INSTRUCTION.md')
    prm = safe(work / 'shared/controls' / prompt_name)
    require(rule.is_file() and prm.is_file(), f'missing rule or {prompt_name}')
    require(digest(raw(rule)) == source_identity(work, live=False)['instruction']['sha256'], 'saved instruction changed before model contact')
    wdir = safe(wdir)
    evdir = safe(evdir)
    if expected_inputs is None:
        expected_inputs = inventory(wdir)
    if required_reads is None:
        if phase == 'judge':
            required_reads = sorted([f'{d}.md' for d in DN])
        elif phase == 'build':
            required_reads = ['judgments.json']
        elif phase == 'retrieve':
            required_reads = ['MOC.md']
        else:
            required_reads = []
    # actual shared replay via declared frozen runner
    rt = runner_module(runner_p)
    code = rt.main(['--workdir', str(wdir), '--prompt', str(prm), '--instruction', str(rule), '--thinking', 'low', '--evidence', str(evdir)])
    if code != 0:
        return code, None, set(), None
    # mandatory verify on every call (shared replay, policy, full payloads, exact meta)
    resp, reads, meta = verify_phase(work, runner_p, phase, prm, wdir, evdir, expected_inputs, required_reads)
    return 0, resp, reads, meta


def runner_module(path):
    path = safe(path)
    raw(path)
    spec = importlib.util.spec_from_file_location('module02_runner', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def attempted_calls(guard, events):
    decisions = {row['call_id']: row for row in guard if row.get('type') == 'decision'}
    executed = {row['call_id']: row for row in guard if row.get('type') == 'executed'}
    for row in events:
        msg = row.get('message', {})
        if row.get('type') != 'message_end' or msg.get('role') != 'assistant':
            continue
        for call in msg.get('content', []):
            if call.get('type') != 'toolCall':
                continue
            dec = decisions.get(call['id'])
            exe = executed.get(call['id'])
            state = 'EXECUTED' if exe else ('ALLOWED_ABSENT' if dec and dec.get('allow') else 'DENIED')
            yield call, dec, exe, state




def validate_judgments(work, value):
    fields(value, {'claims', 'coverage'})
    claims = value['claims']
    require(isinstance(claims, list) and claims, 'claims required')
    seen = set()
    cmap = {}
    for c in claims:
        fields(c, {'claim_id', 'claim', 'treatment', 'reason', 'limits', 'sources'})
        jg = c['claim_id']
        require(re.fullmatch(r'JG-[0-9]{3}', jg), 'bad JG id')
        require(jg not in seen, 'duplicate JG')
        seen.add(jg)
        cmap[jg] = c
        treat = c['treatment']
        require(treat in {'use', 'qualify', 'unresolved', 'exclude'}, 'treatment must be use|qualify|unresolved|exclude')
        for fld in ('claim', 'reason', 'limits'):
            val = c.get(fld, '')
            require(isinstance(val, str), f'{fld} must be string')
            require(val.strip(), f'empty {fld}')
            require('[[' not in val and '](' not in val, f'model-injected markup/navigation refused in {fld} for {jg}')
        require(c['claim'].strip() and c['reason'].strip(), 'empty claim/reason')
        srcs = c['sources']
        require(isinstance(srcs, list), 'sources must be list')
        if treat in {'use', 'qualify'}:
            require(srcs, 'use/qualify need evidence')
        for s in srcs:
            fields(s, {'source_id', 'excerpt'})
            require(isinstance(s['excerpt'], str) and s['excerpt'].strip(), 'empty excerpt')
            support(work, s['source_id'], s['excerpt'])
    cov = value['coverage']
    require(isinstance(cov, list) and len(cov) == 40, 'exactly 40 coverage')
    cset = set()
    for e in cov:
        fields(e, {'source_id', 'reason'})
        sid = e['source_id']
        require(sid in DN, 'bad source in cov')
        require(sid not in cset, 'dup cov source')
        cset.add(sid)
        require(e['reason'].strip(), 'coverage reason required (empty not allowed)')
        require('[[' not in e['reason'] and '](' not in e['reason'], 'model-injected in coverage reason')
    return cmap


def validate_build(value, cmap):
    fields(value, {'notes'})
    notes = value['notes']
    require(isinstance(notes, list), 'notes must be list')
    seen = set()
    used = set()
    all_nids = set()
    for n in notes:
        all_nids.add(n.get('note_id'))
    for n in notes:
        fields(n, {'note_id', 'title', 'claim_ids', 'related'})
        nid = n['note_id']
        require(re.fullmatch(KB, nid), 'bad KB id')
        require(nid not in seen, 'dup note')
        seen.add(nid)
        title = n['title']
        require(isinstance(title, str) and title.strip(), 'empty title')
        require(not any(char in title for char in '[]|\r\n'), 'title must be one line without brackets or pipes')
        cids = n['claim_ids']
        require(isinstance(cids, list) and cids, 'note needs claim_ids')
        for j in cids:
            require(j in cmap and cmap[j]['treatment'] != 'exclude', 'excluded or unknown claim')
            require(j not in used, 'claim used >1')
            used.add(j)
        rels = n['related']
        require(isinstance(rels, list), 'related must be list')
        for r in rels:
            require(isinstance(r, dict) and set(r.keys()) >= {'note_id', 'reason'}, 'related entries must match {note_id,reason}')
            rid = r['note_id']
            require(re.fullmatch(KB, rid) and rid != nid and rid in all_nids, 'bad related target (must exist and distinct)')
            reason = r.get('reason', '')
            require(isinstance(reason, str) and reason.strip(), 'bad related')
            require('[[' not in reason and '](' not in reason, 'model-injected markup refused in related reason')
    non_ex = {j for j, c in cmap.items() if c['treatment'] != 'exclude'}
    require(used == non_ex, 'all non-exclude claims must be in exactly one note')
    return value


def render_knowledge_note(rev, nid, title, cids, rels, cmap):
    clines = []
    llines = []
    evs = []
    for j in cids:
        c = cmap[j]
        clines.append(f"[{j} {c['treatment']}] {c['claim']}")
        if c['limits'].strip():
            llines.append(f"[{j}] {c['limits']}")
        for s in c.get('sources', []):
            evs.append((s['source_id'], s['excerpt']))
    body = f"# {title}\n## Claim\n" + "\n\n".join(clines) + "\n## Limits and conflicts\n" + ("\n\n".join(llines) if llines else "No specific limits.") + "\n"
    body += "## Evidence\n"
    body += "Judgment provenance (AI): see " + ", ".join(f"[[Reviews/{rev}-judgments.md#{j}|{j}]]" for j in cids) + "\n"
    seen = set()
    for sid, ex in evs:
        if (sid, ex) in seen: continue
        seen.add((sid, ex))
        body += f"### [[Sources/{sid}]]\n" + "\n".join("> " + ln for ln in ex.splitlines()) + "\n"
    rel_ids = [r if isinstance(r, str) else r.get('note_id', '') for r in (rels or [])]
    body += "## Related\n" + "".join(f"- [[Knowledge/{rev}/{rid}|{rid}]]\n" for rid in rel_ids if rid)
    return body


def render_judgments_text(rev, cmap, cov):
    ls = [f"# {rev} judgments (AI-processed, provisional)\n"]
    source_claims = {sid: [] for sid in DN}
    for j in sorted(cmap):
        c = cmap[j]
        ls.append(f"## {j}\nTreatment: {c['treatment']}\nClaim: {c['claim']}\nReason: {c['reason']}\nLimits: {c['limits']}")
        for s in c.get('sources', []):
            if j not in source_claims[s['source_id']]:
                source_claims[s['source_id']].append(j)
            ls.append(f"### [[Sources/{s['source_id']}]]")
            ls.extend("> " + ln for ln in s['excerpt'].splitlines())
        ls.append("")
    ls.append("## Coverage\n" + "\n".join(f"- {e['source_id']}: {source_claims[e['source_id']]} {e['reason']}" for e in cov))
    return "\n".join(ls) + "\n"


def render_answers_text(rev, aval, cmap, bval, focus=None):
    ls = [f"# {rev} answers (AI-processed, provisional)\n"]
    note2claims = {nn['note_id']: [cmap[j] for j in nn.get('claim_ids', []) if j in cmap] for nn in bval.get('notes', [])}
    cited = set()
    for a in aval.get('answers', []):
        ls.append(f"## {a['question_id']} ({a['status']})\n{a['answer']}")
        for c in a.get('citations', []):
            ls.append(f"  [[Knowledge/{rev}/{c['note_id']}|{c['note_id']}]] · [[Sources/{c['source_id']}|{c['source_id']}]]: {c['excerpt']}")
            excerpt = c['excerpt'].replace('\r\n', '\n')
            candidates = (excerpt, decode_quote(excerpt))
            for cl in note2claims.get(c['note_id'], []):
                if not any(s['source_id'] == c['source_id'] and any(
                    quote in s['excerpt'].replace('\r\n', '\n') for quote in candidates
                ) for s in cl['sources']):
                    continue
                if cl.get('limits', '').strip():
                    ls.append(f"    (limit) {cl['limits']}")
                jg = cl['claim_id']
                ls.append(f"    (from judgment [[Reviews/{rev}-judgments.md#{jg}|{jg}]])")
            cited.add(c.get('note_id'))
        ls.append("")
    if focus and focus not in cited:
        ls.append(f"Focal note [[Knowledge/{rev}/{focus}|{focus}]] was read but is uncitable (no eligible use/qualify claims; honest unsupported path).")
        ls.append("")
    return "\n".join(ls) + "\n"


def render_navigation(rev, notes):
    """Pure MOC renderer. notes: list of build note dicts or ids. Matches staged MOC bytes."""
    mlines = ['# Knowledge index', '']
    for n in (notes or []):
        if isinstance(n, dict):
            nid = n.get('note_id', '')
            title = n.get('title', nid)
        else:
            nid = str(n)
            title = nid
        if nid:
            mlines.append(f"- [[Knowledge/{rev}/{nid}|{title}]]")
    return '\n'.join(mlines) + '\n'


def knowledge_signature(note, cmap):
    """Canonical bytes of substantive knowledge for comparison.
    Structured (not regex): sorted normalized claim/treatment/limits + (source_id, exact excerpt).
    Ignores claim IDs, title, ordering, generated paths/rev, reason/rel wording, whitespace.
    """
    if not isinstance(note, dict):
        note = {}
    cids = note.get('claim_ids', []) or []
    claim_norms = []
    for j in sorted(cids):
        c = cmap.get(j) or {}
        srcs = sorted((s.get('source_id', ''), s.get('excerpt', '')) for s in c.get('sources', []))
        claim_norms.append({
            'claim': (c.get('claim') or '').strip(),
            'treatment': c.get('treatment') or '',
            'limits': (c.get('limits') or '').strip(),
            'sources': [{'source_id': sid, 'excerpt': ex} for sid, ex in srcs]
        })
    payload = {'claims': claim_norms}
    return canonical(payload)


def render_judgments_md(work, rev, cmap, cov):
    txt = render_judgments_text(rev, cmap, cov)
    p = work / 'vault/Reviews' / f'{rev}-judgments.md'
    write_new(p, txt.encode())
    return p


def render_answers_md(work, rev, aval, cmap, bval, focus=None):
    txt = render_answers_text(rev, aval, cmap, bval, focus=focus)
    p = work / 'vault/Reviews' / f'{rev}-answers.md'
    write_new(p, txt.encode())
    return p


def validate_retrieve(work, rev, manifest, reads, aval, focus, cmap, build_notes=None):
    fields(aval, {'answers'})
    require(isinstance(aval.get('answers'), list), 'answers must be list')
    require(len(aval['answers']) == 3, 'exactly 3 answers')
    seenq = set()
    cited = set()
    for a in aval['answers']:
        fields(a, {'question_id', 'status', 'answer', 'citations'})
        q = a['question_id']
        require(q in {'Q1','Q2','Q3'} and q not in seenq, 'bad Q')
        seenq.add(q)
        require(a['status'] in {'supported','unsupported'}, 'bad status')
        ans = a['answer']
        require(isinstance(ans, str) and ans.strip(), 'empty answer')
        require('[[' not in ans and '](' not in ans, f'model-injected markup refused in answer {q}')
        cits = a.get('citations', [])
        require(isinstance(cits, list), 'citations list')
        if a['status'] == 'supported':
            require(cits, f'{q}: supported answer needs citations')
        for c in cits:
            fields(c, {'note_id', 'source_id', 'excerpt'})
            nid = c['note_id']
            require(re.fullmatch(KB, nid), 'bad cited nid')
            qrel = f'Knowledge/{rev}/{nid}.md'
            require(qrel in reads, f'unread citation {nid} (exact path required)')
            np = work / 'cold' / rev / 'Knowledge' / rev / (nid + '.md')
            require(np.is_file(), f'missing frozen note {nid}')
            quotes, _ = parse_note(raw(np), nid)
            ex = c['excerpt']
            cands = [ex.replace('\r\n','\n'), decode_quote(ex)]
            # every citation must match exact rendered note evidence
            require(any(cc and cc in qq['excerpt'] for qq in quotes if qq['source_id'] == c['source_id'] for cc in cands), 'fabricated excerpt')
            cited.add(nid)
            # stricter: the source+excerpt must be from an eligible (use/qualify) claim treatment in THIS note, not unresolved elsewhere in note or ambiguous
            if build_notes and cmap:
                bnotes = build_notes.get('notes', []) if isinstance(build_notes, dict) else (build_notes or [])
                nobj = next((nn for nn in bnotes if nn.get('note_id') == nid), None)
                if nobj:
                    eligible_exs = []
                    for j in nobj.get('claim_ids', []):
                        cl = cmap.get(j, {})
                        if cl.get('treatment') in {'use', 'qualify'}:
                            for s in cl.get('sources', []):
                                if s.get('source_id') == c['source_id']:
                                    eligible_exs.append(s.get('excerpt', ''))
                    matched_eligible = any( any(cc and (cc in el or el in cc) for cc in cands) for el in eligible_exs )
                    require(matched_eligible, f'{q} citation {c["source_id"]} excerpt must match eligible claim treatment in note {nid} (unresolved ambiguous not sufficient)')
    # per answer has at least one eligible (kept for overall)
    if build_notes and cmap:
        note_treats = {}
        bnotes = build_notes.get('notes', []) if isinstance(build_notes, dict) else (build_notes or [])
        for n in bnotes:
            note_treats[n.get('note_id')] = [cmap.get(j, {}).get('treatment', '') for j in n.get('claim_ids', []) if j in cmap]
        for a in aval['answers']:
            if a['status'] == 'supported':
                c_nids = [c['note_id'] for c in a.get('citations', [])]
                has_eligible = any(any(t in {'use', 'qualify'} for t in note_treats.get(nid, [])) for nid in c_nids)
                require(has_eligible, f"{a['question_id']}: supported answer cannot rely only on unresolved claims")
    if focus:
        # focal actual read always required (even all unsupported/uncitable)
        fpath = f'Knowledge/{rev}/{focus}.md'
        require(fpath in reads, f'focal note {focus} must be actually read')
        supported = any(a['status'] == 'supported' for a in aval['answers'])
        if supported:
            require(focus in cited, 'v2 must cite focal note for supported answers')
        # else uncitable focal read but not cited is ok, helper render will note limitation
    return aval




def freeze_rev(work, rev, prev=None, foc=None, moc_bytes=None):
    revision_id(rev)
    dest = absent(work / 'cold' / rev)
    src = source_identity(work, live=False)
    require(digest(raw(work / 'shared/controls/SAVED_INSTRUCTION.md')) == src['instruction']['sha256'], 'instruction changed')
    kdir = work / 'vault' / 'Knowledge' / rev
    require(kdir.is_dir(), 'no rendered Knowledge for rev')
    if moc_bytes is not None:
        moc_entry = dict(path='MOC.md', bytes=len(moc_bytes), sha256=digest(moc_bytes))
    else:
        moc_entry = dict(path='MOC.md', bytes=len(raw(work / 'vault/MOC.md')), sha256=digest(raw(work / 'vault/MOC.md')))
    files = [moc_entry]
    for p in sorted(kdir.iterdir()):
        if re.fullmatch(KB + r'\.md', p.name):
            d = raw(p)
            files.append(dict(path=f'Knowledge/{rev}/{p.name}', bytes=len(d), sha256=digest(d)))
    files.sort(key=lambda x: x['path'])
    if prev:
        old = check(work, prev)
    lock = absent(dest.with_name('.' + rev + '.lock'))
    lock.mkdir()
    tmp = Path(tempfile.mkdtemp(prefix='.' + rev + '-', dir=safe(dest.parent)))
    try:
        (tmp / 'Knowledge' / rev).mkdir(parents=True)
        for it in files:
            if it['path'] == 'MOC.md':
                if moc_bytes is not None:
                    write_new(tmp / 'MOC.md', moc_bytes)
                else:
                    sp = work / 'vault' / 'MOC.md'
                    write_new(tmp / it['path'], raw(sp))
            else:
                sp = work / 'vault' / 'Knowledge' / rev / Path(it['path']).name
                write_new(tmp / it['path'], raw(sp))
        navigation(tmp, files)
        absent(dest)
        publish_directory(tmp, dest)
    finally:
        if tmp.exists():
            shutil.rmtree(tmp)
        lock.rmdir()
    return {'files': files, 'previous': prev, 'focus_note': foc}


def do_run(work, rev, runner, ev_base, prev=None, foc=None, fb_path=None):
    work = safe(work)
    rev = revision_id(rev)
    rulep = work / 'shared/controls/SAVED_INSTRUCTION.md'
    if not rulep.is_file():
        print(f'HOLD: missing saved instruction: {rulep}', file=sys.stderr)
        return 2
    source_identity(work, live=True)
    # single work-wide exclusive lock for entire mutating lifecycle (MOC, KB, cold); released in finally on success/error/early return
    wlock = absent(work / '.module02-ai-handoff.lock')
    wlock.mkdir()
    try:
        prior = None
        require(prev or (foc is None and fb_path is None), 'focus-note and feedback require --previous')
        if prev:
            prev = revision_id(prev)
            prior = check(work, prev)
            require(foc and re.fullmatch(KB, foc), 'focus-note required for revision')
            require(fb_path, 'feedback required for v2 correction run')
            require(any(note['note_id'] == foc for note in load(work / 'runs' / prev / 'build.json')['notes']), f'focus-note {foc} is absent from previous revision {prev}')
        fb_text = ''
        if fb_path:
            fbp = safe(fb_path)
            require(fbp.is_file(), 'feedback missing')
            fb_text = text(fbp)
        if prior:
            require(fb_text.strip(), 'feedback must describe a source-backed correction')
        # under-lock preflight (real runner, fresh evidence, exact public no-overwrite) before run state or stage
        runner_p = safe(runner)
        require(runner_p.is_file(), 'runner missing or not regular file')
        base = safe(ev_base)
        absent(base)
        # subs created later; whole evidence base must be fresh (no adopt other files)
        pub_k = work / 'vault' / 'Knowledge' / rev
        require(not pub_k.exists(), f'public Knowledge/{rev} dir already exists')
        for suf in ('-judgments.md', '-answers.md'):
            rp = work / 'vault' / 'Reviews' / f'{rev}{suf}'
            require(not rp.exists(), f'public Reviews {rev}{suf} already exists')
        cld = work / 'cold' / rev
        require(not cld.exists(), f'cold/{rev} already exists')
        rdir = work / 'runs' / rev
        absent(rdir)
        rdir.mkdir(parents=True)
        if fb_text:
            write_new(rdir / 'feedback.md', fb_text.encode())
        if prior:
            prdir = work / 'runs' / prev
            if (prdir / 'judgments.json').is_file():
                write_new(rdir / 'previous-judgments.json', raw(prdir / 'judgments.json'))
            if (prdir / 'build.json').is_file():
                write_new(rdir / 'previous-build.json', raw(prdir / 'build.json'))

        # judge packet
        jpack = rdir / 'inputs' / 'judge'
        jpack.mkdir(parents=True)
        for d in sorted(DN):
            write_new(jpack / (d + '.md'), raw(work / 'vault/Sources' / (d + '.md')))
        if fb_text:
            write_new(jpack / 'Feedback.md', fb_text.encode())
        if prior:
            if (rdir / 'previous-judgments.json').is_file():
                write_new(jpack / 'previous-judgments.json', raw(rdir / 'previous-judgments.json'))
            if (rdir / 'previous-build.json').is_file():
                write_new(jpack / 'previous-build.json', raw(rdir / 'previous-build.json'))
        if fb_text:
            require(fb_text.strip(), 'feedback must be meaningful for v2')
        # freeze controls and phase prompts (pure derivation; no raw leaks to retrieve; model must read frozen)
        ctrl = rdir / 'controls'
        ctrl.mkdir(parents=True, exist_ok=True)
        for bn in ('SAVED_INSTRUCTION.md', 'JUDGE_PROMPT.md', 'BUILD_PROMPT.md', 'RETRIEVE_PROMPT.md'):
            bp = work / 'shared/controls' / bn
            write_new(ctrl / bn, raw(bp))
        bprm = rdir / 'base-prompts'
        bprm.mkdir(parents=True, exist_ok=True)
        for bn in ('JUDGE_PROMPT.md', 'BUILD_PROMPT.md', 'RETRIEVE_PROMPT.md'):
            write_new(bprm / bn, raw(work / 'shared/controls' / bn))
        prm_dir = rdir / 'prompts'
        prm_dir.mkdir(parents=True, exist_ok=True)
        for ph, bn in (('judge','JUDGE_PROMPT.md'),('build','BUILD_PROMPT.md'),('retrieve','RETRIEVE_PROMPT.md')):
            bt = text(work / 'shared/controls' / bn)
            write_new(prm_dir / f'{ph}.md', phase_prompt(bt, ph, rev, prev, foc).encode())
        j_prompt = prm_dir / 'judge.md'
        j_exp = inventory(jpack)
        j_req = [e['path'] for e in j_exp]
        ej = base / 'judge'
        code, resp, rds, meta = call_stage(work, runner, 'judge', j_prompt, jpack, ej, expected_inputs=j_exp, required_reads=j_req)
        if code != 0:
            return code
        jv = response_json(resp)
        cmap = validate_judgments(work, jv)
        save(rdir / 'judgments.json', jv)
        # judgments record published with pure render after retrieve validation (no early md write)
        save(rdir / 'judge-phase.json', meta)
        # build
        bpack = rdir / 'inputs' / 'build'
        bpack.mkdir(parents=True)
        write_new(bpack / 'judgments.json', raw(rdir / 'judgments.json'))
        if prior and (rdir / 'previous-build.json').is_file():
            write_new(bpack / 'previous-build.json', raw(rdir / 'previous-build.json'))
        eb = base / 'build'
        b_exp = inventory(bpack)
        b_req = [e['path'] for e in b_exp]
        b_prompt = prm_dir / 'build.md'
        code, resp, rds, meta = call_stage(work, runner, 'build', b_prompt, bpack, eb, expected_inputs=b_exp, required_reads=b_req)
        if code != 0:
            return code
        bv = response_json(resp)
        validate_build(bv, cmap)
        if prior:
            pbuild = load(rdir / 'previous-build.json')
            prior_nids = {n.get('note_id') for n in pbuild.get('notes', []) if n.get('note_id')}
            curr_nids = {n.get('note_id') for n in bv.get('notes', []) if n.get('note_id')}
            require(prior_nids.issubset(curr_nids), 'old note identities must be preserved across revisions')
        if foc:
            focal_note = next((n for n in bv.get('notes', []) if n.get('note_id') == foc), None)
            if focal_note:
                treats = [cmap.get(j, {}).get('treatment', '') for j in focal_note.get('claim_ids', [])]
                if treats and all(t == 'exclude' for t in treats):
                    print(f'HOLD: focal note {foc} wholly excluded; technical hold before publish', file=sys.stderr)
                    return 1
        save(rdir / 'build.json', bv)
        save(rdir / 'build-phase.json', meta)
        # render notes to vault/Knowledge/rev/ (staged; live nav only updated on full success)
        kdir = work / 'vault' / 'Knowledge' / rev
        kdir.mkdir(parents=True)
        for n in bv['notes']:
            body = render_knowledge_note(rev, n['note_id'], n['title'], n['claim_ids'], n.get('related', []), cmap)
            parse_note(body.encode(), n['note_id'])
            write_new(kdir / (n['note_id'] + '.md'), body.encode())
        # compute correct rev MOC bytes from this build (staged for cold; live MOC only post full success)
        mlines = ['# Knowledge index', '']
        for n in bv['notes']:
            mlines.append(f"- [[Knowledge/{rev}/{n['note_id']}|{n['title']}]]")
        moc_bytes = ('\n'.join(mlines) + '\n').encode()
        # require semantic (not cosmetic) focal change via knowledge_signature (ignores ids/titles/paths/reasons/rels per contract)
        if prior and foc:
            pj_p = rdir / 'previous-judgments.json'
            require(pj_p.is_file(), 'prior judgments required for v2 focal signature')
            pjv = load(pj_p)
            prior_cmap = validate_judgments(work, pjv)
            pbuild_p = rdir / 'previous-build.json'
            require(pbuild_p.is_file(), 'prior build required for v2 focal signature')
            pbuild = load(pbuild_p)
            prior_focal = next((n for n in pbuild.get('notes', []) if n.get('note_id') == foc), None)
            require(prior_focal, 'prior focal not found in previous build')
            new_focal = next((n for n in bv.get('notes', []) if n.get('note_id') == foc), None)
            require(new_focal, 'focal note not present in this build')
            sig_new = knowledge_signature(new_focal, cmap)
            sig_old = knowledge_signature(prior_focal, prior_cmap)
            require(sig_new != sig_old, 'focal change is only cosmetic (prefix/whitespace/render/ids)')
        # freeze using staged MOC bytes (cold gets this rev's index, not prior live MOC)
        freeze_info = freeze_rev(work, rev, prev, foc, moc_bytes=moc_bytes)
        base_files = freeze_info.get('files', [])
        fman = {
            'schema_version': 2,
            'files': base_files,
            'root_fingerprint': digest(canonical(base_files)),
            'source_manifest_sha256': digest(raw(work / 'source-manifest.json')),
            'instruction_sha256': source_identity(work, live=False)['instruction']['sha256'],
            'prompt_shas': {
                'judge': digest(raw(work / 'shared/controls/JUDGE_PROMPT.md')),
                'build': digest(raw(work / 'shared/controls/BUILD_PROMPT.md')),
                'retrieve': digest(raw(work / 'shared/controls/RETRIEVE_PROMPT.md')),
            },
            'judgments_sha256': digest(raw(rdir / 'judgments.json')),
            'build_sha256': digest(raw(rdir / 'build.json')),
            'previous': freeze_info.get('previous'),
            'previous_manifest_sha256': digest(raw(work / 'identities' / (prev + '.json'))) if prev else None,
            'focus_note': freeze_info.get('focus_note'),
            'phases': {'judge': load(rdir / 'judge-phase.json')},
        }
        # retrieve on cold
        # retrieve on cold (use frozen, exact expected from staged MOC+KB, min required MOC+focal)
        cold = work / 'cold' / rev
        er = base / 'retrieve'
        r_exp = inventory(cold)
        r_req = ['MOC.md']
        if foc:
            r_req.append(f'Knowledge/{rev}/{foc}.md')
        r_prompt = prm_dir / 'retrieve.md'
        code, resp, rds, meta = call_stage(work, runner, 'retrieve', r_prompt, cold, er, expected_inputs=r_exp, required_reads=r_req)
        if code != 0:
            return code
        av = response_json(resp)
        validate_retrieve(work, rev, fman, rds, av, foc, cmap, bv)
        # after retrieve validation: preserve answers.json + pure-rendered judgment/answer records
        save(rdir / 'answers.json', av)
        jtext = render_judgments_text(rev, cmap, jv.get('coverage', []))
        write_new(work / 'vault' / 'Reviews' / f'{rev}-judgments.md', jtext.encode())
        atext = render_answers_text(rev, av, cmap, bv, focus=foc)
        write_new(work / 'vault' / 'Reviews' / f'{rev}-answers.md', atext.encode())
        save(rdir / 'retrieve-phase.json', meta)
        # complete schema2 manifest with all supplied fields
        fman['answers_sha256'] = digest(raw(rdir / 'answers.json'))
        fman['feedback_sha256'] = digest(fb_text.encode()) if fb_text else None
        fman['phases']['build'] = load(rdir / 'build-phase.json')
        fman['phases']['retrieve'] = meta
        fman['run_files'] = inventory(rdir)
        pubf = []
        for n in bv.get('notes', []):
            kp = work / 'vault' / 'Knowledge' / rev / (n.get('note_id') + '.md')
            if kp.is_file():
                d = raw(kp)
                pubf.append(dict(path=f'Knowledge/{rev}/{n["note_id"]}.md', bytes=len(d), sha256=digest(d)))
        for suf in ('-judgments.md', '-answers.md'):
            rp = work / 'vault' / 'Reviews' / f'{rev}{suf}'
            if rp.is_file():
                d = raw(rp)
                pubf.append(dict(path=f'Reviews/{rev}{suf}', bytes=len(d), sha256=digest(d)))
        fman['public_files'] = sorted(pubf, key=lambda x:x['path'])
        fman['revision'] = rev
        man_p = work / 'identities' / (rev + '.json')
        moc_live = work / 'vault' / 'MOC.md'
        old_moc = raw(moc_live) if moc_live.is_file() else None
        try:
            replace_latest_moc(work, rev, moc_bytes)
            save(man_p, fman)
            print(f'PASS: run --revision {rev}')
            return 0
        except Exception:
            if old_moc is not None:
                tmp_r = moc_live.parent / ('.tmp-restore-' + rev)
                write_new(tmp_r, old_moc)
                os.replace(tmp_r, moc_live)
            raise
    finally:
        if wlock.exists():
            wlock.rmdir()
def do_retrieve(work, rev, runner, ev_base):
    work = safe(work)
    rev = revision_id(rev)
    rulep = work / 'shared/controls/SAVED_INSTRUCTION.md'
    if not rulep.is_file():
        print(f'HOLD: missing saved instruction: {rulep}', file=sys.stderr)
        return 2
    source_identity(work, live=False)
    manifest = check(work, rev)
    cold = work / 'cold' / rev
    base = safe(ev_base)
    er = base / 'retrieve'
    expected = inventory(cold)
    req = ['MOC.md']
    fn = manifest.get('focus_note')
    if fn:
        req.append(f'Knowledge/{rev}/{fn}.md')
    frz = work / 'runs' / rev / 'prompts' / 'retrieve.md'
    prm_arg = frz if frz.is_file() else 'RETRIEVE_PROMPT.md'
    code, resp, rds, meta = call_stage(work, runner, 'retrieve', prm_arg, cold, er, expected_inputs=expected, required_reads=req)
    if code != 0:
        return code
    av = response_json(resp)
    cmap = {}
    rj = work / 'runs' / rev / 'judgments.json'
    if rj.is_file():
        cmap = validate_judgments(work, load(rj))
    bv = {'notes': []}
    rb = work / 'runs' / rev / 'build.json'
    if rb.is_file():
        bv = load(rb)
    validate_retrieve(work, rev, manifest, rds, av, fn, cmap, bv)
    # standalone: fresh evidence; skip render to avoid rewriting immutable answers.md; useful negative for missing rule before correction
    print(f'PASS: retrieve --revision {rev} (fresh evidence {er})')
    return 0




def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    pi = sub.add_parser('initialize')
    pi.add_argument('--work', required=True, type=Path)
    pr = sub.add_parser('run')
    pr.add_argument('--work', required=True, type=Path)
    pr.add_argument('--revision', required=True)
    pr.add_argument('--runner', required=True, type=Path)
    pr.add_argument('--evidence', required=True, type=Path)
    pr.add_argument('--previous')
    pr.add_argument('--focus-note')
    pr.add_argument('--feedback', type=Path)
    prt = sub.add_parser('retrieve')
    prt.add_argument('--work', required=True, type=Path)
    prt.add_argument('--revision', required=True)
    prt.add_argument('--runner', required=True, type=Path)
    prt.add_argument('--evidence', required=True, type=Path)
    pc = sub.add_parser('check')
    pc.add_argument('--work', required=True, type=Path)
    pc.add_argument('--revision', required=True)
    args = parser.parse_args(argv)
    try:
        w = safe(args.work)
        require(w.is_dir(), f'missing work: {w}')
        if args.command == 'initialize':
            r = safe(w / 'shared/controls/SAVED_INSTRUCTION.md')
            if not r.is_file():
                print(f'HOLD: missing saved instruction: {r}', file=sys.stderr)
                return 2
            initialize(w)
        elif args.command == 'run':
            p = args.previous
            f = args.feedback
            return do_run(w, args.revision, args.runner, args.evidence, p, args.focus_note, f)
        elif args.command == 'retrieve':
            return do_retrieve(w, args.revision, args.runner, args.evidence)
        elif args.command == 'check':
            check(w, args.revision)
        print(f'PASS: {args.command}')
        return 0
    except (OSError, ValueError, UnicodeError, TypeError, KeyError, AttributeError, RuntimeError, ImportError) as e:
        print(f'HOLD: {e}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
