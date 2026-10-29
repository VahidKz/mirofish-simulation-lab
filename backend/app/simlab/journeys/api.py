# Modified 2026-10-29 for the independent Simulation Lab edition; see NOTICE and MODIFICATIONS.md.
import json
from flask import Blueprint, request, jsonify, Response, send_file
from pydantic import ValidationError
from ..provider import usage
from .models import JourneyConfig
from .policy import targets, save_bundle, MAX_FILE
from .templates import public_templates
from . import service
from .report import markdown

bp=Blueprint('simlab_journeys',__name__)


@bp.errorhandler(ValueError)
@bp.errorhandler(ValidationError)
def invalid(exc):
    return jsonify(success=False,error=str(exc)),400


@bp.errorhandler(FileNotFoundError)
def missing(exc):
    return jsonify(success=False,error=str(exc)),404


@bp.get('/templates')
def templates():
    public_targets=[{k:v for k,v in t.items() if k in {'id','name','kind','origin','login_authorized'}} for t in targets().values()]
    return jsonify(success=True,data=public_templates(),targets=public_targets,defaults=JourneyConfig().model_dump())


@bp.post('/bundles')
def bundles():
    files=request.files.getlist('files')
    paths=request.form.getlist('paths') or [f.filename for f in files]
    if not 1<=len(files)<=100 or len(paths)!=len(files) or len(set(paths))!=len(paths):
        raise ValueError('Supply 1–100 files with unique matching paths.')
    data={name:file.read(MAX_FILE+1) for name,file in zip(paths,files)}
    return jsonify(success=True,data=save_bundle(data)),201


@bp.route('/runs',methods=['GET','POST'])
def runs():
    if request.method=='GET':
        return jsonify(success=True,data=service.list_runs())
    return jsonify(success=True,data=service.start(request.get_json())),202


@bp.get('/runs/<run_id>')
def result(run_id):
    return jsonify(success=True,data=service.load(run_id))


@bp.get('/runs/<run_id>/export')
def export(run_id):
    value=service.load(run_id)
    if request.args.get('format')=='json':
        return Response(json.dumps(value,indent=2),mimetype='application/json',
            headers={'Content-Disposition':f'attachment; filename="journey-{value["id"]}.json"'})
    return Response(markdown(value),mimetype='text/markdown',
        headers={'Content-Disposition':f'attachment; filename="journey-{value["id"]}.md"'})


@bp.get('/runs/<run_id>/artifacts/<name>')
def artifact(run_id,name):
    path=service.artifact(run_id,name)
    return send_file(path,as_attachment=path.suffix!='.png',conditional=True)
