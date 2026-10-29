# Modified 2026-10-29 for the independent Simulation Lab edition; see NOTICE and MODIFICATIONS.md.
"""Run a registered, test-only browser journey without needing the web server."""
import argparse
import json
from pathlib import Path
import time
from app.simlab.journeys import service


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--template',choices=['buyer','seller_offer','merchant'],default='buyer')
    parser.add_argument('--mode',choices=['scripted','ai'],default='scripted')
    parser.add_argument('--target',default='sample')
    parser.add_argument('--entry',default='')
    parser.add_argument('--script',help='JSON action list for a custom scripted target')
    parser.add_argument('--max-calls',type=int,default=4)
    parser.add_argument('--max-steps',type=int,default=16)
    parser.add_argument('--timeout',type=int,default=120)
    parser.add_argument('--personas',type=int,default=1)
    args=parser.parse_args()
    value=service.start({'name':f'SimLab {args.template} {args.mode} journey','template':args.template,
        'target_id':args.target,'entry_path':args.entry,'mode':args.mode,'maximum_calls':args.max_calls,
        'max_steps':args.max_steps,'timeout_seconds':args.timeout,'persona_count':args.personas,
        'script':json.loads(Path(args.script).read_text()) if args.script else []})
    print('Journey:',value['id'],flush=True)
    while True:
        value=service.load(value['id'])
        if value['status']!='running':
            print(json.dumps({'id':value['id'],'status':value['status'],
                'personas':[(p['status'],p['actions']) for p in (value.get('result') or {}).get('personas',[])],
                'budget':value['usage']['budgets'],'events':len(value.get('events',[])),
                'error':value.get('error')}),flush=True)
            print('Evidence:',service.folder(value['id']),flush=True)
            raise SystemExit(0 if value['status']=='completed' else 2)
        time.sleep(.5)


if __name__=='__main__':
    main()
