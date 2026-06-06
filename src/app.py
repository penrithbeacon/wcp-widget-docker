"""
WCP Widget: Docker
Four instruments: Local Docker, NAS Docker, Docker Hub, Settings.
Port: 3744  |  Specification: https://widgetcontextprotocol.com
"""

import io, json, os, time, zipfile
from urllib.parse import urlparse
import requests
import docker as docker_sdk
from flask import Flask, jsonify, request, Response, render_template

app = Flask(__name__)

PUBLISHED_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'published', 'index.html')
SETTINGS_FILE  = '/app/data/settings.json'
CACHE_TTL      = 15  # seconds

os.makedirs('/app/data', exist_ok=True)

# ── Settings ──────────────────────────────────────────────────────────────────

_DEFAULT_SETTINGS = {
    'nas_agent_url':   '',
    'nas_agent_token': '',
    'hub_pat':         '',
}

def read_settings():
    try:
        with open(SETTINGS_FILE) as f:
            s = json.load(f)
        return {**_DEFAULT_SETTINGS, **s}
    except Exception:
        return dict(_DEFAULT_SETTINGS)

def write_settings(data):
    merged = {**read_settings(), **{k: data[k] for k in data if k in _DEFAULT_SETTINGS}}
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(merged, f, indent=2)
    return merged

# ── Cache ─────────────────────────────────────────────────────────────────────

_cache = {}

def get_cache(key):
    c = _cache.get(key)
    if c and time.time() - c['t'] < CACHE_TTL:
        return c['v']
    return None

def set_cache(key, v):
    _cache[key] = {'v': v, 't': time.time()}

def clear_cache(key=None):
    if key:
        _cache.pop(key, None)
    else:
        _cache.clear()

# ── Helpers ───────────────────────────────────────────────────────────────────

def human_size(n):
    if not n:
        return '—'
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if n < 1024:
            return f'{n:.1f} {unit}'
        n /= 1024
    return f'{n:.1f} TB'

def get_instance_id():
    iid = request.headers.get('Wcp-Instance-Id', '').strip()
    return iid or request.args.get('wcpInstanceId', '').strip()

def get_orchestration_id():
    oid = request.headers.get('Wcp-Orchestration-Id', '').strip()
    return oid or request.args.get('wcpOrchestrationId', '').strip()

def get_application_id():
    aid = request.headers.get('Wcp-Application-Id', '').strip()
    return aid or request.args.get('wcpApplicationId', '').strip()

# ── WCP Manifest ─────────────────────────────────────────────────────────────

WCP_MANIFEST = {
    'wcp':     '2.1.0',
    'uuid':    'a3f8c291-7e4b-4d1a-b6f2-9c0e5d3a8b47',
    'name':    'Docker',
    'version': '1.2.0',
    'description': (
        'Docker management across local and NAS hosts, plus a Docker Hub browser. '
        'Four instruments: Local Docker, NAS Docker, Docker Hub, Settings.'
    ),
    'icon':    '/widget/icon.svg',
    'health':  '/widget/health',
    'container': {
        'image':            'docker.io/penrithbeacon/wcp-widget-docker',
        'source':           {'type': 'registry'},
        'tag':              '1.2.0-wcp2.1.0',
        'port':             3744,
        'volumes':          [{'name': 'docker_data', 'mountPath': '/app/data'}],
        'defaultLifecycle': 'always',
    },
    'components': [
        {
            'id': 'docker-local', 'uuid': 'b1c2d3e4-f5a6-7890-bcde-f12345678901',
            'name': 'Local Docker', 'role': 'widget',
            'path': '/widget/local', 'icon': '/widget/icon.svg',
            'renderMode': 'iframe', 'defaultSize': {'w': 12, 'h': 6},
        },
        {
            'id': 'docker-nas', 'uuid': 'c2d3e4f5-a6b7-8901-cdef-234567890123',
            'name': 'NAS Docker', 'role': 'widget',
            'path': '/widget/nas', 'icon': '/widget/icon.svg',
            'renderMode': 'iframe', 'defaultSize': {'w': 12, 'h': 6},
        },
        {
            'id': 'docker-hub', 'uuid': 'd3e4f5a6-b7c8-9012-def0-345678901234',
            'name': 'Docker Hub', 'role': 'widget',
            'path': '/widget/hub', 'icon': '/widget/icon.svg',
            'renderMode': 'iframe', 'defaultSize': {'w': 12, 'h': 6},
        },
        {
            'id': 'docker-settings', 'uuid': 'e4f5a6b7-c8d9-0123-ef01-456789012345',
            'name': 'Docker Settings', 'role': 'widget',
            'path': '/widget/settings', 'icon': '/widget/icon.svg',
            'renderMode': 'iframe', 'defaultSize': {'w': 12, 'h': 6},
        },
    ],
}

WIDGET_JSONLD = json.dumps({
    '@context': 'https://schema.org',
    '@type': 'SoftwareApplication',
    'name': WCP_MANIFEST['name'],
    'softwareVersion': WCP_MANIFEST['version'],
    'description': WCP_MANIFEST['description'],
    'identifier': WCP_MANIFEST['uuid'],
    'applicationCategory': 'WCP Widget',
    'operatingSystem': 'Web',
    'isBasedOn': {
        '@type': 'WebSite',
        'name': 'Widget Context Protocol',
        'url': 'https://widgetcontextprotocol.com',
    },
    'additionalProperty': [
        {'@type': 'PropertyValue', 'name': 'wcpVersion',    'value': WCP_MANIFEST['wcp']},
        {'@type': 'PropertyValue', 'name': 'containerImage','value': WCP_MANIFEST['container']['image']},
        {'@type': 'PropertyValue', 'name': 'containerTag',  'value': WCP_MANIFEST['container']['tag']},
        {'@type': 'PropertyValue', 'name': 'containerPort', 'value': str(WCP_MANIFEST['container']['port'])},
    ],
}, indent=2)

# ── CORS ──────────────────────────────────────────────────────────────────────

@app.after_request
def add_cors(resp):
    resp.headers['Access-Control-Allow-Origin']  = '*'
    resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, DELETE, OPTIONS'
    resp.headers['Access-Control-Allow-Headers'] = (
        'Content-Type, Wcp-Instance-Id, Wcp-Dashboard-Id, Wcp-Version, Wcp-Widget-Id, '
        'Wcp-Orchestration-Id, Wcp-Application-Id'
    )
    return resp

@app.route('/widget/<path:p>', methods=['OPTIONS'])
@app.route('/widget/', methods=['OPTIONS'])
@app.route('/wcp', methods=['OPTIONS'])
def cors_preflight(p=''):
    return Response('', status=204)

# ── WCP boilerplate ───────────────────────────────────────────────────────────

@app.route('/')
def published_spa():
    if os.path.exists(PUBLISHED_PATH):
        with open(PUBLISHED_PATH, 'r', encoding='utf-8') as f:
            return Response(f.read(), mimetype='text/html')
    return Response('Not Found', status=404, mimetype='text/plain')

@app.route('/widget/publish', methods=['POST'])
def publish():
    html = request.get_data(as_text=True)
    if not html:
        return jsonify({'success': False, 'error': 'Empty body'}), 400
    try:
        os.makedirs(os.path.dirname(PUBLISHED_PATH), exist_ok=True)
        with open(PUBLISHED_PATH, 'w', encoding='utf-8') as f:
            f.write(html)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/widget/publish', methods=['DELETE'])
def unpublish():
    try:
        if os.path.exists(PUBLISHED_PATH):
            os.remove(PUBLISHED_PATH)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/wcp')
def container_directory():
    return jsonify({
        'type':    'directory',
        'wcp':     '2.1.0',
        'widgets': [{
            'id':          'docker',
            'uuid':        WCP_MANIFEST['uuid'],
            'name':        WCP_MANIFEST['name'],
            'description': WCP_MANIFEST['description'],
            'icon':        WCP_MANIFEST['icon'],
            'manifest':    '/widget/wcp',
        }]
    })

@app.route('/widget/wcp')
def widget_wcp():
    m = dict(WCP_MANIFEST)
    m['web'] = {'published': os.path.exists(PUBLISHED_PATH)}
    return jsonify(m)

@app.route('/widget/health')
def widget_health():
    return jsonify({'status': 'ok', 'name': WCP_MANIFEST['name']})

# ── Template routes ───────────────────────────────────────────────────────────

def _ctx():
    return dict(
        manifest=WCP_MANIFEST,
        jsonld=WIDGET_JSONLD,
        wcp_instance_id=get_instance_id(),
        wcp_orchestration_id=get_orchestration_id(),
        wcp_application_id=get_application_id(),
    )

@app.route('/widget/')
@app.route('/widget/index.html')
def widget_root():
    return render_template('widget.html', **_ctx())

@app.route('/widget/local')
def widget_local():
    return render_template('local.html', **_ctx())

@app.route('/widget/nas')
def widget_nas():
    return render_template('nas.html', **_ctx())

@app.route('/widget/hub')
def widget_hub():
    return render_template('hub.html', **_ctx())

@app.route('/widget/settings')
def widget_settings():
    s = read_settings()
    return render_template('settings.html', settings=s, **_ctx())

# ── Local Docker API ──────────────────────────────────────────────────────────

def _docker_client():
    return docker_sdk.DockerClient(base_url='unix:///var/run/docker.sock', timeout=8)

@app.route('/widget/api/local/containers')
def api_local_containers():
    cached = get_cache('local:containers')
    if cached:
        return jsonify(cached)
    try:
        client = _docker_client()
        raw = client.containers.list(all=True)
        containers = []
        for c in raw:
            ports = []
            for k, v in (c.ports or {}).items():
                if v:
                    for p in v:
                        ports.append(f"{p['HostPort']}→{k.split('/')[0]}")
            containers.append({
                'id':     c.short_id,
                'name':   c.name,
                'image':  c.image.tags[0] if c.image.tags else c.image.short_id,
                'state':  c.status,
                'status': c.status,
                'ports':  ', '.join(ports),
            })
        result = {'success': True, 'data': {'containers': containers}}
        set_cache('local:containers', result)
        return jsonify(result)
    except Exception as e:
        msg = 'Docker socket unavailable' if 'socket' in str(e).lower() or 'connect' in str(e).lower() else str(e)
        return jsonify({'success': False, 'error': msg})

@app.route('/widget/api/local/images')
def api_local_images():
    cached = get_cache('local:images')
    if cached:
        return jsonify(cached)
    try:
        client = _docker_client()
        raw = client.images.list()
        images = []
        for img in raw:
            tags = img.tags or ['<none>:<none>']
            repo, _, tag = tags[0].partition(':')
            images.append({
                'repo':    repo or '<none>',
                'tag':     tag  or '<none>',
                'id':      img.short_id.replace('sha256:', '')[:12],
                'size':    human_size(img.attrs.get('Size', 0)),
                'created': img.attrs.get('Created', ''),
            })
        images.sort(key=lambda x: x['created'], reverse=True)
        result = {'success': True, 'data': {'images': images}}
        set_cache('local:images', result)
        return jsonify(result)
    except Exception as e:
        msg = 'Docker socket unavailable' if 'socket' in str(e).lower() or 'connect' in str(e).lower() else str(e)
        return jsonify({'success': False, 'error': msg})

@app.route('/widget/api/local/containers/<cid>/<action>', methods=['POST'])
def api_local_action(cid, action):
    if action not in ('start', 'stop', 'restart'):
        return jsonify({'success': False, 'error': 'Invalid action'}), 400
    try:
        client = _docker_client()
        c = client.containers.get(cid)
        getattr(c, action)()
        clear_cache('local:containers')
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ── NAS Docker API (proxies to wcp-docker-agent) ──────────────────────────────

def _nas_headers():
    token = read_settings().get('nas_agent_token', '')
    return {'Authorization': f'Bearer {token}'} if token else {}

def _nas_url(path):
    base = read_settings().get('nas_agent_url', '').rstrip('/')
    return f'{base}{path}' if base else None

@app.route('/widget/api/nas/containers')
def api_nas_containers():
    cached = get_cache('nas:containers')
    if cached:
        return jsonify(cached)
    url = _nas_url('/containers')
    if not url:
        return jsonify({'success': False, 'error': 'NAS agent URL not configured — open Docker Settings'})
    try:
        r = requests.get(url, headers=_nas_headers(), timeout=8)
        result = r.json()
        if result.get('success'):
            # Include NAS hostname so frontend can build clickable port links
            nas_host = urlparse(read_settings().get('nas_agent_url', '')).hostname or 'NAS.local'
            if 'data' not in result:
                result['data'] = {}
            result['data']['nas_host'] = nas_host
            set_cache('nas:containers', result)
        return jsonify(result)
    except requests.exceptions.ConnectionError:
        return jsonify({'success': False, 'error': 'Cannot reach NAS agent — check URL in settings'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/widget/api/nas/images')
def api_nas_images():
    cached = get_cache('nas:images')
    if cached:
        return jsonify(cached)
    url = _nas_url('/images')
    if not url:
        return jsonify({'success': False, 'error': 'NAS agent URL not configured — open Docker Settings'})
    try:
        r = requests.get(url, headers=_nas_headers(), timeout=8)
        result = r.json()
        if result.get('success'):
            set_cache('nas:images', result)
        return jsonify(result)
    except requests.exceptions.ConnectionError:
        return jsonify({'success': False, 'error': 'Cannot reach NAS agent — check URL in settings'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/widget/api/nas/test', methods=['POST'])
def api_nas_test():
    data  = request.get_json(force=True) or {}
    url   = (data.get('url') or '').strip().rstrip('/')
    token = (data.get('token') or '').strip()
    if not url:
        return jsonify({'success': False, 'error': 'NAS agent URL not configured — open Docker Settings'})
    if not token:
        token = read_settings().get('nas_agent_token', '')
    headers = {'Authorization': f'Bearer {token}'} if token else {}
    try:
        r = requests.get(f'{url}/containers', headers=headers, timeout=8)
        result = r.json()
        return jsonify(result)
    except requests.exceptions.ConnectionError:
        return jsonify({'success': False, 'error': 'Cannot reach NAS agent — check URL'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/widget/api/nas/containers/<cid>/<action>', methods=['POST'])
def api_nas_action(cid, action):
    if action not in ('start', 'stop', 'restart'):
        return jsonify({'success': False, 'error': 'Invalid action'}), 400
    url = _nas_url(f'/containers/{cid}/{action}')
    if not url:
        return jsonify({'success': False, 'error': 'NAS agent URL not configured'})
    try:
        r = requests.post(url, headers=_nas_headers(), timeout=15)
        result = r.json()
        if result.get('success'):
            clear_cache('nas:containers')
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ── Docker Hub API ────────────────────────────────────────────────────────────

HUB_BASE = 'https://hub.docker.com/v2'

def _hub_headers():
    pat = read_settings().get('hub_pat', '')
    return {'Authorization': f'Bearer {pat}'} if pat else {}

@app.route('/widget/api/hub/repos')
def api_hub_repos():
    cached = get_cache('hub:repos')
    if cached:
        return jsonify(cached)
    try:
        r = requests.get(
            f'{HUB_BASE}/repositories/penrithbeacon/',
            params={'page_size': 100, 'ordering': 'name'},
            headers=_hub_headers(),
            timeout=10,
        )
        raw = r.json()
        repos = []
        for repo in raw.get('results', []):
            name = repo.get('name', '')
            display = name.replace('wcp-widget-', '').replace('-', ' ').title() if name.startswith('wcp-widget-') else name
            repos.append({
                'name':        name,
                'display':     display,
                'description': repo.get('description', ''),
                'pull_count':  repo.get('pull_count', 0),
                'star_count':  repo.get('star_count', 0),
                'updated':     repo.get('last_updated', ''),
            })
        result = {'success': True, 'data': {'repos': repos}}
        set_cache('hub:repos', result)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/widget/api/hub/repos/<name>/description')
def api_hub_description(name):
    cache_key = f'hub:desc:{name}'
    cached = get_cache(cache_key)
    if cached:
        return jsonify(cached)
    try:
        r = requests.get(
            f'{HUB_BASE}/repositories/penrithbeacon/{name}/',
            headers=_hub_headers(),
            timeout=10,
        )
        raw = r.json()
        result = {'success': True, 'data': {'description': raw.get('full_description', '')}}
        set_cache(cache_key, result)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/widget/api/hub/repos/<name>/tags')
def api_hub_tags(name):
    cache_key = f'hub:tags:{name}'
    cached = get_cache(cache_key)
    if cached:
        return jsonify(cached)
    try:
        r = requests.get(
            f'{HUB_BASE}/repositories/penrithbeacon/{name}/tags/',
            params={'page_size': 50, 'ordering': '-last_updated'},
            headers=_hub_headers(),
            timeout=10,
        )
        raw = r.json()
        tags = []
        for t in raw.get('results', []):
            size = 0
            for img in t.get('images', []):
                size += img.get('size', 0)
            tags.append({
                'name':    t.get('name', ''),
                'size':    human_size(size) if size else '—',
                'updated': t.get('last_updated', ''),
                'digest':  (t.get('images') or [{}])[0].get('digest', '')[:19],
            })
        result = {'success': True, 'data': {'tags': tags}}
        set_cache(cache_key, result)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ── Settings API ──────────────────────────────────────────────────────────────

@app.route('/widget/api/settings', methods=['GET'])
def api_settings_get():
    s = read_settings()
    # Mask token/PAT for GET — show presence only
    masked = {
        'nas_agent_url':   s.get('nas_agent_url', ''),
        'nas_agent_token': '••••••••' if s.get('nas_agent_token') else '',
        'hub_pat':         '••••••••' if s.get('hub_pat') else '',
        'nas_agent_token_set': bool(s.get('nas_agent_token')),
        'hub_pat_set':         bool(s.get('hub_pat')),
    }
    return jsonify({'success': True, 'data': masked})

@app.route('/widget/api/settings', methods=['POST'])
def api_settings_post():
    data = request.get_json(force=True) or {}
    # Don't overwrite masked values
    current = read_settings()
    update = {}
    if 'nas_agent_url' in data:
        update['nas_agent_url'] = data['nas_agent_url'].strip()
    if 'nas_agent_token' in data and data['nas_agent_token'] != '••••••••':
        update['nas_agent_token'] = data['nas_agent_token'].strip()
    if 'hub_pat' in data and data['hub_pat'] != '••••••••':
        update['hub_pat'] = data['hub_pat'].strip()
    merged = write_settings({**current, **update})
    clear_cache()  # force refresh after settings change
    return jsonify({'success': True})

# ── Icon + export ─────────────────────────────────────────────────────────────

ICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">
  <path fill="#f0883e" d="M9.5 3h-3v2h3V3zm1 0v2h3l-1-2h-2zm-5 0H3l-1 2h3V3zm-3 3v1h13V6H2.5zm1.5 2v5h8V8H4zm2 1h1v1H6V9zm2 0h1v1H8V9zm-2 2h1v1H6v-1zm2 0h1v1H8v-1z"/>
</svg>"""

@app.route('/widget/icon.svg')
def widget_icon():
    return Response(ICON_SVG, mimetype='image/svg+xml')

@app.route('/widget/api/guids')
def api_guids():
    return jsonify({
        'uuid': WCP_MANIFEST['uuid'],
        'components': [{'id': c['id'], 'uuid': c['uuid'], 'name': c['name']}
                       for c in WCP_MANIFEST.get('components', [])],
    })

@app.route('/widget/export.wcp')
def export_wcp():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('manifest.json', json.dumps(WCP_MANIFEST, indent=2))
        z.writestr('icon.svg', ICON_SVG)
        z.writestr('DOCKER.md', f"""# {WCP_MANIFEST['name']} — WCP Container

## Pull
```
docker pull penrithbeacon/wcp-widget-docker
```

## Run
```
docker compose up -d
```

Port: 3744 | Spec: https://widgetcontextprotocol.com
""")
    buf.seek(0)
    resp = Response(buf.read(), mimetype='application/zip')
    resp.headers['Content-Disposition'] = 'attachment; filename="docker.wcp"'
    return resp

# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3744, debug=False)
