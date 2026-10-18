# Precis

**Is this summary faithful to its source?** A standalone GenLayer Intelligent Contract. A digest binds a public
HTTPS source, an immutable materiality `scope`, and a bounded summary. Anyone can `audit` it: every validator
fetches the source itself, recomputes a deterministic figure floor, and independently accounts for every sentence of
the summary. Other contracts read `attests(id, summary_hash, now_ts, max_age_s)`. No funds, no admin key, no frontend.

- **Who calls it:** DAOs showing proposal digests, wallets showing terms gists, grant programs checking progress reports.
- **What consensus decides:** FAITHFUL / INCOMPLETE / MISLEADING for one summary version against one source snapshot.
- **What code decides:** figures, verdict table, cooldowns, freshness, bounds, receipt binding.
- **Delete GenLayer:** the summary's author, or one operator, becomes the judge of their own restatement.

## Status (what was actually run)

| Gate | Result |
|---|---|
| Direct Mode (`tests/direct`) | 123 passed (63 surface/lifecycle, 60 forged-leader + malformed-result), Windows shim used |
| Mutation checks | 5 deliberate validator/gate breakages each made tests fail (verdict compare, UNCLASSIFIED censorship, digest, coverage, figure floor) |
| GenVM lint / SDK check (`genvm-lint` 0.11.0) | passed, 12 methods (8 view, 4 write); reports a newer py-genlayer runner exists than the header pins |
| Studionet integration (`tests/integration`, 5 tests, real validators, disposable contracts) | first run: 2 passed, 3 failed on gateway `RemoteDisconnected` (transport). Second run: 4 passed, 1 failed: the live model correctly returned INCOMPLETE because my test summary omitted an early-exit cost the scope covers (test bug, fixed). After the fix, the faithful test alone passed live (FAITHFUL with a grounded receipt and `attests` true). The full suite has not been re-run as one pass since that edit |
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
