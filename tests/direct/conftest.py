"""Shared Direct Mode helpers for Precis."""
import datetime
import hashlib
import json
import sys

import pytest

BASE = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
URL = "https://docs.example.com/staking-terms"
URL_RE = r"^https://docs\.example\.com/staking-terms$"
SCOPE = "lockup period, yield, penalties and withdrawal restrictions"

SOURCE = (
    "Acme Staking Terms. Deposits are locked for 30 days. The annual yield is 5% paid monthly. "
    "Early withdrawal carries a 2% penalty. Acme may suspend withdrawals during a security incident."
)
SOURCE_REWRITTEN = (
    "Acme Staking Terms. Deposits are locked for 90 days. The annual yield is 5% paid monthly. "
    "Early withdrawal is not permitted. Acme may suspend withdrawals during a security incident."
)
SOURCE_CONTRA = (
    "Acme Staking Terms. Deposits are locked for 30 days. The annual yield is 5% paid monthly. "
    "Early withdrawal is not permitted, regardless of the 2% fee schedule. "
    "Acme may suspend withdrawals during a security incident."
)
SUMMARY = (
    "Deposits are locked for 30 days. The annual yield is 5%. "
    "Early withdrawal carries a 2% penalty."
)
SUMMARY_WRONG_FIGURE = (
    "Deposits are locked for 30 days. The annual yield is 7%. "
    "Early withdrawal carries a 2% penalty."
)

SUPPORT = [
    {"summary_quote": "locked for 30 days", "source_quote": "locked for 30 days"},
    {"summary_quote": "annual yield is 5%", "source_quote": "annual yield is 5% paid monthly"},
    {"summary_quote": "Early withdrawal carries a 2% penalty", "source_quote": "Early withdrawal carries a 2% penalty"},
]
OMISSION = {"kind": "OMISSION", "summary_quote": "",
            "source_quote": "Acme may suspend withdrawals during a security incident"}
CONTRADICTION = {"kind": "CONTRADICTION", "summary_quote": "Early withdrawal carries a 2% penalty",
                 "source_quote": "Early withdrawal is not permitted"}
ADDITION = {"kind": "ADDITION", "summary_quote": "The annual yield is 5%", "source_quote": ""}


def source_digest(text=SOURCE):
    return hashlib.sha256(" ".join(text.split()).encode("utf-8")).hexdigest()


def iso(offset_s: int) -> str:
    return (BASE + datetime.timedelta(seconds=offset_s)).isoformat().replace("+00:00", "Z")


def audit_json(support=None, findings=None):
    return json.dumps({"support": SUPPORT if support is None else support,
                       "findings": [] if findings is None else findings})


class Env:
    def __init__(self, vm, contract, alice, bob):
        self.vm, self.c = vm, contract
        self.owner, self.other = alice, bob
        self.t = 0
        self.prompts = []

    def warp(self, offset_s):
        # genlayer-test 0.29.2: vm.warp() does not refresh the already-loaded
        # gl.message_raw['datetime'] that the contract reads, so sync it here.
        self.vm.warp(iso(offset_s))
        sys.modules["genlayer.gl"].message_raw["datetime"] = iso(offset_s)

    def as_(self, who):
        self.vm.sender = who

    def page(self, body, status=200):
        self.vm.mock_web(URL_RE, {"method": "GET", "status": status, "body": body})

    def llm(self, reply):
        self.vm.mock_llm(r"PRECIS_AUDIT", reply)

    def reset(self):
        self.vm.clear_mocks()

    def register(self, summary=SUMMARY, who=None, scope=SCOPE, url=URL):
        self.as_(who or self.owner)
        return self.c.register(url, scope, summary)

    def audit(self, did, page=SOURCE, reply=None, dt=61, who=None, status=200):
        self.reset()
        self.page(page, status)
        self.llm(reply if reply is not None else audit_json())
        self.t += dt
        self.warp(self.t)
        self.as_(who or self.other)
        return self.c.audit(did)

    def audit_down(self, did, dt=61):
        self.reset()  # unmocked URL -> the web call raises -> unreachable
        self.t += dt
        self.warp(self.t)
        self.as_(self.other)
        return self.c.audit(did)

    def ready(self, summary=SUMMARY):
        did = self.register(summary)
        self.audit(did)
        return did


@pytest.fixture
def env(direct_vm, direct_deploy, direct_alice, direct_bob):
    direct_vm.check_pickling = True
    direct_vm.warp(iso(0))
    contract = direct_deploy("contracts/precis.py")
    # A real network delivers calldata addresses as genlayer Address, not raw bytes.
    from genlayer.py.types import Address  # importable once the loader has staged the SDK

    a, b = (Address(x) if isinstance(x, bytes) else x for x in (direct_alice, direct_bob))
    e = Env(direct_vm, contract, a, b)
    e.warp(0)
    return e
