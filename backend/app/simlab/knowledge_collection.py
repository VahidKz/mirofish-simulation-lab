# Modified 2026-10-29 for the independent Simulation Lab edition; see NOTICE and MODIFICATIONS.md.
"""Passive knowledge capture, deliberately separate from interactive journeys.

Production collection navigates only public document URLs. No clicks, forms,
uploads, login, carts, checkout, mutations or third-party application requests.
"""
import json
import os
from pathlib import Path
import re
from urllib.parse import urljoin, urlparse
from .knowledge import kb_dir,extract_html,digest,now

HOST=os.getenv('SIMLAB_KNOWLEDGE_HOST','')
FORBIDDEN=re.compile(r'(?:^|/)(?:account(?:-settings)?|auth|checkout|communications|confirm-email|edit-profile|favorites|forgot-password|login|messages|my-[^/]*|offer-detail|order-detail|overview|payment-details|register|setup-password|shopping-cart|signin|signup|verify-id|logout|unsubscribe)(?:/|$)|/sell/confirm',re.I)


def public_document(url):
    p=urlparse(url)
    return bool(HOST) and p.scheme=='https' and p.hostname==HOST and not p.username and not p.password and not p.query and not p.fragment and not FORBIDDEN.search(p.path) and (p.path.startswith('/en/') or p.path in {'/robots.txt','/sitemap.xml','/sitemap_index.xml','/core-sitemap.xml'})


def collect_production(max_pages=28, seed_urls=None):
    from playwright.sync_api import sync_playwright
    from .ingestion import public_url
    if not HOST:
        raise ValueError('Set SIMLAB_KNOWLEDGE_HOST to the explicit public host you are authorized to read.')
    public_url('https://'+HOST+'/en/')  # Reject private/loopback destinations before collection.
    records=[];queue=list(seed_urls or ['https://'+HOST+'/en/']);seen=set()
    previous_file=kb_dir()/'production-manifest.json'
    previous=json.loads(previous_file.read_text()) if previous_file.exists() else {}
    output=kb_dir()/'production';output.mkdir(exist_ok=True)
    sources=kb_dir()/'sources';sources.mkdir(exist_ok=True)
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,args=['--disable-quic','--force-webrtc-ip-handling-policy=disable_non_proxied_udp'])
        context=browser.new_context(service_workers='block',accept_downloads=False,viewport={'width':1440,'height':1050})
        blocked=[]
        def route(r):
            req=r.request;p=urlparse(req.url)
            if req.method not in {'GET','HEAD'} or p.scheme!='https' or p.hostname not in {HOST,'cdn.'+HOST} or FORBIDDEN.search(p.path):
                blocked.append({'method':req.method,'host':p.hostname,'reason':'Read-only public-source policy'})
                return r.abort()
            # Only document navigations in our explicit queue are allowed. Static
            # resources and passive public GET data required by rendering remain GET-only.
            if req.is_navigation_request() and not public_document(req.url):
                blocked.append({'method':req.method,'host':p.hostname,'reason':'Non-public document URL'})
                return r.abort()
            r.continue_()
        context.route('**/*',route)
        context.route_web_socket('**/*',lambda ws:ws.on_message(lambda _:None))
        while queue and len(records)<min(35,max_pages):
            url=queue.pop(0)
            if url in seen or not public_document(url):
                continue
            seen.add(url)
            page=context.new_page()
            item={'id':'prod-'+digest(url.encode())[:12],'url':url,'category':'production_public_observation',
                'source_kind':'public_production_render','approval_status':'not_applicable','retrieved_at':now(),
                'verification_scope':'Public visible page content and control presence only; no backend transaction verification.',
                'actions_performed':['HTTP GET navigation','passive render','screenshot'],'forms_submitted':0,'clicks':0}
            try:
                response=page.goto(url,wait_until='domcontentloaded',timeout=25000)
                page.wait_for_timeout(1000)
                item['http_status']=response.status if response else None
                item['final_url']=page.url
                if not response or response.status>=400:
                    item['capture_status']='blocked_or_http_error';item['text']='';item['title']=page.title()
                else:
                    html=page.content()
                    extracted=extract_html(html)
                    item.update(extracted)
                    item['text']=page.locator('body').inner_text()
                    item['content_completeness']='partial_loading_or_placeholder' if any(t in item['text'].lower() for t in ['loading page','loading...','loading…','$tbd']) else 'captured_initial_visible_state'
                    item['html_line_scope']='Captured rendered DOM serialization lines, not production repository lines.'
                    item['sha256']=digest(html.encode())
                    item['capture_status']='captured'
                    item['screenshot']=f'production/{item["id"]}.png'
                    page.screenshot(path=str(output/(item['id']+'.png')),full_page=True,
                        mask=[page.locator('input,textarea,[data-sensitive]')],timeout=8000)
                    links=[]
                    for a in page.locator('a[href]').all():
                        href=a.get_attribute('href') or ''
                        absolute=urljoin(page.url,href)
                        if public_document(absolute):
                            links.append({'label':' '.join(a.inner_text().split())[:160],'url':absolute})
                    item['public_links']=links
                    if url=='https://'+HOST+'/en/':
                        # Public policy/navigation pages first; sample at most 3 PDPs.
                        general=[l['url'] for l in links if '/page/' in l['url'] or re.search(r'/en/(?:shop|collectibles|gemstones|sell|sell-for-cash|pre-authentication|buying|selling|help-center|education|category)(?:/|$)',l['url'])]
                        product=[l['url'] for l in links if l['label'] and len(urlparse(l['url']).path)>45 and '/page/' not in l['url']][:3]
                        queue.extend(dict.fromkeys(general+product))
                    if '/page/' in url and any(k in url for k in ['how-simlab-works','how-to-buy','how-to-sell','help','buying','selling']):
                        queue.extend(l['url'] for l in links if '/page/' in l['url'] and not any(x in l['url'] for x in ['blog','collectibles-guide','collectible-guide','sizing']))
                print(f'Production read {item.get("http_status")} {url}',flush=True)
            except Exception as exc:
                item.update(capture_status='capture_failed',failure_class=type(exc).__name__,text='',title='')
                print(f'Production capture unavailable ({type(exc).__name__}) {url}',flush=True)
            finally:
                page.close()
            (sources/(item['id']+'.json')).write_text(json.dumps(item,ensure_ascii=False,indent=2))
            (sources/(item['id']+'.md')).write_text(f'# {item.get("title",url)}\n\nSource: {url}\nObserved: {item["retrieved_at"]}\nScope: {item["verification_scope"]}\n\n'+item.get('text',''))
            records.append({k:v for k,v in item.items() if k not in {'text','controls','headings','blocks','public_links'}})
        browser.close()
    merged={r['url']:r for r in previous.get('records',[])}
    merged.update({r['url']:r for r in records})
    manifest={'collected_at':now(),'origin':'https://'+HOST,'records':list(merged.values()),'blocked_request_count':previous.get('blocked_request_count',0)+len(blocked),
        'read_only':True,'forms_submitted':0,'clicks':0,'login_attempts':0,'production_transactions':0,
        'remaining_queue':list(dict.fromkeys(u for u in queue if u not in seen)),
        'coverage_note':'Public core pages and a small PDP sample, not every product/language or private account page.'}
    (kb_dir()/'production-manifest.json').write_text(json.dumps(manifest,indent=2))
    return manifest
