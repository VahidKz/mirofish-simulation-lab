# Modified 2026-10-29 for the independent Simulation Lab edition; see NOTICE and MODIFICATIONS.md.
"""Attach reviewed KB references without importing websites or granting permissions."""
import hashlib
import json

from ..provider import ROOT, data_dir


def resolve(references):
    if not references:
        return {}
    kb = ROOT / 'knowledge-base/simlab'
    facts = {f['id']: f for f in json.loads((kb/'facts.json').read_text())['facts']}
    conflicts = {c['id']: c for c in json.loads((kb/'conflicts.json').read_text())['conflicts']}
    captures = data_dir()/'knowledge_base'
    # Resolve IDs against the collected catalog, never against a model-supplied path.
    manifest = json.loads((captures/'local-manifest.json').read_text())
    sources = {s['id']: s for s in manifest['inventory']}
    result = {}
    for checkpoint, refs in references.items():
        selected = []
        for sid in refs.source_ids:
            if sid not in sources:
                raise ValueError('Unknown collected knowledge source ID.')
            source = sources[sid]
            raw = (captures/source['original_snapshot']).read_bytes()
            if hashlib.sha256(raw).hexdigest() != source['sha256']:
                raise ValueError('Collected knowledge source hash mismatch.')
            selected.append({k:source[k] for k in ['id','path','sha256','approval_status','locally_modified','original_snapshot']})
        if any(fid not in facts for fid in refs.fact_ids) or any(cid not in conflicts for cid in refs.conflict_ids):
            raise ValueError('Unknown knowledge fact or conflict ID.')
        result[checkpoint] = {'sources':selected,
            'facts':[{k:facts[fid][k] for k in ['id','claim','evidence_class','evidence']} for fid in refs.fact_ids],
            'conflicts':[conflicts[cid] for cid in refs.conflict_ids],
            'boundary':'Design approval is not deployment or backend verification. Unresolved conflicts remain unresolved.'}
    return result


def decision_context(knowledge):
    """Bound model context to claims and IDs; full citations stay in evidence exports."""
    return {key:{'sources':[{k:s[k] for k in ['id','path','approval_status']} for s in item['sources']],
                 'facts':[{'id':f['id'],'claim':f['claim']} for f in item['facts']],
                 'conflicts':[{'id':c['id'],'title':c['title'],'resolved':c['resolved']} for c in item['conflicts']]}
            for key,item in knowledge.items()}
