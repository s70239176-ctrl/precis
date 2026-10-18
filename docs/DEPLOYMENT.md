# Canonical Studionet deployment and live evidence

| | |
|---|---|
| Network | GenLayer Studionet, chain id 61999, RPC `https://studio.genlayer.com/api` |
| Method | `genlayer-test` Studio Mode, `scripts/live_canonical.py` (genlayer-test 0.29.2, genlayer-py 0.16.3, Python 3.12.10) |
| Deployer (public address) | `0x3BAb8bdc7337B6F419b529759Facaf0B869e6F27` (ephemeral default Studionet account; no key recorded) |
| Canonical contract | `0x611Ce44Cc09BD22179722fc132358383f7D55b16` |
| Explorer | https://explorer-studio.genlayer.com/address/0x611Ce44Cc09BD22179722fc132358383f7D55b16 |
| Deployment tx | `0xd071b6ed84491ca46afad7defaea5056588ecf6a36b77c5540bc0b9ce26db6ce` |
| Status observed | `ACCEPTED` for every tx below. **FINALIZED was not checked or claimed.** |
| Deployment source | working tree at commit `7cd17aa`; `contracts/precis.py` blob `a45d22fc5607a3042835d84af9ef03ed4e9ce84b`, identical at `f2bcb3f` and `7cd17aa` (the contract file has not changed since the first commit) |
| On-chain code vs file | not compared byte-for-byte (`genlayer code` not run) |

Raw record: [`evidence/live_state.json`](../evidence/live_state.json).

## Transactions

| Scenario | Action | Tx | Stored result |
|---|---|---|---|
| deploy | constructor | `0xd071b6ed…db6ce` | contract created |
| success | `register` #1 | `0x1796fe09…fc8b9` | digest 1 |
| success | `audit(1)` real validators + model | `0x5509438b…7543f` | **FAITHFUL**, defects 0, no findings, `reliance_status` RELIABLE |
| negative (deterministic) | `register` #2 (summary says 7%, source says 5%) | `0xb581681e…ce88a8` | digest 2 |
| negative (deterministic) | `audit(2)` | `0xf5cecab6…592ea` | accepted; the receipt for this audit rotated out of my recorded results (only the last receipt was saved), so the 7% refusal is shown by the integration test, not by this table |
| negative (semantic) | `register` #3 + `audit(3)` (summary says "Withdrawals are always available", source says Acme may freeze all withdrawals) | `0x5de0b7ab…942f4`, `0x62b1af49…34702` | **MISLEADING**, defect CONTRADICTION, grounded quote `Acme may freeze all withdrawals indefinitely.`, reliance BLOCKED |
| recovery | `revise(2, corrected summary)` | `0x2acf58f3…52cc7` | version 2, verdict cleared |
| recovery | `audit(2)` again | `0x83a88269…e6340` | **FAITHFUL**, receipt version 2, `RELIABLE` |

Full hashes are in `evidence/live_state.json`.

## Integration suite

`gltest tests/integration/ -v -s --network studionet` (5 tests, real consensus):

* run 1: 2 passed, 3 failed (gateway `RemoteDisconnected` at deploy/connect);
* run 2: 4 passed, 1 failed (test bug: summary omitted a scope item; the model rightly said INCOMPLETE; fixed);
* run 3 (after the fix): **4 passed, 1 failed**, the failure again a `RemoteDisconnected` at deploy, before any transaction.

The suite has **not** passed 5/5 in a single run. `test_live_wrong_figure_is_refused_deterministically`
passed in run 2 and failed only on transport in runs 1 and 3. Disposable test deployments are not the canonical contract.
