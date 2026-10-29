# Modification notice — 29 October 2026

This is an independent modified edition of `nikmcfly/MiroFish-Offline` at foundation commit `313fe64`. The original MiroFish and offline-fork notices and AGPL-3.0 license are retained. Research extensions and this sanitized public edition were prepared for [VahidKz](https://github.com/VahidKz).

Changes include a local research dashboard, Codex/Ollama provider routing and native CAMEL adapter, persistent model budgets and concurrency controls, read-only material ingestion, a separate bounded Playwright journey runner, source provenance/conflict references, test fixtures, and an optional private JSON case adapter. Existing service files were changed to integrate inference and local storage. This is not an unchanged upstream checkout or an official upstream release.

The public edition excludes all collected product specifications and research evidence, actual policy dictionaries, private case-specific scripts, audit reports, presentations, credentials, sessions and runtime data. The original private workspace is not the publication source. A validated operator-supplied JSON case replaces embedded real-case policy code. Examples are invented frontend fixtures and are not a company's product contract.

The inherited image workflow is manual-only. The application remains a loopback workstation tool. Codex inference uses the account's remote service; local Ollama is an explicit alternative. No paid fallback or extra-credit purchasing is implemented.

## Changed or added paths relative to the foundation

The following list is the dated modification notice for source, configuration, documentation and lock-file changes. Existing upstream copyright notices remain intact. `LICENSE` is byte-identical to the foundation.

- `.dockerignore`
- `.env.simlab.example`
- `.github/workflows/docker-image.yml`
- `.gitignore`
- `JOURNEY_SETUP.md`
- `MODIFICATIONS.md`
- `NOTICE`
- `PRIVATE_CASE_SETUP.md`
- `PUBLIC_RELEASE.md`
- `PUBLIC_RELEASE_AUDIT.md`
- `README.md`
- `THIRD_PARTY_NOTICES.md`
- `backend/app/__init__.py`
- `backend/app/config.py`
- `backend/app/services/oasis_profile_generator.py`
- `backend/app/services/simulation_config_generator.py`
- `backend/app/services/simulation_runner.py`
- `backend/app/simlab/__init__.py`
- `backend/app/simlab/api.py`
- `backend/app/simlab/camel_adapter.py`
- `backend/app/simlab/case_review.py`
- `backend/app/simlab/codex_worker.py`
- `backend/app/simlab/ingestion.py`
- `backend/app/simlab/journeys/__init__.py`
- `backend/app/simlab/journeys/api.py`
- `backend/app/simlab/journeys/knowledge.py`
- `backend/app/simlab/journeys/models.py`
- `backend/app/simlab/journeys/policy.py`
- `backend/app/simlab/journeys/report.py`
- `backend/app/simlab/journeys/runner.py`
- `backend/app/simlab/journeys/service.py`
- `backend/app/simlab/journeys/templates.py`
- `backend/app/simlab/journeys/worker.py`
- `backend/app/simlab/knowledge.py`
- `backend/app/simlab/knowledge_collection.py`
- `backend/app/simlab/lab.py`
- `backend/app/simlab/provider.py`
- `backend/app/simlab/scenarios.py`
- `backend/app/storage/embedding_service.py`
- `backend/app/storage/neo4j_storage.py`
- `backend/app/storage/ner_extractor.py`
- `backend/app/utils/file_parser.py`
- `backend/app/utils/llm_client.py`
- `backend/pyproject.toml`
- `backend/pytest.ini`
- `backend/requirements.simlab.lock`
- `backend/requirements.txt`
- `backend/run.py`
- `backend/scripts/run_parallel_simulation.py`
- `backend/scripts/run_reddit_simulation.py`
- `backend/scripts/run_twitter_simulation.py`
- `backend/scripts/simlab_case_review.py`
- `backend/scripts/simlab_journey.py`
- `backend/scripts/simlab_kb.py`
- `backend/scripts/simlab_smoke.py`
- `backend/tests/conftest.py`
- `backend/tests/test_adapter.py`
- `backend/tests/test_api.py`
- `backend/tests/test_ingestion.py`
- `backend/tests/test_journey_api.py`
- `backend/tests/test_journey_browser.py`
- `backend/tests/test_journey_knowledge.py`
- `backend/tests/test_journey_policy.py`
- `backend/tests/test_journey_service.py`
- `backend/tests/test_knowledge.py`
- `backend/tests/test_private_case.py`
- `backend/tests/test_provider.py`
- `backend/tests/test_release_boundary.py`
- `backend/tests/test_scenarios.py`
- `backend/tests/test_sdk_auth.py`
- `backend/uv.lock`
- `compose.simlab.yml`
- `docs/UPSTREAM_README.md`
- `docs/research/BUYER_JOURNEY.md`
- `docs/research/CONFLICTS.md`
- `docs/research/MERCHANT_GAPS.md`
- `docs/research/PRODUCT_RULES.md`
- `docs/research/README.md`
- `docs/research/SELLER_JOURNEYS.md`
- `docs/research/SOURCE_CATALOG.md`
- `examples/simlab-journeys/buyer.html`
- `examples/simlab-journeys/journey.css`
- `examples/simlab-journeys/journey.js`
- `examples/simlab-journeys/merchant.html`
- `examples/simlab-journeys/offer.html`
- `examples/simlab-wireframe/index.html`
- `examples/simlab-wireframe/merchant.html`
- `examples/simlab-wireframe/style.css`
- `examples/simlab-wireframe/wireframe.js`
- `frontend/package-lock.json`
- `frontend/package.json`
- `frontend/public/home-styles.css`
- `frontend/src/App.vue`
- `frontend/src/api/index.js`
- `frontend/src/components/JourneyPanel.vue`
- `frontend/src/components/KnowledgePanel.vue`
- `frontend/src/router/index.js`
- `frontend/src/views/Home.css`
- `frontend/src/views/Home.vue`
- `frontend/src/views/SimulationLab.vue`
- `frontend/vite.config.js`
- `journey-targets.example.json`
- `scripts/check-public-release.py`
- `scripts/simlab-local.sh`
