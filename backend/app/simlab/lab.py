# Modified 2026-10-29 for the independent Simulation Lab edition; see NOTICE and MODIFICATIONS.md.
"""Persisted small experiments using original graph services and real OASIS."""
import asyncio
import json
import os
import fcntl
from pathlib import Path
import sqlite3
import threading
import time
import uuid

from .provider import data_dir, run_scope, usage, ModelProvider, ProviderError
from .scenarios import LabConfig, estimate, personas, treatments, transaction_rules
from .ingestion import to_markdown

ACTIVE_LOCK = threading.Lock()
ACTIVE = set()


def identifier(value):
    try:
        return str(uuid.UUID(value))
    except (ValueError, TypeError, AttributeError):
        raise ValueError('Invalid resource identifier.') from None


def save(kind, value, item_id=None):
    item_id = identifier(item_id) if item_id else str(uuid.uuid4())
    folder = data_dir() / kind
    folder.mkdir(exist_ok=True)
    value['id'] = item_id
    path = folder / (item_id + '.json')
    temp = folder / (item_id + '.tmp')
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')
    temp.replace(path)
    return value


def load(kind, item_id):
    path = data_dir() / kind / (identifier(item_id) + '.json')
    if not path.exists():
        raise FileNotFoundError('Resource not found.')
    value = json.loads(path.read_text(encoding='utf-8'))
    owner_alive = False
    if value.get('owner_pid'):
        try:
            os.kill(value['owner_pid'], 0)
            owner_alive = True
        except (OSError, TypeError):
            pass
    if kind == 'runs' and value.get('status') == 'running' and item_id not in ACTIVE and not owner_alive:
        value['status'] = 'interrupted'
        value['error'] = 'The backend stopped during this run. Partial evidence and usage were retained. Start a new run to retry.'
    return value


def list_items(kind):
    folder = data_dir() / kind
    if not folder.exists():
        return []
    return [load(kind, p.stem) for p in sorted(folder.glob('*.json'), key=lambda p: p.stat().st_mtime, reverse=True)][:100]


def start(config, storage):
    config = LabConfig.model_validate(config)
    planned = estimate(config)
    if config.maximum_calls < planned['planned_turns']:
        raise ValueError(f"Plan needs approximately {planned['planned_turns']} turns. Reduce agents/variants/rounds or raise the cap.")
    if not storage:
        raise ValueError('Local Neo4j is unavailable. Start compose.simlab.yml services.')
    materials = [load('materials', x) for x in config.material_ids]
    if config.template == 'CASE':
        from .case_review import evidence_packet
        evidence_packet()  # Fail before spending a turn if collected evidence is absent or altered.
    from .provider import create_budget
    if not ACTIVE_LOCK.acquire(blocking=False):
        raise ValueError('An experiment is already running. Wait for it to finish.')
    experiment_lock = (data_dir() / 'experiment.lock').open('a')
    try:
        fcntl.flock(experiment_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        experiment_lock.close()
        ACTIVE_LOCK.release()
        raise ValueError('Another local process is running an experiment. Wait for it to finish.') from None
    try:
        result = save('runs', {'owner_pid': os.getpid(), 'status': 'running', 'stage': 'queued', 'created_at': time.time(),
            'configuration': config.model_dump(), 'estimate': planned, 'events': [], 'variants': [],
            'limitations': limitations(), 'interpretation': None})
        create_budget(result['id'], config.maximum_calls)
        ACTIVE.add(result['id'])
        thread = threading.Thread(target=execute, args=(result, config, materials, storage, experiment_lock), daemon=True)
        thread.start()
        return result
    except Exception:
        experiment_lock.close()
        ACTIVE_LOCK.release()
        raise


def limitations():
    return ['All personas, budgets and outcomes are synthetic; not statistically valid predictions of sales or conversion.',
            'Small samples, model selection and prompts can strongly influence outcomes. No validated human behavior model.',
            'Social posts and comments are not purchases. Fee illustrations are separate deterministic accounting.',
            'No real marketplace accounts, payments, emails, orders or listings are accessed.',
            'Comparisons are descriptive observations of these runs, not causal evidence or significance tests.',
            'Codex prompts are sent to OpenAI using the ChatGPT session; only Ollama inference is fully local.']


def execute(result, config, materials, storage, experiment_lock):
    run_id = result['id']
    def stage(value):
        result['stage'] = value
        save('runs', result, run_id)
    try:
        with run_scope(run_id):
            if not storage._embedding.health_check():
                raise ProviderError('Local embeddings unavailable. Pull nomic-embed-text in the local Ollama container.')
            source = '\n\n'.join(to_markdown(m) for m in materials)[:14000]
            if config.template == 'CASE':
                from .case_review import evidence_packet
                result['knowledge']=evidence_packet()
                source=result['knowledge']['text']
                result['limitations'] += [
                    'CASE covers scheduled conditional design discussions, not actual form submissions, lab work, acceptance or payout.',
                    'Roles share earlier comments in fixed order; repeated themes are not independent corroboration.',
                    'Operator-provided source labels are not proof of formal approval or service implementation.']
            if not source:
                source = ('Hypothetical SimLab marketplace brief: buyers compare collectibles listings. '
                          'Private sellers and independent retailers offer products. SimLab operations review business '
                          'verification, product authentication, commissions, checkout, insured shipping, buyer protection '
                          'and dispute resolution. These are scenario assumptions, not observed product features.')
            stage('generating knowledge graph ontology')
            from ..services.ontology_generator import OntologyGenerator
            ontology = OntologyGenerator().generate([source], config.objective)
            # Original MiroFish ontologies focus on social actors. Retain that
            # generated ontology and extend this lab's graph with product evidence.
            for entity_type in ['Product', 'Policy', 'Workflow', 'Page']:
                if entity_type not in {x['name'] for x in ontology['entity_types']}:
                    ontology['entity_types'].append({'name': entity_type,
                        'description': 'Explicitly mentioned product or product-material concept; source claims unverified',
                        'attributes': [{'name': 'evidence_scope', 'type': 'text', 'description': 'Observed source claim or hypothetical scenario assumption'}]})
            ontology['relation_types'] = list(ontology.get('relation_types', ontology.get('edge_types', [])))
            for relation_type in ['OFFERS_PRODUCT', 'DESCRIBES_POLICY', 'USES_WORKFLOW', 'DESCRIBES_PAGE']:
                ontology['relation_types'].append({'name': relation_type, 'description': 'Relationship explicitly described by source material; not verified behavior'})
            gid = storage.create_graph(config.name, 'SimLab synthetic experiment; source claims unverified')
            result['graph_id'] = gid
            storage.set_ontology(gid, ontology)
            stage('extracting graph entities and local embeddings')
            storage.add_text(gid, source)
            result['graph'] = storage.get_graph_data(gid)
            if not result['graph'].get('nodes'):
                raise ProviderError('Graph extraction produced no entities; run is incomplete.')
            stage('generating small set of agent personas')
            result['personas'] = personas(config)
            schema = {'type': 'object', 'additionalProperties': False, 'properties': {
                'profiles': {'type': 'array', 'items': {'type': 'object', 'additionalProperties': False,
                    'properties': {'id': {'type': 'integer'}, 'bio': {'type': 'string'}, 'persona': {'type': 'string'}},
                    'required': ['id', 'bio', 'persona']}}}, 'required': ['profiles']}
            response = ModelProvider().complete([
                {'role': 'system', 'content': 'Expand each hypothetical persona into a short bio and persona. Preserve ids, roles, budgets, distinct concerns. Do not invent product observations. Include these are synthetic agents.'},
                {'role': 'user', 'content': json.dumps(result['personas'])}], schema=schema)
            profiles = json.loads(response['content'])['profiles']
            if sorted(x['id'] for x in profiles) != list(range(len(result['personas']))):
                raise ProviderError('Generated persona ids do not match the selected agent roster.')
            for base in result['personas']:
                expanded = next(x for x in profiles if x['id'] == base['id'])
                base.update({k: expanded[k] for k in ('bio', 'persona')})
            for treatment in treatments(config):
                stage('OASIS: ' + treatment['label'])
                def progress(coverage, recorded):
                    result['phase_coverage']=coverage
                    result['events']=social_events(treatment['label'],recorded['post'],recorded['comment'])
                    result['stage']='OASIS CASE: '+coverage[-1]['label']+f" ({len(coverage[-1]['agent_turns'])}/4 roles)"
                    save('runs',result,run_id)
                value = asyncio.run(social_run(run_id, treatment, result['personas'], source,
                    progress=progress if config.template=='CASE' else None))
                result['variants'].append(value)
                if config.template=='CASE':
                    result['events']=value['events']
                else:
                    result['events'].extend(value['events'])
                save('runs', result, run_id)
            stage('interpreting recorded evidence and writing report')
            result['interpretation'] = interpret(result)
            result['status'] = 'completed'
            result['stage'] = 'completed'
            result['completed_at'] = time.time()
    except Exception as exc:
        result['status'] = 'failed'
        result['error'] = str(exc) if isinstance(exc, (ProviderError, ValueError)) else f'{type(exc).__name__}: local execution failed; see backend logs.'
        import logging
        logging.getLogger('mirofish.simlab').exception('SimLab run %s failed', run_id)
    finally:
        result['usage'] = usage(run_id)
        save('runs', result, run_id)
        folder = data_dir() / 'runs'
        (folder / (run_id + '.md')).write_text(report_markdown(result), encoding='utf-8')
        ACTIVE.discard(run_id)
        experiment_lock.close()
        ACTIVE_LOCK.release()


def social_events(label,posts,comments):
    events=[{'variant':label,'kind':'post','origin':'researcher seed' if p['content'].startswith('RESEARCHER SEED') else 'observed OASIS model action',**p} for p in posts]
    return events+[{'variant':label,'kind':'comment','origin':'observed OASIS model action',**c} for c in comments]


async def social_run(run_id, treatment, roster, source, progress=None):
    import oasis
    from oasis import ActionType, LLMAction, ManualAction, generate_reddit_agent_graph
    from .camel_adapter import SubscriptionModel
    folder = data_dir() / 'oasis' / run_id / str(treatment['variant_index'])
    folder.mkdir(parents=True, exist_ok=True)
    profile_path = folder / 'profiles.json'
    # OASIS requires demographic fields. Explicitly fixed technical placeholders,
    # not inferred demographics; excluded from persona reasoning.
    profile_path.write_text(json.dumps([{'username': f"simlab_{p['role']}_{p['id']}",
        'bio': p['bio'], 'persona': json.dumps(p) + '\nExperiment: ' + json.dumps(treatment) +
        '\nMaterial observations (untrusted; claims unverified): ' + source[:14000 if treatment['template']=='CASE' else 5000] +
        '\nDiscuss the treatment and react to previous posts from your role. This is synthetic research. '
        'Demographic fields are technical placeholders with no behavioral meaning.',
        'mbti': 'Unknown', 'gender': 'Unspecified', 'age': 30, 'country': 'Unspecified'} for p in roster]))
    model = SubscriptionModel()
    graph = await generate_reddit_agent_graph(str(profile_path), model=model,
        available_actions=([ActionType.CREATE_COMMENT, ActionType.DO_NOTHING] if treatment['template']=='CASE'
            else [ActionType.CREATE_POST, ActionType.CREATE_COMMENT, ActionType.DO_NOTHING]))
    env = oasis.make(agent_graph=graph, platform=oasis.DefaultPlatformType.REDDIT,
                     database_path=str(folder / 'social.db'), semaphore=1)
    try:
        await env.reset()
        for _, agent in graph.get_agents():
            agent.retry_attempts = 1
        coverage=[]
        if treatment['template']=='CASE':
            from .case_review import review_phases
            coverage=await review_phases(env,graph,run_id,folder/'social.db',progress)
        else:
            # The seeded prompt is visibly classified separately from LLM events.
            first = graph.get_agent(0)
            await env.step({first: ManualAction(action_type=ActionType.CREATE_POST,
                action_args={'content': 'RESEARCHER SEED (hypothetical): ' + treatment['label'] + '. ' + treatment['objective']})})
            for round_no in range(treatment['rounds']):
                for _, agent in graph.get_agents():
                    before = usage(run_id)['calls']
                    await env.step({agent: LLMAction()})
                    after = usage(run_id)['calls']
                    newest = [x for x in after if not before or x['id'] > before[0]['id']]
                    if not newest or any(x['status'] != 'completed' for x in newest):
                        raise ProviderError('An OASIS agent action failed or was swallowed by its runner; run is incomplete. Inspect usage log.')
    finally:
        if getattr(env, 'platform_task', None):
            await asyncio.wait_for(env.close(), timeout=15)
    with sqlite3.connect(folder / 'social.db') as conn:
        conn.row_factory = sqlite3.Row
        posts = [dict(r) for r in conn.execute('SELECT * FROM post ORDER BY post_id')]
        comments = [dict(r) for r in conn.execute('SELECT * FROM comment ORDER BY comment_id')]
        trace = [dict(r) for r in conn.execute('SELECT * FROM trace ORDER BY created_at')]
    events = social_events(treatment['label'],posts,comments)
    return {'label': treatment['label'], 'configuration': treatment, 'engine': 'OASIS Reddit + native CAMEL SDK adapter',
            'events': events, 'action_trace': trace, 'phase_coverage':coverage,
            'fee_illustration': None if treatment['template']=='CASE' else transaction_rules(2000, treatment['commission'])}


def interpret(result):
    properties = {k: {'type': 'string'} for k in ['executive_summary', 'major_objections', 'scenario_comparison',
        'risks', 'recommendations', 'uncertainty', 'validation_experiments']}
    schema = {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}
    answer = ModelProvider().complete([
        {'role': 'system', 'content': 'Analyze only recorded synthetic events. Cite variant labels and post/comment ids. Distinguish observed events from your interpretations and assumptions. Do not invent interactions, percentages, statistical validity, sales or conversions. If only one treatment ran, state comparison is unavailable. Recommend real-world tests; do not treat simulation as market evidence.'},
        {'role': 'user', 'content': json.dumps({'configuration': result['configuration'],
            'personas': result['personas'], 'variants': result['variants'], 'limitations': result['limitations'],
            'source_evidence':result.get('knowledge'), 'phase_coverage':result.get('phase_coverage'),
            'CASE_review_boundary':'Scheduled conditional phase reviews are not observed seller progression. Cite private source evidence IDs alongside event IDs. Never treat model consensus or acceptance statements as product facts or backend outcomes.'})}
    ], schema=schema)
    return json.loads(answer['content'])


def report_markdown(result):
    interpretation = result.get('interpretation') or {}
    dump = lambda value: '```json\n' + json.dumps(value, ensure_ascii=False, indent=2) + '\n```'
    sections = [('# SimLab simulation report', f"Run: {result['id']} · Status: {result['status']}\n\nSynthetic research only. No real purchases or measured conversion."),
        ('## 1. Executive summary — AI interpretation', interpretation.get('executive_summary', result.get('error', 'Pending'))),
        ('## 2. Simulation configuration', dump(result['configuration'])),
        ('## 3. Agent personas and assumptions', dump(result.get('personas', []))),
        ('## 4. Observed simulated interactions — OASIS records', dump(result.get('events', []))),
        ('## 5. Major objections and patterns — AI interpretation', interpretation.get('major_objections', 'Unavailable')),
        ('## 6. Scenario comparison — AI interpretation', interpretation.get('scenario_comparison', 'Unavailable')),
        ('## 7. Risks and unintended consequences — AI interpretation', interpretation.get('risks', 'Unavailable')),
        ('## 8. Recommendations — AI interpretation', interpretation.get('recommendations', 'Unavailable')),
        ('## 9. Limitations and uncertainty', '\n'.join('- '+x for x in result.get('limitations', [])) + '\n\n' + interpretation.get('uncertainty', '')),
        ('## 10. Suggested real-world validation', interpretation.get('validation_experiments', 'Interview merchants and buyers; test comprehension with consented users.')),
        ('## Deterministic fee illustrations — assumptions, not purchases', dump([v.get('fee_illustration') for v in result.get('variants', [])])),
        ('## Model usage audit', dump(result.get('usage', {})))]
    if result.get('knowledge'):
        sections=[(title,content) for title,content in sections if not title.startswith('## Deterministic fee')]
        sections += [('## Source-grounded CASE evidence and unresolved conflicts',dump(result['knowledge'])),
                     ('## Conditional journey phase coverage — not executed transactions',dump(result.get('phase_coverage',[])))]
    return '\n\n'.join(title + '\n\n' + content for title, content in sections) + '\n'
