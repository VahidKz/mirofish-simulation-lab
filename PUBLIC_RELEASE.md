# Public release boundary

This is a sanitized source edition, not an export of a private research workspace. Reusable engines and synthetic fixtures are included. Collected specifications, case definitions, audits/presentations and operational data remain private.

## Candidate-tree checks

```bash
python3 scripts/check-public-release.py
# Optional: keep customer names/identifiers in a private JSON list outside Git.
python3 scripts/check-public-release.py --deny-terms-file /absolute/private/path/deny-terms.json
# Gitleaks, using an independently installed official binary:
gitleaks dir . --redact --no-banner
gitleaks git . --log-opts=--all --redact --no-banner
```

Review the exact candidate paths and staged diff before committing. `.gitignore` does not remove already tracked content or older history. The release checker rejects forbidden paths anywhere reachable in local refs, verifies the original license hash, scans content for private-case markers and likely credentials, and can validate a tracked candidate manifest. Keep scanner reports local and redacted; do not publish matched credential values.

Before pushing, verify the destination is your repository, run tests/build, inspect every outgoing commit, and ensure the private source checkout is not the push source. The foundation's upstream history is retained for attribution; no private working-tree commits are included. Never force-push another repository or publish the original private branch to make an export easier.

The inherited container-publishing workflow is manual-only in this edition. No image, tag, deployment or registry package is published by a source push. The application is configured for a trusted local workstation, not public hosting.

## Excluded

- `.env` and operational environment variants; only reviewed example templates are shipped.
- Authentication stores, session/storage-state files, keys and certificates.
- `backend/uploads/`, logs, `.run/`, local browser evidence, SQLite/Neo4j data, installed environments and build outputs.
- The entire collected `knowledge-base/` corpus and customer specifications.
- Case-specific policy dictionaries, curation scripts, exact source selectors and run-specific replay scripts.
- Audit reports, model-usage histories, CEO presentations, user paths and private source identifiers.

The optional private-case loader accepts operator-provided JSON. That input and its source archives are not distributed. Keep it private even after enabling the feature.

## License

`LICENSE` is the unchanged AGPL-3.0 text inherited from the foundation. `NOTICE`, `MODIFICATIONS.md` and upstream source notices identify provenance and changes. Binary distribution and remote-network operation have source-availability conditions under the license; publishing this source alone does not configure a hosted source offer for a future deployment.
