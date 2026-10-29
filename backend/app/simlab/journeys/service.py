# Modified 2026-10-29 for the independent Simulation Lab edition; see NOTICE and MODIFICATIONS.md.
"""Process isolation, wall-clock watchdog, persistent results and artifact access."""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

from .. import lab
from ..provider import ROOT, create_budget, data_dir, usage
from .models import JourneyConfig
from .policy import TargetPolicy
from .report import markdown


def folder(run_id):
    return data_dir() / 'journey_evidence' / lab.identifier(run_id)


def load(run_id):
    value = lab.load('journey_runs', run_id)
    if value['status']=='running':
        try:
            os.kill(value['owner_pid'],0)
        except OSError:
            value['status']='interrupted'
            value['error']='Runner stopped before completion; partial evidence was retained.'
    path = folder(run_id)/'events.jsonl'
    if path.exists():
        events=[]
        for line in path.read_text().splitlines():
            try:
                events.append(json.loads(line))
            except ValueError:
                pass  # A concurrent append may not yet be complete.
        value['events']=events
    if not value.get('result') and value.get('events'):
        from .templates import TEMPLATES, roster
        config=JourneyConfig.model_validate(value['configuration'])
        progress=[]
        for index, persona in enumerate(roster(config)):
            own=[e for e in value['events'] if e.get('persona_index')==index]
            if not own:
                continue
            checks={key:{'label':label,'status':'not_observed','evidence':[]} for key,label in TEMPLATES[config.template]['checkpoints']}
            artifacts=[]
            for event in own:
                if event.get('screenshot'):
                    artifacts.append(event['screenshot'])
                for key in event.get('observed',[]):
                    if key in checks:
                        checks[key]['status']='observed'
                        checks[key]['evidence'].append(event['screenshot'])
            progress.append({'index':index,'persona':persona,'status':value['status'],
                'checkpoints':checks,'actions':max((e.get('step',0) for e in own if e['kind']=='checkpoint'),default=0),
                'validation_errors':[{'step':e.get('step'),'message':m,'screenshot':e.get('screenshot')} for e in own for m in e.get('validation_errors',[])],
                'artifacts':artifacts,'trace_type':'sanitized event trace'})
        value['result']={'personas':progress,'browser_failures':[e for e in value['events'] if e['kind'] in {'failure','browser_error','http_error'}],
                         'ux_hypotheses':[],'scope':'Live/partial evidence reconstructed from recorded checkpoints.'}
    value['usage']=usage(run_id)
    return value


def list_runs():
    directory=data_dir()/'journey_runs'
    if not directory.exists():
        return []
    return [load(p.stem) for p in sorted(directory.glob('*.json'),key=lambda p:p.stat().st_mtime,reverse=True)[:50]]


def start(configuration):
    config=JourneyConfig.model_validate(configuration)
    from .knowledge import resolve
    resolve(config.knowledge_references)  # Reject unknown IDs or altered captures before launching.
    policy=TargetPolicy(config.target_id,config.template,config.entry_path or None)
    if config.mode=='scripted' and policy.target['kind']!='fixture' and not config.script:
        raise ValueError('Custom target scripted tests require an explicit script. Use AI exploration to discover controls.')
    cap=int(os.getenv('SIMLAB_MAX_CALLS','24'))
    if config.maximum_calls > cap:
        raise ValueError(f'Model turns exceed the server cap of {cap}.')
    lock=(data_dir()/'journey.lock').open('a')
    try:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
        lock.close()
        raise ValueError('A journey is already running. Browser contexts are processed serially.') from None
    try:
        value=lab.save('journey_runs',{'status':'running','owner_pid':os.getpid(),'created_at':time.time(),
            'configuration':config.model_dump(),'target':{'id':config.target_id,'kind':policy.target['kind'],
            'origin':policy.origin,'scope':'Frontend/sandbox browser evidence only'},'result':None,'events':[]})
        create_budget(value['id'],config.maximum_calls)
        folder(value['id']).mkdir(parents=True,exist_ok=True)
        threading.Thread(target=supervise,args=(value,lock),daemon=True).start()
        return value
    except Exception:
        lock.close()
        raise


def terminate_tree(process):
    # The shared provider creates its own SDK process group; kill descendants
    # explicitly as well as the journey group if the hard watchdog expires.
    import psutil
    try:
        children=psutil.Process(process.pid).children(recursive=True)
        for child in reversed(children):
            try:
                child.kill()
            except psutil.Error:
                pass
    except psutil.Error:
        pass
    process.kill()
    process.wait(timeout=5)


def supervise(value,lock):
    run_id=value['id']
    try:
        env=os.environ.copy()
        env['PYTHONPATH']=str(ROOT/'backend')
        env['SIMLAB_RUN_ID']=run_id
        # Hard wall-clock watchdog includes Chromium startup and trace finalization.
        process=subprocess.Popen([sys.executable,'-m','app.simlab.journeys.worker',run_id],
            cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
        try:
            process.wait(timeout=value['configuration']['timeout_seconds'])
        except subprocess.TimeoutExpired:
            terminate_tree(process)
            value=lab.load('journey_runs',run_id)
            value.update(status='timeout',error='Journey wall-clock watchdog expired; browser and SDK descendants were stopped.')
        else:
            value=lab.load('journey_runs',run_id)
            if value['status']=='running':
                value.update(status='failed',error='Journey worker ended without a completed result. Partial evidence was retained.')
    except Exception:
        value.update(status='failed',error='Local journey supervisor failed. No paid fallback or external write was enabled.')
    finally:
        value['completed_at']=time.time()
        value['usage']=usage(run_id)
        lab.save('journey_runs',value,run_id)
        current=load(run_id)
        (folder(run_id)/'report.md').write_text(markdown(current))
        lock.close()


def artifact(run_id,name):
    if '/' in name or '\\' in name or name.startswith('.') or Path(name).suffix not in {'.png','.zip','.jsonl'}:
        raise ValueError('Invalid artifact name.')
    path=folder(run_id)/name
    if not path.is_file():
        raise FileNotFoundError('Journey artifact not found.')
    return path
