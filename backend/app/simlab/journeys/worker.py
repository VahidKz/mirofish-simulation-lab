# Modified 2026-10-29 for the independent Simulation Lab edition; see NOTICE and MODIFICATIONS.md.
import json
import os
import sys

from .. import lab
from ..provider import run_scope
from .models import JourneyConfig
from .policy import TargetPolicy, redact
from .runner import run
from .service import folder


def execute(run_id):
    value=lab.load('journey_runs',run_id)
    config=JourneyConfig.model_validate(value['configuration'])
    output=folder(run_id)
    output.mkdir(parents=True,exist_ok=True)
    def emit(event):
        with (output/'events.jsonl').open('a') as stream:
            stream.write(json.dumps(event,ensure_ascii=False)+'\n')
    try:
        policy=TargetPolicy(config.target_id,config.template,config.entry_path or None)
        with run_scope(run_id):
            result=run(config,policy,output,emit)
        value.update(status=result['status'],result=result)
    except Exception as exc:
        value.update(status='failed',error=f'{type(exc).__name__}: journey could not execute safely; no external write was enabled.')
    lab.save('journey_runs',value,run_id)


if __name__=='__main__':
    execute(lab.identifier(sys.argv[1]))
