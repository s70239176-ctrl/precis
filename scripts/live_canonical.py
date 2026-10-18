"""Canonical Studionet deployment plus the live evidence run, in one pass.

  gltest scripts/live_canonical.py -s --network studionet

Deploys one canonical Precis, then runs: a faithful summary, a wrong-figure summary (deterministic
refusal), a materially silent summary, and the recovery path (revise the wrong-figure summary,
re-audit). Sources are httpbin.org/base64 echoes (same bytes for every validator).
State and tx hashes go to evidence/live_state.json (no key material: the deployer is the
genlayer-test default Studionet account, and only its public address is recorded).
"""
import json
import os
import time

from gltest import get_contract_factory, get_default_account
from gltest.assertions import tx_execution_succeeded
from gltest.utils import extract_contract_address

import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tests", "integration"))
from test_precis_studionet import (  # noqa: E402
    SCOPE, SOURCE, SOURCE_WITH_TRAP, SUMMARY, SUMMARY_SILENT, SUMMARY_WRONG_FIGURE, TX, WAIT, _url,
)

STATE = "evidence/live_state.json"


def _hash(r):
    return r.get("hash") or r.get("id")


def test_canonical():
    st = {"txs": [], "digests": {}}

    def save():
        os.makedirs("evidence", exist_ok=True)
        with open(STATE, "w", encoding="utf-8") as f:
            json.dump(st, f, indent=2)

    def send(label, call):
        r = call.transact(**TX)
        ok = tx_execution_succeeded(r)
        st["txs"].append({"label": label, "hash": _hash(r), "status": r.get("status_name") or str(r.get("status")), "ok": ok})
        save()
        print(label, "->", st["txs"][-1])
        assert ok, label

    acct = get_default_account()
    factory = get_contract_factory(contract_file_path="precis.py")
    receipt = factory.deploy_contract_tx(account=acct, consensus_max_rotations=3, **WAIT)
    assert tx_execution_succeeded(receipt)
    st["deployer"] = acct.address
    st["address"] = extract_contract_address(receipt)
    st["txs"].append({"label": "deploy", "hash": _hash(receipt),
                      "status": receipt.get("status_name") or str(receipt.get("status")), "ok": True})
    save()
    c = factory.build_contract(st["address"], account=acct)

    def new_digest(name, url, summary):
        send(f"register {name}", c.register(args=[url, SCOPE, summary]))
        did = c.digest_count_view(args=[]).call()
        st["digests"][name] = did
        save()
        return did

    ok = new_digest("faithful", _url(SOURCE), SUMMARY)
    send("audit faithful", c.audit(args=[ok]))
    bad = new_digest("wrong_figure", _url(SOURCE), SUMMARY_WRONG_FIGURE)
    send("audit wrong_figure", c.audit(args=[bad]))
    silent = new_digest("silent", _url(SOURCE_WITH_TRAP), SUMMARY_SILENT)
    send("audit silent", c.audit(args=[silent]))

    time.sleep(65)  # per-digest audit cooldown
    send("revise wrong_figure -> corrected summary", c.revise(args=[bad, SUMMARY]))
    send("re-audit wrong_figure after revise", c.audit(args=[bad]))

    for name, did in st["digests"].items():
        d = c.get_digest(args=[did]).call()
        n = d["receipt_count"]
        st.setdefault("results", {})[name] = {
            "status": d["status"], "version": d["version"], "receipts": n,
            "last_receipt": c.get_receipt(args=[did, n]).call(),
            "reliance": c.reliance_status(args=[did, d["last_ok_ts"] + 10, 3600]).call(),
        }
    save()
    print(json.dumps(st["results"], indent=2))
