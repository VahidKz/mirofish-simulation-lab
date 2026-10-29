# Modified 2026-10-29 for the independent Simulation Lab edition; see NOTICE and MODIFICATIONS.md.
"""Real, opt-in subscription smoke run. Default is one treatment / 3 agents.

Run from repository root: PYTHONPATH=backend .venv/bin/python backend/scripts/simlab_smoke.py
"""
import argparse
import json
from pathlib import Path
import time

from app import create_app
from app.simlab import lab
from app.simlab.ingestion import ingest_folder


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--compare', action='store_true', help='Run all three commission treatments within a 24-turn cap')
    parser.add_argument('--wireframe', default='examples/simlab-wireframe')
    args = parser.parse_args()
    app = create_app()
    material = lab.save('materials', ingest_folder(Path(args.wireframe)))
    print('Imported material:', material['id'], flush=True)
    config = {'name': 'SimLab commission comparison' if args.compare else 'SimLab first wireframe experiment',
              'template': 'A', 'variant_indices': [0, 1, 2] if args.compare else [0],
              'material_ids': [material['id']], 'maximum_calls': 24}
    value = lab.start(config, app.extensions['neo4j_storage'])
    print('Run:', value['id'], flush=True)
    previous = None
    while True:
        current = lab.load('runs', value['id'])
        if current['stage'] != previous:
            print('Stage:', current['stage'], flush=True)
            previous = current['stage']
        if current['status'] != 'running':
            print(json.dumps({'id': current['id'], 'status': current['status'],
                'error': current.get('error'), 'graph_nodes': len(current.get('graph', {}).get('nodes', [])),
                'events': len(current['events']), 'variants': len(current['variants']),
                'budgets': current.get('usage', {}).get('budgets', [])}), flush=True)
            if current['status'] != 'completed':
                raise SystemExit(1)
            break
        time.sleep(2)


if __name__ == '__main__':
    main()
