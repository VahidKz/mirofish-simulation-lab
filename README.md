# MiroFish Simulation Lab

A modified, local-workstation research edition of [MiroFish-Offline](https://github.com/nikmcfly/MiroFish-Offline), which derives from [MiroFish](https://github.com/666ghj/MiroFish). Includes a bounded multi-agent lab, an independent browser journey runner, and reusable source-evidence tooling.

**Modified edition dated 29 October 2026.** Distributed under the existing [GNU AGPL-3.0 license](LICENSE). See [NOTICE](NOTICE) and [MODIFICATIONS.md](MODIFICATIONS.md) for attribution and changes. This is an independent fork; upstream authors and service providers do not endorse its results.

## What is included

- Original graph and OASIS/CAMEL simulation components, with Neo4j and Ollama embeddings.
- A `/simlab` research dashboard for small hypothetical scenario comparisons, saved records and reports. Examples use invented research policies and personas; no customer brand or product specification is distributed.
- An authenticated Codex provider and native CAMEL action adapter, persistent SQLite model-turn budgets, a shared inference lock and no paid API fallback. Using Codex consumes the signed-in account's usage and sends prompts to OpenAI. It is **not fully offline**. Ollama inference is a separately selected local alternative.
- A separate Playwright journey runner with isolated contexts, bounded actions, evidence capture and explicit target permissions. Generated examples verify the tool, not any company's service.
- Read-only material import, source provenance and conflict-aware references. No customer wireframes, collected knowledge base, private policies, audit reports or CEO presentation are included.
- An optional private-case adapter. Its roles, five phases and evidence must be explicitly supplied by the operator; the case template is hidden until configured. No real case is distributed.

A completed synthetic discussion or checkpoint is not a purchase, payout, customer conversion metric or validated prediction of human behavior.

## Quick start

Use Python 3.11, Node.js with npm, Docker Compose and `uv`. The tested helper targets Linux/WSL x86_64 with CPU PyTorch wheels; see its script for other-platform handling.

```bash
git clone https://github.com/VahidKz/mirofish-simulation-lab.git
cd mirofish-simulation-lab
./scripts/simlab-local.sh setup
./scripts/simlab-local.sh start
```

The helper creates a private `.env` with a generated local database password, installs locked dependencies and Chromium, starts Neo4j/Ollama, and pulls the local embedding model. Initial downloads require network access. Existing `.env` files are not overwritten.

Open <http://localhost:3000/simlab>. The original interface remains at <http://localhost:3000/>. The helper binds to loopback and is intended for a trusted workstation, not an Internet-facing multi-tenant service.

```bash
./scripts/simlab-local.sh status
./scripts/simlab-local.sh stop
```

Review `.env.simlab.example` before running inference. Codex uses the supported installed client's existing ChatGPT authentication; authentication files are never bundled. No API key is required for that path. Set `MODEL_PROVIDER=ollama` only when explicitly choosing the local model alternative. No automatic provider fallback is enabled. Do not assume a subscription includes unlimited usage or that a model is available to your account.

## Zero-inference browser check

```bash
PYTHONPATH=backend .venv/bin/python backend/scripts/simlab_journey.py --template buyer
```

Other synthetic examples use `--template seller_offer` and `--template merchant`. Each uses isolated local sample pages, not collected product evidence. The CLI exits 0 for all configured checkpoints and 2 for bounded partial/failure results. See [browser journey setup](JOURNEY_SETUP.md).

## Small model-driven social run

```bash
PYTHONPATH=backend .venv/bin/python backend/scripts/simlab_smoke.py
```

This is **opt-in inference** through your configured provider, not a free/no-model test. It creates a synthetic three-agent experiment with the existing hard cap. Review the dashboard's estimate, server cap and provider settings first. Source evidence is untrusted data, never authorization for real-world actions.

## Private case definitions and research materials

The source-evidence tool accepts your own authorized files. Store originals, collected text, source catalogs and reports outside version control. Its expected local schemas and optional five-phase case adapter are described in [private case setup](PRIVATE_CASE_SETUP.md). Do not commit identity documents, payment data, login state or customer records.

The `SIMLAB_KNOWLEDGE_HOST` passive collector is disabled by default. An explicit public host enables bounded GET-only public-document collection; it never grants interactive automation. Interactive production targets remain prohibited. Staging login requires a separate explicit grant and a deliberately provided seeded session.

## Verification without inference

```bash
PYTHONPATH=backend .venv/bin/python -m pytest backend/tests backend/scripts/test_profile_format.py -q
.venv/bin/python -m compileall -q backend/app backend/scripts
npm --prefix frontend run build
python3 scripts/check-public-release.py
```

Tests replace model responses with deterministic test doubles and use local fixtures. Release checks inspect the actual Git candidate tree, reject runtime/private files and require the original license. Run the independent secret scanner described in [PUBLIC_RELEASE.md](PUBLIC_RELEASE.md) before pushing.

## License and credits

- Original MiroFish: [666ghj/MiroFish](https://github.com/666ghj/MiroFish), by 666ghj, originally supported by Shanda Group.
- Offline foundation: [nikmcfly/MiroFish-Offline](https://github.com/nikmcfly/MiroFish-Offline), retaining its Neo4j/Ollama migration and English UI work.
- Agent simulation: [CAMEL-AI OASIS](https://github.com/camel-ai/oasis) and [CAMEL](https://github.com/camel-ai/camel).
- Browser automation: [Playwright](https://github.com/microsoft/playwright-python). Codex generation uses the separately installed official SDK.

Keep the AGPL license, upstream notices and modification notices. Distribution of modified source remains under AGPL-3.0; binary/container distribution and remote-network use have corresponding-source obligations under the license. If operating a modified version over a network, provide the applicable source-access offer required by Section 13. Review the [license text](LICENSE), including Sections 5, 6 and 13, for the exact conditions.

Dependencies and separately obtained services retain their own licenses. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). The historical upstream README is preserved at [docs/UPSTREAM_README.md](docs/UPSTREAM_README.md).
