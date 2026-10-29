# Modified 2026-10-29 for the independent Simulation Lab edition; see NOTICE and MODIFICATIONS.md.
import fcntl
import os
import subprocess
from types import SimpleNamespace
import pytest

from app.simlab import lab
from app.simlab.provider import data_dir,create_budget
from app.simlab.journeys import service
from app.simlab.journeys.models import JourneyConfig


def test_cross_process_lock_prevents_another_browser_run():
    with (data_dir()/'journey.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        with pytest.raises(ValueError,match='already running'):
            service.start({})
    assert service.list_runs()==[]


def test_hard_watchdog_stops_worker_and_preserves_partial_evidence(monkeypatch):
    value=lab.save('journey_runs',{'owner_pid':os.getpid(),'status':'running','events':[],
        'configuration':JourneyConfig(timeout_seconds=10).model_dump(),'result':None})
    create_budget(value['id'],4)
    directory=service.folder(value['id']);directory.mkdir(parents=True)
    (directory/'events.jsonl').write_text('{"kind":"checkpoint","persona_index":0,"step":0,"observed":["plp"],"screenshot":"persona-0-step-00.png"}\n')
    timeouts=[];terminated=[];closed=[]
    class Process:
        def wait(self,timeout):
            timeouts.append(timeout)
            raise subprocess.TimeoutExpired('test-worker',timeout)
    monkeypatch.setattr(service.subprocess,'Popen',lambda *_a,**_k:Process())
    monkeypatch.setattr(service,'terminate_tree',lambda p:terminated.append(p))
    service.supervise(value,SimpleNamespace(close=lambda:closed.append(True)))
    actual=service.load(value['id'])
    assert actual['status']=='timeout'
    assert timeouts==[10] and len(terminated)==1 and closed==[True]
    assert actual['result']['personas'][0]['checkpoints']['plp']['status']=='observed'
    assert (directory/'report.md').exists()
    assert actual['usage']['budgets'][0]['attempted']==0
