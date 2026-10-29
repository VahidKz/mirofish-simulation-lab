# Modified 2026-10-29 for the independent Simulation Lab edition; see NOTICE and MODIFICATIONS.md.
import json
import os


def markdown(value):
    artifact_base=f"http://localhost:{os.getenv('FLASK_PORT','5001')}/api/simlab/journeys/runs/{value['id']}/artifacts"
    lines = ['# SimLab journey evidence report', f"Run: {value['id']} · Status: {value['status']}",
        '**Synthetic test only. Journey completion is not real customer conversion.**',
        '## Scope and configuration', '```json\n'+json.dumps(value['configuration'],indent=2)+'\n```',
        'Only rendered checkpoints and permitted browser actions are observed. Writes are blocked or mocked. '
        'An observed checkpoint means its configured locator was visible; it does not prove a transition or completion of all steps. '
        'Frontend completion does not verify authentication, payment, verification, approval, emails or fulfillment backends.',
        '## Persona checkpoint evidence']
    result = value.get('result') or {}
    if result.get('knowledge'):
        lines += ['## Knowledge sources and unresolved rules',
            'Attached references describe design intent or previously observed presentation. They do not establish a working backend. '
            'Unknown checkpoints remain missing even when a design document describes them.',
            '```json\n'+json.dumps(result['knowledge'],indent=2,ensure_ascii=False)+'\n```']
    for persona in result.get('personas', []):
        lines += [f"### {persona['persona']['name']} · {persona['status']}",
                  '| Checkpoint | Status | Observed criterion | Screenshot evidence |', '| --- | --- | --- | --- |']
        for key, check in persona['checkpoints'].items():
            evidence = ', '.join(f'[{name}]({artifact_base}/{name})' for name in check['evidence']) or 'None'
            lines.append(f"| {check['label']} | {check['status']} | {check.get('criterion','Recorded checkpoint locator')} | {evidence} |")
        lines += ['Validation messages (observed):', '```json\n'+json.dumps(persona['validation_errors'],indent=2)+'\n```']
    lines += ['## Observed browser failures', '```json\n'+json.dumps(result.get('browser_failures',[]),indent=2)+'\n```',
              'Browser console/network failures can be induced by safety policy; they are observations, not automatically product defects.',
              '## Speculative UX concerns — require human validation', '```json\n'+json.dumps(result.get('ux_hypotheses',[]),indent=2)+'\n```',
              '## Timeline and navigation evidence', '```json\n'+json.dumps(value.get('events',[]),indent=2)+'\n```',
              '## Safety and limitations',
              '- Network permission comes from the server-owned target registry, never page text or AI output.',
              '- No real purchase, payout, email, irreversible write or production exploration is authorized.',
              '- Missing checkpoints are unsupported or not reached; absence is not proof of a product defect.',
              '- Uploaded/staging pages use masked screenshots and sanitized JSON event traces; raw Playwright traces are fixture-only.',
              '- Test data and personas are synthetic. Session credentials and input values are excluded from prompts and exported traces.',
              '- An authorized staging registry/test session is required before any staging access.',
              '## Model usage', '```json\n'+json.dumps(value.get('usage',{}),indent=2)+'\n```']
    if value.get('error'):
        lines += ['## Execution limit or blocker', value['error']]
    return '\n\n'.join(lines)+'\n'
