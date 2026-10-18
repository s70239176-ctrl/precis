# Integrating Precis

A consumer needs no web access, no prompts and no equivalence principle. It pins the summary it
shows and asks one question.

```python
from genlayer import *


@gl.contract_interface
class IPrecis:
    class View:
        def attests(self, digest_id: int, summary_hash: str, now_ts: int, max_age_s: int) -> bool: ...
        def reliance_status(self, digest_id: int, now_ts: int, max_age_s: int) -> str: ...
        def receipt_matches(self, digest_id: int, definition_hash: str, summary_hash: str, source_digest: str) -> bool: ...
        def get_digest(self, digest_id: int) -> dict: ...
    class Write:
        pass


class ProposalGate(gl.Contract):
    precis: Address

    def __init__(self, precis: Address):
        self.precis = precis

    @gl.public.write
    def open_voting(self, digest_id: int, shown_summary_hash: str, now_ts: int) -> None:
        ok = IPrecis(self.precis).view().attests(digest_id, shown_summary_hash, now_ts, 7 * 24 * 3600)
        if not ok:
            raise gl.vm.UserError("EXPECTED: the shown summary is not attested against its source")
        # ... start the vote
```

Views have no clock, so the caller passes `now_ts` (take it from `gl.message_raw["datetime"]`).

## The three consumers

1. **Governance**: open voting only when the digest of the proposal text is attested.
2. **Wallet / registry**: show a "plain-English terms" gist only while `attests(...)` is true.
3. **Grant program**: release a milestone only if the grantee's progress summary is attested against the public deliverable.

## Gate recipes

| Need | Call |
|---|---|
| "this exact text is faithful and fresh" | `attests(id, hash, now_ts, max_age_s)` |
| "what is the state?" | `reliance_status` -> `RELIABLE` / `STALE` / `BLOCKED` / `UNKNOWN` |
| "was it judged against the source version I expect?" | `receipt_matches(id, definition_hash, summary_hash, source_digest)` |
| "why was it refused?" | `get_receipt(id, seq)` -> `defects`, `ungrounded`, `findings` |

Check `get_digest(id)["url"]` and `["scope"]` against what you accept as the authoritative source:
Precis attests fidelity to *that* source only.
