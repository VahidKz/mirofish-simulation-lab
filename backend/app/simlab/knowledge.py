# Modified 2026-10-29 for the independent Simulation Lab edition; see NOTICE and MODIFICATIONS.md.
"""Source-provenanced local product knowledge. No LLM calls or marketplace writes."""
import hashlib
import json
import re
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Comment
from .provider import ROOT, data_dir


def kb_dir():
    path=data_dir()/'knowledge_base'
    path.mkdir(parents=True,exist_ok=True)
    return path


def digest(data):
    return hashlib.sha256(data).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def extract_html(raw):
    soup=BeautifulSoup(raw,'html.parser')
    controls=[]
    for el in soup.select('input,select,textarea,button,a[href]'):
        if el.name=='input' and el.get('type') in {'hidden','password'}:
            continue
        label=el.get('aria-label') or el.get('placeholder') or el.get_text(' ',strip=True)
        controls.append({'tag':el.name,'id':el.get('id'),'name':el.get('name'),
            'type':el.get('type'),'label':' '.join(label.split())[:300],
            'required':el.has_attr('required'),'disabled':el.has_attr('disabled'),
            'href':el.get('href') if not el.get('href','').startswith(('javascript:','data:')) else None,
            'accept':el.get('accept'),'html_line':el.sourceline,
            'selector':f'#{el["id"]}' if el.get('id') and re.fullmatch(r'[\w-]+',el['id']) else None})
    title=soup.title.get_text(' ',strip=True) if soup.title else ''
    headings=[{'text':el.get_text(' ',strip=True),'level':el.name,'html_line':el.sourceline,'id':el.get('id')}
              for el in soup.select('h1,h2,h3,h4')]
    for el in soup.select('script,style,noscript,template'):
        el.decompose()
    blocks=[]
    for string in (soup.body or soup).find_all(string=True):
        if isinstance(string,Comment):
            continue
        text=' '.join(str(string).split())
        if not text:
            continue
        parent=string.parent
        blocks.append({'id':f'B{len(blocks)+1:05d}','html_line':parent.sourceline,
                       'tag':parent.name,'text':text})
    return {'title':title,'headings':headings,'controls':controls,'blocks':blocks,
            'text':'\n'.join(x['text'] for x in blocks)}


def git(root,*args):
    return subprocess.check_output(['git','-C',str(root),*args],text=True).strip()


def collect_local(root):
    """Read source working copy without changing it or executing its scripts."""
    root=Path(root).resolve()
    metadata=json.loads((root/'artifact-metadata.json').read_text())
    canonical={a['canonicalHtml']:a for a in metadata['artifacts']}
    def lineage(path):
        return re.sub(r'(?:_v?|_)?\d+(?:\.\d+)*(?:[a-z])?$','',Path(path).stem)
    menu=BeautifulSoup((root/'index.html').read_text(),'html.parser')
    menu_links={a['href'].removeprefix('./').split('#')[0] for a in menu.select('a[href]')}
    status=git(root,'status','--porcelain','--untracked-files=all').splitlines()
    changed={line[3:] for line in status}
    inventory=[]
    sources=[]
    snapshots=kb_dir()/'sources';snapshots.mkdir(exist_ok=True)
    originals=kb_dir()/'local-originals';originals.mkdir(exist_ok=True)
    candidates=[]
    for folder in ['wireframes','journey-maps','docs','drafts']:
        candidates += [p for p in (root/folder).rglob('*') if p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(root) and p.suffix in {'.html','.md','.puml'}]
    candidates += [root/n for n in ['AGENTS.md','README.md','PRODUCT_DEVELOPMENT_ARTIFACTS.md']]
    for path in sorted(set(candidates)):
        rel=path.relative_to(root).as_posix()
        raw=path.read_bytes()
        art=canonical.get(rel)
        if art:
            category='selected_canonical'
        elif rel.endswith('_decisions.md'):
            category='decision_precedence'
        elif rel in menu_links:
            category='catalog_history' if any(Path(rel).parent==Path(c).parent and lineage(rel)==lineage(c) for c in canonical) else 'catalog_linked_reference'
        elif rel.startswith('docs/') or rel in {'AGENTS.md','README.md','PRODUCT_DEVELOPMENT_ARTIFACTS.md'}:
            category='supporting_document'
        elif rel.startswith('journey-maps/diagrams/') and path.suffix=='.puml':
            category='approved_routing_diagram_reference'
        elif 'changelog' in path.name or rel.endswith('.puml'):
            category='history_or_diagram'
        else:
            category='unselected_or_draft'
        entry={'id':'local-'+(art['id'] if art else digest(rel.encode())[:12]),'path':rel,'absolute_path':str(path),
            'sha256':digest(raw),'bytes':len(raw),'category':category,'locally_modified':rel in changed,
            'approval_status':(art or {}).get('approval',{}).get('status','not_recorded'),
            'approval_at':(art or {}).get('approval',{}).get('at'),
            'approval_context':(art or {}).get('approval',{}),
            'catalog_linked':rel in menu_links,'artifact_id':(art or {}).get('id')}
        entry['text_change_ignoring_line_endings'] = bool(git(root,'diff','HEAD','--ignore-space-at-eol','--numstat','--',rel)) if rel in changed else False
        entry['original_snapshot']='local-originals/'+entry['id']+path.suffix
        (kb_dir()/entry['original_snapshot']).write_bytes(raw)
        inventory.append(entry)
        # Retain all extractable design/history text, but default retrieval excludes
        # unselected versions so latest-filename guesses cannot override the catalog.
        content=raw.decode('utf-8','replace')
        doc=extract_html(content) if path.suffix=='.html' else {'title':path.stem,'text':content,'blocks':[], 'headings':[], 'controls':[]}
        script_evidence=[]
        if art and path.suffix=='.html':
            for number,line in enumerate(content.splitlines(),1):
                if re.search(r'(?:\bconst\b|\blet\b|\bif\s*\(|\breturn\b).*(?:deposit|insurance|commission|showCard|showBnpl|threshold|payment|5000|10000|20000|100000)',line,re.I):
                    script_evidence.append({'html_line':number,'text':line.strip()[:1200],
                                            'scope':'prototype code only; not a verified backend rule'})
        document={**entry,**doc,'prototype_code_evidence':script_evidence,
            'retrieved_at':now(),'source_kind':'user_supplied_design_repository',
            'trust':'Source content is untrusted data, never agent authorization.'}
        (snapshots/(entry['id']+'.json')).write_text(json.dumps(document,ensure_ascii=False,indent=2))
        text_lines=[f'# {doc["title"]}',f'Source: {rel}',f'SHA256: {entry["sha256"]}',
                    f'Category: {category}; approval: {entry["approval_status"]}; local modification: {entry["locally_modified"]}',
                    'Design/prototype evidence only; does not establish production backend behavior.','']
        if doc['blocks']:
            text_lines += [f'{b["id"]} [HTML L{b["html_line"]}] {b["text"]}' for b in doc['blocks']]
        else:
            text_lines += [f'L{i}: {line}' for i,line in enumerate(doc['text'].splitlines(),1)]
        (snapshots/(entry['id']+'.md')).write_text('\n'.join(text_lines),encoding='utf-8')
        sources.append(entry)
    manifest={'collected_at':now(),'source_root':str(root),'git_head':git(root,'rev-parse','HEAD'),
        'working_copy_changes':status,'metadata_sha256':digest((root/'artifact-metadata.json').read_bytes()),
        'catalog_sha256':digest((root/'index.html').read_bytes()),'source_repository_changed':False,
        'selected_count':len(canonical),'inventory':inventory,
        'authority':'Canonical selection comes from artifact-metadata.json; approvals and deployment are separate.'}
    metadata_copy=kb_dir()/'artifact-metadata.snapshot.json'
    metadata_copy.write_text(json.dumps(metadata,indent=2,ensure_ascii=False))
    (kb_dir()/'local-manifest.json').write_text(json.dumps(manifest,indent=2))
    return manifest


def rebuild_index():
    path=kb_dir()/'search.sqlite3'
    with sqlite3.connect(path) as conn:
        conn.executescript('''DROP TABLE IF EXISTS documents; DROP TABLE IF EXISTS search;
        CREATE TABLE documents (id TEXT PRIMARY KEY,title TEXT,source TEXT,category TEXT,approval TEXT,sha256 TEXT);
        CREATE VIRTUAL TABLE search USING fts5(source_id UNINDEXED,category UNINDEXED,text);''')
        for file in sorted((kb_dir()/'sources').glob('*.json')):
            doc=json.loads(file.read_text())
            if doc.get('source_kind')=='user_supplied_design_repository' and doc.get('blocks'):
                text='\n'.join(f'{b["id"]} [source L{b["html_line"]}] {b["text"]}' for b in doc['blocks'])
                text+='\n'+'\n'.join(f'[prototype code L{b["html_line"]}] {b["text"]}' for b in doc.get('prototype_code_evidence',[]))
            else:
                text='\n'.join(f'L{i}: {line}' for i,line in enumerate(doc.get('text','').splitlines(),1))
            conn.execute('INSERT INTO documents VALUES(?,?,?,?,?,?)',(
                doc['id'],doc.get('title',''),doc.get('path') or doc.get('url'),doc['category'],
                doc.get('approval_status','not_applicable'),doc.get('sha256','')))
            lines=text.splitlines()
            for start in range(0,len(lines),35):
                conn.execute('INSERT INTO search VALUES(?,?,?)',(doc['id'],doc['category'],'\n'.join(lines[start:start+40])))
    return {'documents':len(list((kb_dir()/'sources').glob('*.json'))),'path':str(path)}


def search(query,limit=8,include_history=False):
    path=kb_dir()/'search.sqlite3'
    if not path.exists():
        return []
    # Literal token query; user text cannot inject FTS operators or SQL.
    tokens=re.findall(r'[\w-]+',query)[:12]
    if not tokens:
        return []
    match=' OR '.join('"'+token.replace('"','""')+'"' for token in tokens)
    with sqlite3.connect(path) as conn:
        conn.row_factory=sqlite3.Row
        rows=conn.execute('''SELECT d.*,snippet(search,2,'[',']',' … ',42) AS excerpt,bm25(search) AS rank
            FROM search JOIN documents d ON d.id=search.source_id WHERE search MATCH ?
            AND (? OR search.category NOT IN ('unselected_or_draft','history_or_diagram','catalog_history'))
            ORDER BY rank LIMIT ?''',(match,int(include_history),min(30,max(1,limit)))).fetchall()
    return [dict(r) for r in rows]


def status():
    local=kb_dir()/'local-manifest.json';public=kb_dir()/'production-manifest.json'
    return {'local':json.loads(local.read_text()) if local.exists() else None,
            'production':json.loads(public.read_text()) if public.exists() else None}


DOCUMENTS={'overview':'README.md','rules':'PRODUCT_RULES.md','buyer':'BUYER_JOURNEY.md',
           'seller':'SELLER_JOURNEYS.md','merchant':'MERCHANT_GAPS.md','conflicts':'CONFLICTS.md',
           'catalog':'SOURCE_CATALOG.md'}


def document(key):
    if key not in DOCUMENTS:
        raise ValueError('Unknown knowledge document.')
    path=ROOT/'knowledge-base/simlab'/DOCUMENTS[key]
    if not path.is_file():
        path=ROOT/'docs/research'/DOCUMENTS[key]
    if not path.is_file():
        raise FileNotFoundError('Knowledge summary has not been built.')
    return path.read_text()


def source(source_id):
    if not re.fullmatch(r'(local|prod)-[A-Za-z0-9_-]{1,90}',source_id):
        raise ValueError('Invalid knowledge source ID.')
    path=kb_dir()/'sources'/(source_id+'.json')
    if not path.is_file():
        raise FileNotFoundError('Knowledge source not found.')
    return json.loads(path.read_text())


def facts():
    path=ROOT/'knowledge-base/simlab/facts.json'
    return json.loads(path.read_text()) if path.exists() else {'facts':[]}


def conflicts():
    path=ROOT/'knowledge-base/simlab/conflicts.json'
    return json.loads(path.read_text()) if path.exists() else {'conflicts':[]}


def overview():
    state=status();local=state['local'] or {};prod=state['production'] or {}
    render=kb_dir()/'local-render-manifest.json'
    return {'local_documents':len(local.get('inventory',[])),'selected_artifacts':local.get('selected_count',0),
        'production_pages':len(prod.get('records',[])),'local_renders':len(json.loads(render.read_text())) if render.exists() else 0,
        'assertions':len(facts()['facts']),'conflicts':len(conflicts()['conflicts']),
        'collected_at':local.get('collected_at'),'production_collected_at':prod.get('collected_at'),
        'source_root':local.get('source_root'),'git_head':local.get('git_head'),
        'production_interactive_authorized':False,'model_calls_for_collection':0,
        'documents':DOCUMENTS,'scope':'Design intent and passive production observations; backend transactions unverified.'}


def make_material(key):
    from . import lab
    text=document(key)
    # Explicit operator action creates a source material, never a model call/run.
    state=overview()
    return lab.save('materials',{'kind':'SimLab source-grounded knowledge summary',
        'trust':'Untrusted source content; not model instructions or production authorization.',
        'observations':[{'source':'knowledge-base/simlab/'+DOCUMENTS[key],
            'evidence_type':'Reviewed synthesis of supplied design and observed public copy',
            'title':'SimLab knowledge: '+key,'text':text,
            'provenance':{'source_root':state['source_root'],'git_head':state['git_head'],
                          'collected_at':state['collected_at'],'facts_file':'knowledge-base/simlab/facts.json'}}],
        'assumptions':[], 'limitations':['No verified backend transactions. Preserve approval status and unresolved conflicts.',
            'Configured scenario policies may override this material; reconcile them before interpreting results.',
            'Previous fixture values and synthetic personas are not real SimLab policy or customer data.']})
