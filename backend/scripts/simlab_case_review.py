# Modified 2026-10-29 for the independent Simulation Lab edition; see NOTICE and MODIFICATIONS.md.
"""Opt-in bounded discussion of an explicitly configured private JSON case."""
import os
import time
from app import create_app
from app.simlab import lab
from app.simlab.case_review import evidence_packet


def main():
    evidence_packet()  # Validate the private input before constructing services or spending a turn.
    os.environ['MODEL_PROVIDER']='codex'
    os.environ['SIMLAB_MODEL_RETRIES']='0'
    app=create_app()
    value=lab.start({'template':'CASE','name':'Private source-grounded case review','maximum_calls':24},
                    app.extensions.get('neo4j_storage'))
    print('Run:',value['id'],flush=True)
    previous=None
    while True:
        current=lab.load('runs',value['id'])
        if current['stage']!=previous:
            previous=current['stage'];print('Stage:',previous,flush=True)
        if current['status']!='running':
            print('Result:',current['status'],flush=True)
            return 0 if current['status']=='completed' else 2
        time.sleep(1)


if __name__=='__main__':
    raise SystemExit(main())
