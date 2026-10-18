# Precis

**Is this summary faithful to its source?** A standalone GenLayer Intelligent Contract. A digest binds a public
HTTPS source, an immutable materiality `scope`, and a bounded summary. Anyone can `audit` it: every validator
fetches the source itself, recomputes a deterministic figure floor, and independently accounts for every sentence of
the summary. Other contracts read `attests(id, summary_hash, now_ts, max_age_s)`. No funds, no admin key, no frontend.

- **Who calls it:** DAOs showing proposal digests, wallets showing terms gists, grant programs checking progress reports.
- **What consensus decides:** FAITHFUL / INCOMPLETE / MISLEADING for one summary version against one source snapshot.
- **What code decides:** figures, verdict table, cooldowns, freshness, bounds, receipt binding.
- **Delete GenLayer:** the summary's author, or one operator, becomes the judge of their own restatement.

## Live contract (Studionet)

| | |
|---|---|
| Contract | [`0x611Ce44Cc09BD22179722fc132358383f7D55b16`](https://explorer-studio.genlayer.com/address/0x611Ce44Cc09BD22179722fc132358383f7D55b16) |
| Network | GenLayer Studionet, chain id 61999, RPC `https://studio.genlayer.com/api` |
| Deployment tx | `0xd071b6ed84491ca46afad7defaea5056588ecf6a36b77c5540bc0b9ce26db6ce` (ACCEPTED; FINALIZED not checked) |
| Deployer | `0x3BAb8bdc7337B6F419b529759Facaf0B869e6F27` (ephemeral test account) |
| Source | `contracts/precis.py`, git blob `a45d22fc5607a3042835d84af9ef03ed4e9ce84b`, unchanged since the first commit; on-chain code not byte-compared |
| Live results | digest 1 FAITHFUL; digest 3 MISLEADING (grounded contradiction: "Withdrawals are always available" vs "Acme may freeze all withdrawals indefinitely"); digest 2 revised then FAITHFUL |
| Evidence | [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md), [evidence/live_state.json](evidence/live_state.json) |

Call it from another contract: [docs/INTEGRATION.md](docs/INTEGRATION.md). Studionet is a development network; not audited.

## Status (what was actually run)

| Gate | Result |
|---|---|
| Direct Mode (`tests/direct`) | 123 passed (63 surface/lifecycle, 60 forged-leader + malformed-result), Windows shim used |
| Mutation checks | 5 deliberate validator/gate breakages each made tests fail (verdict compare, UNCLASSIFIED censorship, digest, coverage, figure floor) |
| GenVM lint / SDK check (`genvm-lint` 0.11.0) | passed, 12 methods (8 view, 4 write); reports a newer py-genlayer runner exists than the header pins |
| Studionet integration (`tests/integration`, 5 tests, real validators, disposable contracts) | best single run 4/5; never 5/5 in one run. Failures were gateway `RemoteDisconnected` at deploy (runs 1 and 3, before any tx) and one test bug of mine (run 2, fixed). Details in docs/DEPLOYMENT.md |
| Canonical deployment | Studionet `0x611Ce44Cc09BD22179722fc132358383f7D55b16` ([explorer](https://explorer-studio.genlayer.com/address/0x611Ce44Cc09BD22179722fc132358383f7D55b16)), live FAITHFUL, MISLEADING (grounded contradiction) and revise-then-FAITHFUL recorded in [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md). Txs are ACCEPTED; FINALIZED not checked. Integration suite has not passed 5/5 in one run (gateway disconnects at deploy; 4/5 best). On-chain code not byte-compared to the file |

A real-validator FAITHFUL verdict and a real INCOMPLETE verdict (omission caught) have been observed on Studionet. Hashes for the canonical run are in docs/DEPLOYMENT.md.

## Verdict model

`FIGURE | CONTRADICTION | ADDITION` -> MISLEADING; `OMISSION` only -> INCOMPLETE; none -> FAITHFUL. FAITHFUL requires
a grounded support quote for every claim sentence, so a silent or injected model cannot grant it. Unreadable, oversized
(>14 000 chars, never truncated) or unclassifiable sources are recorded but never trusted.

## Surface

Writes: `register(url, scope, summary)`, `revise(id, summary)`, `deactivate(id)`, `audit(id)`.
Views: `get_digest`, `get_receipt`, `status_of`, `is_faithful`, `reliance_status`, `attests`, `receipt_matches`.

## Docs

[DECISION.md](DECISION.md) (why this primitive, collisions) · [docs/CONSENSUS.md](docs/CONSENSUS.md) ·
[docs/SECURITY.md](docs/SECURITY.md) · [docs/INTEGRATION.md](docs/INTEGRATION.md)

## Reproduce

```bash
python -m venv .venv-test && .venv-test/Scripts/pip install -r requirements-test.txt
PYTHONPATH=scripts pytest tests/direct -p windows_direct_plugin   # the plugin is only needed on Windows
genvm-lint check contracts/precis.py
gltest tests/integration/ -v -s --network studionet               # needs Studionet reachability; ~500 req/h limit
```

## Limitations

Attests fidelity to the chosen source, not truth. Figure check is literal (derived or spelled-out numbers are
flagged or ignored respectively). Studionet is a development network; not audited.
