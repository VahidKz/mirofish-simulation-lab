# Modified 2026-10-29 for the independent Simulation Lab edition; see NOTICE and MODIFICATIONS.md.
import argparse
import json
from app.simlab import knowledge


def main():
    parser=argparse.ArgumentParser(description='Source-grounded SimLab knowledge collection; no inference calls.')
    sub=parser.add_subparsers(dest='command',required=True)
    local=sub.add_parser('collect-local');local.add_argument('source_root')
    sub.add_parser('index')
    live=sub.add_parser('collect-production');live.add_argument('--max-pages',type=int,default=28);live.add_argument('--url',action='append')
    query=sub.add_parser('search');query.add_argument('query');query.add_argument('--history',action='store_true')
    sub.add_parser('status')
    args=parser.parse_args()
    if args.command=='collect-local':
        result=knowledge.collect_local(args.source_root)
        print(json.dumps({'selected':result['selected_count'],'files':len(result['inventory']),
                          'git_head':result['git_head'],'source_changed':result['source_repository_changed']}))
    elif args.command=='collect-production':
        from app.simlab.knowledge_collection import collect_production
        result=collect_production(args.max_pages,seed_urls=args.url)
        print(json.dumps({'pages':len(result['records']),'clicks':result['clicks'],'forms':result['forms_submitted']}))
    elif args.command=='index':print(json.dumps(knowledge.rebuild_index()))
    elif args.command=='search':print(json.dumps(knowledge.search(args.query,include_history=args.history),indent=2))
    else:
        result=knowledge.status()
        print(json.dumps({'local_collected':(result['local'] or {}).get('collected_at'),
                          'local_files':len((result['local'] or {}).get('inventory',[])),
                          'production':result['production']},indent=2))


if __name__=='__main__':main()
