# Modified 2026-10-29 for the independent Simulation Lab edition; see NOTICE and MODIFICATIONS.md.
"""Server-owned target permissions. Model output and uploaded HTML grant none."""
import base64
import json
import mimetypes
import os
from pathlib import Path
import re
import socket
import ipaddress
from urllib.parse import urlparse, urljoin, unquote, parse_qs, urlunparse

from ..provider import ROOT, data_dir
from ..lab import identifier

LOCAL_ORIGIN = 'http://simlab-journey.test'
MAX_FILES, MAX_FILE, MAX_TOTAL = 100, 2 * 1024 * 1024, 12 * 1024 * 1024
SUFFIXES = {'.html', '.htm', '.css', '.js', '.svg', '.png', '.jpg', '.jpeg', '.webp'}
DANGEROUS = re.compile(r'(logout|unsubscribe|delete|destroy|payout|transfer|capture|refund|send.?mail|send.?email|send.?sms|withdraw|webhook|charge|place.?order|purchase)', re.I)
SENSITIVE = re.compile(r'(password|passwd|secret|token|authorization|access.?token|refresh.?token|api.?key|credit.?card|card.?number|cvv|security.?code|one.?time)', re.I)


class SafetyError(ValueError):
    pass


def redact(text):
    text = str(text)
    text = re.sub(r'\b[^\s@]+@[^\s@]+\.[^\s@]+\b', '[email]', text)
    text = re.sub(r'\b(?:\d[ -]?){9,}\b', '[number]', text)
    text = re.sub(r'\b(?:sk-|Bearer\s+)[A-Za-z0-9._-]+', '[secret]', text, flags=re.I)
    text = re.sub(r'(?i)(password|secret|token|api_key)\s*[:=]\s*\S+', r'\1=[redacted]', text)
    text = re.sub(r'\b[A-Za-z0-9_-]{28,}\b', '[opaque identifier]', text)
    return text[:600]


def evidence_url(url):
    p = urlparse(url)
    host = p.hostname or ''
    try:
        host += ':' + str(p.port) if p.port else ''
    except ValueError:
        pass
    return urlunparse((p.scheme, host, redact(p.path), '', '', ''))


def origin(url):
    p = urlparse(url)
    if p.scheme not in {'http', 'https'} or not p.hostname or p.username or p.password:
        raise SafetyError('Only explicitly authorized HTTP(S) origins without credentials are supported.')
    return f'{p.scheme}://{p.netloc}'


def safe_file(name):
    name = name.replace('\\', '/')
    path = Path(name)
    if path.is_absolute() or '..' in path.parts or any(x.startswith('.') for x in path.parts) or path.suffix.lower() not in SUFFIXES:
        raise SafetyError('Unsupported or unsafe wireframe path.')
    return path.as_posix()


def save_bundle(files):
    from .. import lab
    if not 1 <= len(files) <= MAX_FILES:
        raise SafetyError('Provide 1–100 wireframe files.')
    cleaned = {safe_file(k): v for k, v in files.items()}
    if any(len(v) > MAX_FILE for v in cleaned.values()) or sum(map(len, cleaned.values())) > MAX_TOTAL:
        raise SafetyError('Wireframes are limited to 2 MB per file and 12 MB total.')
    if not any(Path(k).suffix.lower() in {'.html', '.htm'} for k in cleaned):
        raise SafetyError('Include an HTML entry page.')
    value = lab.save('journey_bundles', {'name': 'Uploaded local wireframe',
        'files': {k: base64.b64encode(v).decode() for k, v in cleaned.items()}})
    return {'id': 'bundle-' + value['id'], 'name': value['name'],
            'pages': [k for k in cleaned if Path(k).suffix in {'.html', '.htm'}]}


def targets():
    result = {'sample': {'id': 'sample', 'name': 'Seeded local journey wireframes', 'kind': 'fixture',
                        'origin': LOCAL_ORIGIN, 'login_authorized': False, 'sandbox_only': True}}
    config_file = os.getenv('SIMLAB_JOURNEY_TARGETS_FILE')
    if config_file:
        registered = json.loads(Path(config_file).read_text())
        for name, target in registered.items():
            if name == 'sample' or not re.fullmatch(r'[a-zA-Z][a-zA-Z0-9_-]{0,60}', name):
                raise SafetyError('Invalid journey target identifier.')
            validate_target(target)
            result[name] = dict(target, id=name)
    folder = data_dir() / 'journey_bundles'
    for path in sorted(folder.glob('*.json'))[:100] if folder.exists() else []:
        result['bundle-' + path.stem] = {'id': 'bundle-' + path.stem, 'name': 'Uploaded local wireframe ' + path.stem[:8],
            'kind': 'bundle', 'origin': LOCAL_ORIGIN, 'sandbox_only': True, 'login_authorized': False}
    return result


def validate_target(target):
    if target.get('kind') not in {'staging', 'local'}:
        raise SafetyError('Interactive production targets are prohibited.')
    parsed = urlparse(target.get('origin', ''))
    canonical = origin(target.get('origin', ''))
    if target.get('origin') != canonical or parsed.path or parsed.query or parsed.fragment:
        raise SafetyError('Target origin must be exact, without a path or query.')
    required = ('interactive_authorized', 'seeded_test_data_only', 'sandbox_services_confirmed')
    if any(target.get(flag) is not True for flag in required):
        raise SafetyError('A target requires explicit interactive authorization, seeded data and sandbox service confirmation.')
    if target['kind'] == 'local':
        if parsed.hostname not in {'127.0.0.1', 'localhost', '::1'} or parsed.port in {3000, 5001, 7474, 7687, 11434, 3306, 6379}:
            raise SafetyError('Use a dedicated local test-app origin, not lab/admin/database ports.')
    elif parsed.scheme != 'https' or not re.search(r'(^|[.-])(staging|stage|sandbox|test|qa|dev|preview)([.-]|$)', parsed.hostname):
        raise SafetyError('Staging must use HTTPS and an explicit staging/test hostname. Production is not enabled.')
    if not target.get('read_paths') or any(not p.startswith('/') or '?' in p or '*' in p or '..' in p or DANGEROUS.search(p) for p in target['read_paths']):
        raise SafetyError('List explicit safe GET paths. Wildcards and dangerous endpoints are prohibited.')
    if target.get('session_file') and target.get('login_authorized') is not True:
        raise SafetyError('A seeded test session requires explicit staging login authorization.')
    if target.get('session_file'):
        path = Path(target['session_file'])
        if not path.is_absolute() or not path.is_file() or path.stat().st_mode & 0o077:
            raise SafetyError('Authorized seeded session must be an existing private (0600) file.')


class TargetPolicy:
    def __init__(self, target_id, template, entry_path=None):
        from .templates import TEMPLATES
        self.target = targets().get(target_id)
        if not self.target:
            raise SafetyError('Target is not registered. Imported URLs do not authorize interactive journeys.')
        self.origin = self.target['origin']
        self.files = {}
        if self.target['kind'] == 'fixture':
            folder = ROOT / 'examples/simlab-journeys'
            self.files = {p.name: p.read_bytes() for p in folder.iterdir() if p.is_file() and p.suffix in SUFFIXES}
        elif self.target['kind'] == 'bundle':
            from ..lab import load
            value = load('journey_bundles', identifier(target_id.removeprefix('bundle-')))
            self.files = {k: base64.b64decode(v) for k, v in value['files'].items()}
        entry = entry_path or self.target.get('entries', {}).get(template) or TEMPLATES[template]['entry']
        if self.files and entry_path and entry not in self.files:
            raise SafetyError('Entry page is not included in the uploaded bundle.')
        if self.files and entry not in self.files:
            entry = next((k for k in self.files if k.endswith(('.html', '.htm'))), '')
        self.entry = urljoin(self.origin + '/', entry)
        self.checkpoints = self.target.get('checkpoints', {}).get(template, {})
        self.permit(self.entry, 'GET')

    def permit(self, url, method):
        p = urlparse(url)
        if origin(url) != self.origin or p.username or p.password:
            raise SafetyError('Request destination is not the explicitly allowlisted target origin.')
        path = unquote(p.path)
        if '..' in path.split('/') or '\\' in path or DANGEROUS.search(path):
            raise SafetyError('Irreversible or unsafe endpoint is blocked.')
        if any(SENSITIVE.search(k) for k in parse_qs(p.query)):
            raise SafetyError('Credential-bearing URLs are blocked.')
        if self.files:
            if method not in {'GET', 'HEAD'} or path.lstrip('/') not in self.files:
                raise SafetyError('Local bundles cannot send network writes or access files outside the bundle.')
            return 'local'
        if method not in {'GET', 'HEAD'}:
            mock = self.target.get('mock_routes', {}).get(method + ' ' + path)
            if not mock:
                raise SafetyError('All real writes, purchases, payouts and email operations are blocked.')
            return 'mock'
        if path not in self.target['read_paths'] or set(parse_qs(p.query)) - set(self.target.get('query_keys', [])):
            raise SafetyError('GET path or query is not in the server-owned allowlist.')
        return 'read'

    def check_address(self):
        if self.files:
            return
        parsed = urlparse(self.origin)
        addresses = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == 'https' else 80))
        for item in addresses:
            ip = ipaddress.ip_address(item[4][0])
            if self.target['kind'] == 'local':
                if not ip.is_loopback:
                    raise SafetyError('Local test host resolved outside loopback.')
            elif not ip.is_global:
                raise SafetyError('Staging target resolved to a private or reserved network.')

    def install(self, context, record):
        counter = [0]
        def route_handler(route):
            req = route.request
            try:
                counter[0] += 1
                if counter[0] > 120:
                    raise SafetyError('Request count limit reached.')
                mode = self.permit(req.url, req.method)
                if mode == 'local':
                    name = unquote(urlparse(req.url).path).lstrip('/')
                    route.fulfill(body=self.files[name], content_type=mimetypes.guess_type(name)[0] or 'text/plain',
                        headers={'Content-Security-Policy': "default-src 'self' data: blob:; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-src 'none'; object-src 'none'; form-action 'self'; base-uri 'none'"})
                elif mode == 'mock':
                    body = self.target['mock_routes'][req.method + ' ' + urlparse(req.url).path]
                    route.fulfill(status=200, json=body)
                else:
                    self.check_address()
                    response = route.fetch(max_redirects=0, timeout=5000)
                    if 300 <= response.status < 400:
                        self.permit(urljoin(req.url, response.headers.get('location', '')), 'GET')
                    if int(response.headers.get('content-length', '0')) > MAX_FILE:
                        raise SafetyError('Response size limit exceeded.')
                    content = response.body()
                    if len(content) > MAX_FILE:
                        raise SafetyError('Response size limit exceeded.')
                    route.fulfill(response=response, body=content)
                    if response.status >= 400:
                        record('http_error', {'method': req.method, 'url': evidence_url(req.url), 'status': response.status})
                record('request', {'method': req.method, 'url': evidence_url(req.url), 'handling': mode})
            except Exception:
                record('blocked_request', {'method': req.method, 'url': evidence_url(req.url), 'reason': 'Target policy denied request or safe fetch failed.'})
                route.abort()
        context.route('**/*', route_handler)
        def block_ws(ws):
            record('blocked_request', {'reason': 'WebSockets are disabled.'})
            # An intercepted socket has no server connection unless
            # connect_to_server() is called. Keep it as a local inert mock;
            # synchronous close() during interception deadlocks on this runtime.
            ws.on_message(lambda _message: None)
        context.route_web_socket('**/*', block_ws)
