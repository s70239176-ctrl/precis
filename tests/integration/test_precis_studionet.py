"""Real-consensus Studionet tests. Each test deploys its own disposable contract.

Run:  gltest tests/integration/ -v -s --network studionet

Sources are served by httpbin.org/base64/<urlsafe-base64>, which echoes the decoded bytes back, so
every validator fetches exactly the same public document and no hosting is needed. The whole URL
must stay under the contract's 200-char limit, so the documents are short. Keep the `=` padding.
"""
import base64
import hashlib

from gltest import get_contract_factory, get_default_account
from gltest.assertions import tx_execution_succeeded

SCOPE = "lockup period, yield and early-exit costs"
SOURCE = "Acme Terms. Deposits are locked for 30 days. Yield is 5% yearly. Early exit costs 2%."
SUMMARY = "Deposits are locked for 30 days. Yield is 5% yearly. Early exit costs 2%."
SUMMARY_WRONG_FIGURE = "Deposits are locked for 30 days. Yield is 7% yearly. Early exit costs 2%."
SOURCE_WITH_TRAP = (
    "Acme Terms. Deposits are locked for 30 days. Yield is 5% yearly. "
    "Acme may freeze all withdrawals indefinitely."
)
SUMMARY_SILENT = "Deposits are locked for 30 days. Yield is 5% yearly. Withdrawals are always available."

WAIT = {"wait_interval": 10000, "wait_retries": 30}
TX = {"consensus_max_rotations": 3, **WAIT}


def _url(doc: str) -> str:
    url = "https://httpbin.org/base64/" + base64.urlsafe_b64encode(doc.encode()).decode()
    assert len(url) <= 200
    return url


def _deploy():
    factory = get_contract_factory(contract_file_path="precis.py")
    return factory.deploy(account=get_default_account(), consensus_max_rotations=3, **WAIT)


def _register(c, url, summary):
    r = c.register(args=[url, SCOPE, summary]).transact(**TX)
    assert tx_execution_succeeded(r)
    assert c.digest_count_view(args=[]).call() == 1  # setup really created state
    return 1


def test_deploy_and_public_surface():
    c = _deploy()
    did = _register(c, _url(SOURCE), SUMMARY)
    d = c.get_digest(args=[did]).call()
    assert d["status"] == "UNAUDITED" and d["version"] == 1 and len(d["summary_hash"]) == 64
    assert c.reliance_status(args=[did, 1_800_000_000, 3600]).call() == "UNKNOWN"
    assert c.is_faithful(args=[did]).call() is False


def test_live_faithful_summary_is_attested():
    c = _deploy()
    did = _register(c, _url(SOURCE), SUMMARY)
    r = c.audit(args=[did]).transact(**TX)
    assert tx_execution_succeeded(r)
    d = c.get_digest(args=[did]).call()
    assert d["status"] == "FAITHFUL" and d["last_defects"] == 0 and d["receipt_count"] == 1
    assert d["last_source_digest"] == hashlib.sha256(" ".join(SOURCE.split()).encode()).hexdigest()
    rc = c.get_receipt(args=[did, 1]).call()
    assert rc["outcome"] == "FAITHFUL" and rc["findings"] == [] and rc["ungrounded"] == []
    assert c.is_faithful(args=[did]).call() is True
    assert c.attests(args=[did, d["summary_hash"], d["last_ok_ts"] + 10, 3600]).call() is True
    assert c.attests(args=[did, "0" * 64, d["last_ok_ts"] + 10, 3600]).call() is False


def test_live_wrong_figure_is_refused_deterministically():
    c = _deploy()
    did = _register(c, _url(SOURCE), SUMMARY_WRONG_FIGURE)
    r = c.audit(args=[did]).transact(**TX)
    assert tx_execution_succeeded(r)
    rc = c.get_receipt(args=[did, 1]).call()
    assert rc["outcome"] == "MISLEADING" and rc["defects"] == 1 and rc["ungrounded"] == ["7%"]
    assert c.is_faithful(args=[did]).call() is False
    d = c.get_digest(args=[did]).call()
    assert c.reliance_status(args=[did, d["last_ok_ts"], 3600]).call() == "BLOCKED"


def test_live_material_silence_is_not_attested():
    c = _deploy()
    did = _register(c, _url(SOURCE_WITH_TRAP), SUMMARY_SILENT)
    r = c.audit(args=[did]).transact(**TX)
    assert tx_execution_succeeded(r)
    d = c.get_digest(args=[did]).call()
    # Settlement-critical dimension only: it must NOT be FAITHFUL. INCOMPLETE vs MISLEADING is a
    # diagnostic distinction an honest validator may draw differently.
    assert d["status"] in ("INCOMPLETE", "MISLEADING", "UNAUDITED")
    assert c.is_faithful(args=[did]).call() is False


def test_live_unreadable_source_fails_closed():
    c = _deploy()
    did = _register(c, "https://httpbin.org/status/404", SUMMARY)
    r = c.audit(args=[did]).transact(**TX)
    assert tx_execution_succeeded(r)  # UNREACHABLE is a legitimate consensus result
    rc = c.get_receipt(args=[did, 1]).call()
    assert rc["outcome"] == "UNREACHABLE" and rc["fingerprint"] == ""
    assert c.get_digest(args=[did]).call()["status"] == "UNAUDITED"
    assert c.is_faithful(args=[did]).call() is False
