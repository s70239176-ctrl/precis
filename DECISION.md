# Decision record: why Precis

Precis is a standalone GenLayer Intelligent Contract. This file records how the primitive was
chosen, what it deliberately does not overlap with, and the hardest risk.

## Portfolio collision map

Sibling projects inspected (README and contract header) before choosing:

| Repo | Core trust question | Decision | Same lane as Precis? |
|---|---|---|---|
| driftline | Has a public commitment changed since I relied on it? | severity of change of **one page over time** | No. Precis compares **two different texts** (summary vs source) at one moment. |
| headwater | Do N sources corroborate a claim independently? | stance + copying across sources | No. Precis has one source and judges a *derived text*. |
| airlock | Is this page trying to command the model reading it? | CLEAN / QUARANTINED | No. Safety of ingestion, not fidelity of a restatement. |
| credo | What collateral does this identity's public standing earn? | standing quote | No. |
| charterkeeper | Does a plan or spend conform to an immutable charter? | conformance to a **rule** | Adjacent. Charter conformance judges an *action* against a rule; Precis judges whether a *restatement* preserves a source (omission, addition, contradiction). Different evidence role, different state. |
| sla-claim (Tally) | Was an endpoint up? | UP / DOWN probes | No. |
| inquest, sealed, rfpfit, mandate, chargeback, meridian | adjudication of bounties, bids, treasury spend, agent spend, cross-chain escrow | settlement of value | No. Precis moves no value. |
| opennotum | Notarised receipt that a page said something | attestation of page content | Adjacent. OpenNotum attests *what a page says*; Precis attests *that a second text honestly restates it*. |
| commonwealth, agon | simulated world; two-sided contest | game / debate | No. |

## Candidates considered (12)

| # | Candidate | Verdict |
|---|---|---|
| 1 | **Summary fidelity** (this one) | chosen |
| 2 | License-compatibility verdict from a public LICENSE | deterministic SPDX matching covers most of it; the semantic remainder is thin |
| 3 | Deprecation/sunset detector | same lane as driftline |
| 4 | Citation support (does source back a quoted claim) | folds into headwater's stance judgement |
| 5 | Cross-link identity (do pages share a controller) | deterministic bidirectional link check does most of it; overlaps credo |
| 6 | Incident-resolved status from a status page | overlaps tally |
| 7 | Release-notes vs diff honesty | diff size breaks the bounded-input rule |
| 8 | Translation equivalence | same primitive as 1 with a harder language problem; subsumed |
| 9 | Maintainer liveness heartbeat | mostly deterministic |
| 10 | Sanctions / jurisdiction restriction reading | legal advice risk, unstable evidence |
| 11 | Privacy-policy-to-claim consistency | a special case of 1 |
| 12 | Dependency EOL horizon | driftline lane |

## Why summary fidelity

Every reader-facing summary has the same defect: the author benefits if readers believe it.
Governance proposal digests, terms-of-service gists, grant milestone reports, localised notices,
"what you are signing" prompts. The reader cannot afford to read the source, which is why the summary
exists. Today the only fix is trusting the summary's author, or a second operator who reads
the source for you.

## Delete-GenLayer test

Remove GenLayer and *someone* must be trusted to both choose which source is authoritative
and read it against the summary: the author (conflict of interest) or an auditing operator
(a single authority whose reading becomes the verdict). With GenLayer, each validator fetches
the source itself, recomputes the deterministic floor, and independently accounts for every
sentence of the summary; the verdict exists only if they agree.

## Three consumers that need no change to the contract

1. A DAO that only opens voting when `attests(proposal_digest_id, hash_shown_to_voters, ...)` is true.
2. A wallet or registry that only displays a "plain-English terms" gist when it is attested.
3. A grant program that releases a milestone only if the grantee's progress summary is attested
   against the public deliverable page.

## Architecture in one line

```
immutable (url, scope) + bounded summary
  -> deterministic admission
  -> leader/validators each fetch the source
  -> deterministic FIGURE floor (no model)           } validators recompute both
  -> sentence-by-sentence accounting (model, grounded)}
  -> plain-code verdict table, bound to summary hash + source digest
```

## Hardest technical risk

Getting a model to account for every sentence with *verbatim* quotes reliably enough that
honest validators agree, without loosening the grounding that makes a FAITHFUL verdict
meaningful. Mitigations: quotes are short (4..200 chars), consensus is on the verdict class
only (the findings' diagnostic wording may differ), and any accounting gap fails closed to
`UNCLASSIFIED`, never to `FAITHFUL`. Live behaviour is recorded in `docs/DEPLOYMENT.md`.

## Why it belongs under standalone Intelligent Contracts

No frontend, no backend, no funds, no admin key. One contract, a typed interface, and a trust
model that is the product.
