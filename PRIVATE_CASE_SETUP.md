# Optional private case review

The public distribution includes the orchestration engine and synthetic tool fixtures, but no real product case. The five-phase case template is hidden in `/simlab` until `SIMLAB_CASE_FILE` is explicitly configured. The loader fails before starting a model turn if data is missing or invalid.

Create a private JSON definition outside Git, for example under the ignored `.run/` directory. Set `SIMLAB_CASE_FILE` to its **absolute** path in your ignored `.env`, and restart only after active runs finish. The definition has these fields:

| Field | Requirement |
| --- | --- |
| `title` | A human-readable case label |
| `evidence_root` | Absolute directory containing your authorized source archives |
| `phases` | Exactly five objects with unique `id`, `label`, `question`, and a bounded list of `facts` IDs |
| `personas` | Exactly four objects, IDs 0–3, with `role`, `name`, `goal`, `concerns`, `behavior` |
| `sources` | At most twelve source records: `id`, `path`, `original_snapshot`, `sha256`, and your source-status metadata |
| `facts` | At most forty reviewed assertions, each with `id`, `claim`, and `evidence` referencing supplied source IDs and line locators |
| `conflicts` | At most twelve objects with `id`, `title`, `handling`, both source positions and `resolved: false` where applicable |

`original_snapshot` must resolve to a file within `evidence_root`, at most 2 MB, matching its SHA-256. Source labels are operator-provided claims, not verified approvals. JSON is treated as data; it cannot supply Python plugins or execution tools. The compact source packet must fit the lab's 14,000-character context bound.

The orchestrator uses four invented roles and five scheduled conditional discussions, allowing only simulated comments or doing nothing. Later phases are not evidence that earlier business actions completed. It requests a stated intention and source citations, but free-text model statements are not an enforced business state machine.

Run after configuring and reviewing your source packet:

```bash
PYTHONPATH=backend .venv/bin/python backend/scripts/simlab_case_review.py
```

This starts one live model run with a **24-attempt shared cap** and provider retries disabled by the CLI. Planned usage is two graph turns, one persona turn, twenty agent decisions and one report turn. Failure or additional generation consumes the same cap and can leave partial evidence. Account usage is not free or unlimited; no paid API fallback or automatic cap increase is enabled.

The original private case, literal product rules, customer source catalogs, reports and presentations are intentionally not provided. Populate this schema from sources you are authorized to use; do not infer a company's policies from synthetic sample pages.
