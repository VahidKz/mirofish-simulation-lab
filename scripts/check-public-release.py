#!/usr/bin/env python3
# Modified 2026-10-29 for the independent Simulation Lab edition; see NOTICE and MODIFICATIONS.md.
"""Check candidate source paths and content before public distribution.

Complements an independent redacted secret scan; cannot prove arbitrary source
content contains no confidential information.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LICENSE_SHA256 = '8486a10c4393cee1c25392769ddd3b2d6c242d6ec7928e1414efff7dfb2f07ef'
EXAMPLES = {'.env.example', '.env.simlab.example'}
PRIVATE_ROOTS = {'knowledge-base', 'private', 'secrets', 'credentials', '.codex', '.auth', '.run', 'scan-results'}
RUNTIME_PARTS = {'node_modules', '.venv', 'venv', '__pycache__', '.pytest_cache'}


def forbidden_path(name):
    path = Path(name)
    parts, base = path.parts, path.name.lower()
    if not parts:
        return True
    if parts[0] in PRIVATE_ROOTS or any(p in RUNTIME_PARTS for p in parts):
        return True
    if name.startswith(('backend/uploads/', 'backend/logs/', 'backend/test-artifacts/', 'frontend/dist/')):
        return True
    if base.startswith('.env') and name not in EXAMPLES:
        return True
    if base in {'auth.json', 'credentials.json', 'session.json'} or base.startswith(('storage-state', 'storage_state')):
        return True
    if path.suffix.lower() in {'.pem', '.key', '.p12', '.pfx', '.sqlite', '.sqlite3', '.db', '.log'}:
        return True
    return base.endswith('.trace.zip') or any(v in base for v in ['ceo_presentation', 'buyer_audit', 'case_audit'])


def violations(data, forbidden_terms=()):
    text = data.decode('utf-8', 'ignore')
    patterns = {
        'private source identifier': r'local-[a-f0-9]{12}',
        'private workstation path': r'(?:/home/[a-z][a-z0-9_-]*/|C:\\Users\\[A-Za-z])',
        'credential-like token': r'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|sk-(?:proj-)?[A-Za-z0-9_-]{32,})',
        'private key': r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
    }
    for category, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            yield category, text.count('\n', 0, match.start()) + 1
    folded = text.casefold()
    for term in forbidden_terms:
        offset = folded.find(term.casefold())
        if offset >= 0:
            yield 'excluded customer reference', text.count('\n', 0, offset) + 1
            break


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--history', action='store_true', help='Also check forbidden paths in all reachable refs')
    parser.add_argument('--deny-terms-file', default=os.getenv('SIMLAB_RELEASE_DENY_TERMS_FILE'),
                        help='Private JSON list of customer names/identifiers to exclude; never commit this file')
    args = parser.parse_args()
    terms = json.loads(Path(args.deny_terms_file).read_text()) if args.deny_terms_file else []
    if not isinstance(terms, list) or any(not isinstance(t, str) or not t or len(t)>250 for t in terms):
        raise SystemExit('The private deny-terms file must contain bounded nonempty strings.')
    raw = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=ROOT)
    names = sorted(set(filter(None, raw.decode().split('\0'))))
    failures = []
    for name in names:
        if any(term.casefold() in name.casefold() for term in terms):
            failures.append(('excluded customer path', name, 0))
            continue
        if forbidden_path(name):
            failures.append(('excluded path', name, 0))
            continue
        path = ROOT / name
        if path.is_symlink():
            failures.append(('symlink requires explicit review', name, 0))
            continue
        if path.is_file():
            for category, line in violations(path.read_bytes(), terms):
                failures.append((category, name, line))
    if hashlib.sha256((ROOT / 'LICENSE').read_bytes()).hexdigest() != LICENSE_SHA256:
        failures.append(('upstream license changed', 'LICENSE', 0))
    for required in ['NOTICE', 'MODIFICATIONS.md', 'README.md', 'THIRD_PARTY_NOTICES.md', 'PUBLIC_RELEASE.md']:
        if required not in names:
            failures.append(('missing release notice', required, 0))
    if args.history:
        objects = subprocess.check_output(['git', 'rev-list', '--objects', '--all'], cwd=ROOT, text=True)
        for row in objects.splitlines():
            if ' ' in row:
                name = row.split(' ', 1)[1]
                if name and forbidden_path(name):
                    failures.append(('excluded historical path', name, 0))
                if name and any(term.casefold() in name.casefold() for term in terms):
                    failures.append(('excluded historical customer path', name, 0))
    if failures:
        for category, name, line in failures:
            print(f'FAIL {category}: {name}:{line} (content withheld)')
        raise SystemExit(1)
    print(f'PASS: {len(names)} candidate paths; license/notice, private-content and runtime-path checks passed.')
    if args.history:
        print('PASS: all reachable Git-history paths checked. Run an independent history secret scan as well.')


if __name__ == '__main__':
    main()
