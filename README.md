# OriginMesh

Three links can look like three witnesses while carrying one story. OriginMesh audits source lineage instead of voting on truth. It freezes three to eight public pages, binds exact quotations and SHA-256 receipts, groups derivative coverage under its listed original root, and measures whether the requested number of independently gathered roots exists.

## Mechanism

1. The owner opens a draft study with a claim and an independent-root threshold.
2. The owner adds distinct public HTTPS source documents, then permanently seals the source set.
3. Anyone may run the audit. Validators fetch every page and compare the full frozen contents.
4. Every source receives one of four relations: `ORIGINAL`, `DERIVED`, `COMMON_ORIGIN`, or `UNRESOLVED`.
5. The contract derives `INDEPENDENT`, `CONCENTRATED`, or `INCONCLUSIVE`; the model cannot supply that outcome directly.
6. Anyone may finalize the audited result, producing an immutable receipt over the outcome and all source digests.

OriginMesh does not determine whether a claim is true. It reveals whether apparent corroboration comes from genuinely distinct reporting roots. Different domains alone do not prove independence.

## Verification

```bash
python -m pytest tests -q
genvm-lint lint contracts/origin_mesh.py --json
```

The files under `docs/` are operator-created smoke fixtures, not independent authorities. The contract targets GenLayer Studio Next, chain `61997`.

## Live deployment

- Contract: `0x40cf1a0C4a734F9265D81beD5E307a8c16bC9411`
- Network: GenLayer Studio Next (`61997`)
- Exact deployed-source match: `true`
- Completed smoke study: `origin-demo-mv2lscu4`
- Stored outcome: `INDEPENDENT` with `2` independent roots

Every deployment and smoke transaction is recorded in `deployment.json` so reviewers can reproduce the evidence without trusting this summary.
