# Browser journey runner

This modular Playwright addition is independent of OASIS social discussions. The built-in Buyer, Private Seller and Merchant pages are explicitly fictional frontend fixtures with no backend or real marketplace services.

```bash
PYTHONPATH=backend .venv/bin/python backend/scripts/simlab_journey.py --template buyer
PYTHONPATH=backend .venv/bin/python backend/scripts/simlab_journey.py --template seller_offer
PYTHONPATH=backend .venv/bin/python backend/scripts/simlab_journey.py --template merchant
```

Scripted mode uses zero model calls. AI mode is opt-in and consumes the configured provider's account usage within the shared cap. It uses visible control IDs and predefined synthetic values/files, never arbitrary JavaScript, credentials or model-selected file paths.

The dashboard supports your own authorized HTML/folder uploads separately from the unchanged read-only importer. File maps are served at a virtual local origin; cross-origin requests and real writes are blocked. Supply explicit checkpoint locators and scripts for custom pages. Fixture selectors are not assumed to work on another application.

Every persona uses a fresh isolated context, processed serially. Actions, validation, masked screenshots and checkpoint evidence are retained under the ignored `backend/uploads/` directory. Raw Playwright ZIP traces are fixture-only; uploads/staging retain sanitized event traces because raw browser traces can contain private DOM/network data.

Only explicitly registered local/test staging origins can be interactive targets. Production automation is prohibited. Staging requires seeded records, sandbox service confirmation, exact permitted paths and explicit authorization. Write requests are never forwarded; any necessary writes must be declared local mock responses. A mock response verifies frontend presentation, not a backend service.

Staging login has a separate authorization flag. Only deliberately provided private seeded storage state may be loaded; normal browser profiles are not imported. Password and payment controls remain blocked. Non-allowlisted destinations, popups, downloads, service workers and external payment/SSO frames are unsupported.

Use `journey-targets.example.json` as a schema illustration only. Its hosts, paths and selectors are placeholders, not discovered routes. Keep the real registry/session outside Git and set `SIMLAB_JOURNEY_TARGETS_FILE` to its absolute path.

Existing bounds cover calls, per-persona steps and a whole-process watchdog. Reports distinguish observed failures, policy-induced restrictions and speculative UX concerns. Checkpoint counts are not customer conversion rates.
