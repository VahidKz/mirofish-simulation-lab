# Modified 2026-10-29 for the independent Simulation Lab edition; see NOTICE and MODIFICATIONS.md.
from flask import Blueprint, current_app, request, jsonify, Response
from pydantic import ValidationError

from . import lab
from .scenarios import TEMPLATES, LabConfig, estimate
from .provider import usage, codex_status, ProviderError
from .ingestion import ingest_files, ingest_website, to_markdown

bp = Blueprint('simlab', __name__)


@bp.get('/knowledge')
def knowledge_overview():
    from . import knowledge
    return jsonify(success=True,data=knowledge.overview())


@bp.get('/knowledge/search')
def knowledge_search():
    from . import knowledge
    query=request.args.get('q','')[:250]
    matches=knowledge.search(query,include_history=request.args.get('history')=='true')
    terms=set(__import__('re').findall(r'\w+',query.lower()))
    assertions=[f for f in knowledge.facts()['facts'] if terms.intersection(__import__('re').findall(r'\w+',f['claim'].lower()))]
    assertions.sort(key=lambda f:-len(terms.intersection(__import__('re').findall(r'\w+',f['claim'].lower()))))
    return jsonify(success=True,data=matches,facts=assertions[:8],
                   warning='Search matches may disagree. Consult approval status and the conflict register.')


@bp.get('/knowledge/sources/<source_id>')
def knowledge_source(source_id):
    from . import knowledge
    return jsonify(success=True,data=knowledge.source(source_id))


@bp.get('/knowledge/conflicts')
def knowledge_conflicts():
    from . import knowledge
    return jsonify(success=True,data=knowledge.conflicts()['conflicts'])


@bp.get('/knowledge/documents/<key>')
def knowledge_document(key):
    from . import knowledge
    return Response(knowledge.document(key),mimetype='text/markdown')


@bp.post('/knowledge/materials/<key>')
def knowledge_material(key):
    from . import knowledge
    return jsonify(success=True,data=knowledge.make_material(key)),201


@bp.errorhandler(ValueError)
@bp.errorhandler(ValidationError)
def invalid(exc):
    return jsonify(success=False, error=str(exc)), 400


@bp.errorhandler(FileNotFoundError)
def missing(exc):
    return jsonify(success=False, error=str(exc)), 404


@bp.errorhandler(ProviderError)
def unavailable(exc):
    return jsonify(success=False, error=str(exc)), 503


@bp.get('/templates')
def templates():
    import os
    from .case_review import available
    visible={key:value for key,value in TEMPLATES.items() if key!='CASE' or available()}
    return jsonify(success=True, data=visible, defaults=LabConfig().model_dump(),
                   server_cap=int(os.getenv('SIMLAB_MAX_CALLS', '24')))


@bp.get('/status')
def status():
    import os
    value = {'provider': os.getenv('MODEL_PROVIDER', 'codex'),
             'neo4j_ready': bool(current_app.extensions.get('neo4j_storage')),
             'usage': usage(), 'synthetic_only': True}
    if value['provider'] == 'codex':
        try:
            value['codex'] = codex_status()
        except ProviderError as exc:
            value['codex'] = {'authenticated': False, 'error': str(exc)}
    return jsonify(success=True, data=value)


@bp.post('/estimate')
def estimated():
    return jsonify(success=True, data=estimate(LabConfig.model_validate(request.get_json())))


@bp.route('/materials', methods=['GET', 'POST'])
def materials():
    if request.method == 'GET':
        return jsonify(success=True, data=lab.list_items('materials'))
    if request.is_json:
        args = request.get_json()
        if args.get('staging') and not args.get('authorized'):
            raise ValueError('Confirm authorization for staging read-only access before importing.')
        item = ingest_website(args.get('url', ''), max_pages=int(args.get('max_pages', 2)))
    else:
        files = request.files.getlist('files')
        names = request.form.getlist('paths')
        if len(files) > 100 or (names and len(names) != len(files)):
            raise ValueError('Bundle must have at most 100 files with matching paths.')
        names = names or [f.filename for f in files]
        if len(set(names)) != len(names):
            raise ValueError('Duplicate file paths.')
        item = ingest_files({name: f.read() for name, f in zip(names, files)})
    return jsonify(success=True, data=lab.save('materials', item)), 201


@bp.get('/materials/<item_id>/markdown')
def material_markdown(item_id):
    return Response(to_markdown(lab.load('materials', item_id)), mimetype='text/markdown')


@bp.route('/scenarios', methods=['GET', 'POST'])
def scenarios():
    if request.method == 'GET':
        return jsonify(success=True, data=lab.list_items('scenarios'))
    config = LabConfig.model_validate(request.get_json())
    return jsonify(success=True, data=lab.save('scenarios', {'configuration': config.model_dump()})), 201


@bp.route('/runs', methods=['GET', 'POST'])
def runs():
    if request.method == 'GET':
        return jsonify(success=True, data=lab.list_items('runs'))
    result = lab.start(request.get_json(), current_app.extensions.get('neo4j_storage'))
    return jsonify(success=True, data=result), 202


@bp.get('/runs/<run_id>')
def run(run_id):
    result = lab.load('runs', run_id)
    result['usage'] = usage(run_id)
    return jsonify(success=True, data=result)


@bp.get('/runs/<run_id>/export')
def export(run_id):
    value = lab.load('runs', run_id)
    value['usage'] = usage(run_id)
    fmt = request.args.get('format', 'markdown')
    if fmt == 'json':
        import json
        return Response(json.dumps(value, indent=2, ensure_ascii=False), mimetype='application/json',
                        headers={'Content-Disposition': f'attachment; filename="simlab-{run_id}.json"'})
    return Response(lab.report_markdown(value), mimetype='text/markdown',
                    headers={'Content-Disposition': f'attachment; filename="simlab-{run_id}.md"'})


@bp.post('/compare')
def compare():
    ids = request.get_json().get('run_ids', [])
    if not 1 <= len(ids) <= 10:
        raise ValueError('Select 1–10 saved runs.')
    result = []
    for run_id in ids:
        run = lab.load('runs', run_id)
        result.append({'id': run_id, 'status': run['status'], 'configuration': run['configuration'],
                       'variants': [{'label': v['label'], 'observed_events': len(v['events']),
                                     'fee_illustration': v['fee_illustration']} for v in run['variants']],
                       'interpretation': run.get('interpretation')})
    return jsonify(success=True, data=result,
                   limitation='Descriptive synthetic comparison only; no causal or statistical inference.')
