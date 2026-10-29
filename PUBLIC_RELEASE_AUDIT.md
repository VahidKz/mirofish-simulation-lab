# Public source release review — 29 October 2026

Destination: `VahidKz/mirofish-simulation-lab`. Foundation: public `nikmcfly/MiroFish-Offline`, commit `313fe64`. This source edition was assembled in a separate worktree, preserving the private working lab.

## Scope and exclusions

Reusable inference, graph/OASIS, read-only ingestion, source-reference, dashboard and browser journey code is included. Examples are synthetic fixtures. Real case definitions, literal private policy dictionaries, source curation/replay scripts, collected knowledge, audits and presentations were excluded. The case adapter now loads operator-owned private JSON and is hidden unless explicitly configured.

No `.env`, authentication store, session, source archive, operational database, logs, browser trace, screenshot, generated report, installed environment or build output is part of the candidate Git tree. The private code/workspace branch was not pushed.

## License and attribution

The full upstream AGPL-3.0 `LICENSE` is byte-identical to the foundation. Original source notices remain. `NOTICE`, `MODIFICATIONS.md`, `THIRD_PARTY_NOTICES.md` and the current README identify upstream authors, dependency notices and dated changes. Future container distribution/network hosting must satisfy the applicable license source-availability conditions.

## Verification

- 107 automated checks passed, including the pre-existing suite, optional-case loader/OASIS tests using model doubles, publication-boundary tests and the profile-format check.
- Frontend production build and Python compilation passed.
- A fresh public API exposed A/B/C, hid the unconfigured private case, returned an empty knowledge workspace and loaded the public setup note.
- A deterministic synthetic buyer journey completed ten actions and all configured checkpoints with **zero attempted model turns**. Its evidence remains ignored locally and is not published.
- Candidate-tree/history path checks passed. The importer and provider/authentication implementations differ from the private lab only by dated modification comments.
- Gitleaks 8.30.1 from the official checksum-verified release scanned the candidate source and reachable history with redacted output. No secret findings were reported. The final scanner reports and archive manifest are kept locally, not published.

These checks are bounded evidence, not proof that arbitrary future input or every transitive dependency is free of confidential information or security flaws. Future changes must pass the same candidate/history checks. The Docker image workflow is manual-only; this source publication does not publish an image or deploy a service.

## Neutral public naming

The public dashboard is `/simlab`, Python extension modules are under `app.simlab`, environment settings use `SIMLAB_*`, and example data is fictional collectibles/retail research. Customer branding, customer-named paths and private case acronyms are not distributed, including compatibility aliases. The extension is published as one neutral release commit on the preserved upstream foundation.
