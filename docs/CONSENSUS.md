# Consensus design

One nondeterministic region exists: `audit`, via `gl.vm.run_nondet_unsafe(leader, validator)`.
Everything else (registration, revision, cooldowns, the verdict table, views) is deterministic.

## 1. Exact nondeterministic calls

| Call | Data in | Data out | Why code cannot replace it |
|---|---|---|---|
| `gl.nondet.web.request(url)` | the digest's immutable HTTPS url | status + body | the source is live public state |
| `gl.nondet.exec_prompt(..., response_format="json")` | scope, the summary split into sentences, the source text | `support[]` and `findings[]`, each with verbatim quotes | "does this sentence say what the source says" is semantic |

Everything derived from them is deterministic: HTML stripping, whitespace normalisation, the
SHA-256 source digest, the figure floor, quote grounding, sentence coverage, the verdict table.

## 2. Leader

1. Fetch the source. Not 2xx or empty -> `UNREACHABLE`; more than 400 000 bytes or 14 000 normalised
   chars -> `OVERSIZE` (the source is never truncated, so a decisive clause cannot fall off the end).
2. Compute the **figure floor**: every number, percentage, amount and `0x` address in the summary must
   appear (normalised: commas, spaces, case) in the source. Any miss -> `MISLEADING`, bit `FIGURE`, **no model call**.
3. Otherwise ask the model to account for every summary sentence (see 3), clean its output strictly, and
   derive the verdict from the defect bits.

## 3. Model contract and deterministic cleaning

The model returns `support[]` (summary quote, source quote) and `findings[]` (`CONTRADICTION`,
`OMISSION`, `ADDITION`, with quotes). Cleaning never repairs:

* unknown keys, kinds or types, too many entries, or any quote not found **verbatim** (after whitespace
  normalisation) in the summary / source as required -> the whole answer is `UNCLASSIFIED`;
* **coverage**: every claim sentence of the summary (>= 8 chars, <= 8 of them) must contain a support
  quote or the summary quote of a finding. A silent model cannot produce `FAITHFUL`; an empty answer is `UNCLASSIFIED`.

Verdict table (code): `FIGURE | CONTRADICTION | ADDITION` -> `MISLEADING`; else `OMISSION` -> `INCOMPLETE`; else `FAITHFUL`.

## 4. Validator

Each validator independently:

1. rejects any leader result that is not a strict, internally consistent observation (`_obs_well_formed`:
   exact keys, `type(x) is int` so `True`/`1.0` fail, verdict must equal the table applied to the bits, bits must equal the findings, figure refusals carry no findings, digest is 64 lowercase hex);
2. re-fetches the source itself and recomputes `_assess` on its own copy;
3. requires the leader's **source digest equal to its own** (the snapshot must be byte-stable across validators);
4. requires the leader's **ungrounded figure list equal to its own** (exact);
5. requires every leader finding to be grounded in the validator's own copy of the source and summary;
6. requires the **verdict class** to equal its own.

## 5. Equivalence

Must match: reach class (`OK` / `UNREACHABLE` / `OVERSIZE` / `UNCLASSIFIED`), source digest,
ungrounded figures, verdict. May differ: which findings the model surfaced, their wording, which quote
was chosen as support, the INCOMPLETE-vs-MISLEADING *reason* (only the resulting class matters).
Findings differ honestly between models; the verdict is what downstream security depends on.

## 6. Forged-leader defence

A leader result that is perfectly well-formed but false is rejected because the validator recomputes
rather than inspects shape: a forged `FAITHFUL` fails when the validator finds a defect or a missing
figure; a forged `MISLEADING` fails when the validator finds the summary faithful; an invented quote
fails grounding; a wrong digest fails the snapshot check. A leader also cannot **censor** by claiming
`UNCLASSIFIED`: that claim is accepted only if the validator cannot classify either, otherwise the
round does not reach agreement and a new leader is tried. See `tests/direct/test_precis_hardening.py`
(60 cases, including 41 malformed-result attacks).

## 7. Failure

| Condition | Result |
|---|---|
| source unreachable / non-2xx / empty | receipt `UNREACHABLE`; verdict untouched; streak +1 |
| source over the bound | receipt `OVERSIZE`; reliance `UNKNOWN` immediately |
| model failure, parse failure, accounting gap | receipt `UNCLASSIFIED`; verdict untouched; streak +1 |
| validators disagree | protocol-level `UNDETERMINED`/rotation: **no state change** (distinct from a contract-level `UNCLASSIFIED`) |
| malformed consensus value | user error `EXTERNAL: ...`, no state change |

A non-OK receipt never upgrades trust. After 3 consecutive non-OK audits, `reliance_status` is `UNKNOWN`.

## 8. Why consensus is load-bearing

Remove consensus and the contract has no source text, no digest, and no judgement of whether a sentence
is backed. The only inputs left are the summary the author supplied and whatever the author or an operator
says about the source. The verdict would be an assertion by a single party.
