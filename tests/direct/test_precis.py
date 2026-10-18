"""Public-surface and lifecycle tests for Precis (Direct Mode, real contract code, mocked web/LLM)."""
import json

import pytest

from conftest import (
    ADDITION, CONTRADICTION, OMISSION, SCOPE, SOURCE, SOURCE_CONTRA, SOURCE_REWRITTEN, SUMMARY, SUMMARY_WRONG_FIGURE,
    SUPPORT, URL, audit_json, source_digest,
)


def _raises(fn, *args, match="EXPECTED"):
    with pytest.raises(Exception) as ei:
        fn(*args)
    assert match in str(ei.value)


# ------------------------------------------------------------------ registration


def test_register_stores_and_counts(env):
    did = env.register()
    assert did == 1 and env.c.digest_count_view() == 1
    d = env.c.get_digest(did)
    assert d["url"] == URL and d["scope"] == SCOPE and d["summary"] == SUMMARY
    assert d["status"] == "UNAUDITED" and d["version"] == 1 and d["active"] is True
    assert len(d["summary_hash"]) == 64 and len(d["definition_hash"]) == 64
    assert env.c.register(URL, SCOPE, SUMMARY + " It is audited.") == 2  # independent record
    assert env.c.get_digest(1)["summary"] == SUMMARY


@pytest.mark.parametrize("url", [
    "http://docs.example.com/x", "https://user@docs.example.com/x", "https://docs.example.com:8443/x",
    "https://localhost/x", "https://10.0.0.1/x", "https://Docs.Example.com/x", "https://docs.example.com/../x",
    "https://nodots/x", "ftp://docs.example.com/x", "https://" + "a" * 250 + ".com/x", "https://x.internal/a",
])
def test_register_rejects_bad_urls(env, url):
    env.as_(env.owner)
    _raises(env.c.register, url, SCOPE, SUMMARY)
    assert env.c.digest_count_view() == 0


@pytest.mark.parametrize("scope,summary", [
    ("", SUMMARY), ("   ", SUMMARY), ("x" * 241, SUMMARY),
    (SCOPE, "too short"), (SCOPE, "x" * 1201),
    (SCOPE, "Tiny. Brief. Ok. Yes. No. Hmm. Fine. Sure. Okay. Done."),  # no sentence reaches the claim minimum
    (SCOPE, " ".join("Sentence number %d is here." % i for i in range(9))),  # 9 claims > 8
])
def test_register_rejects_bad_scope_or_summary(env, scope, summary):
    env.as_(env.owner)
    _raises(env.c.register, URL, scope, summary)
    assert env.c.digest_count_view() == 0


def test_register_normalises_whitespace(env):
    env.as_(env.owner)
    did = env.c.register(URL, "  " + SCOPE + "  ", SUMMARY.replace(". ", ".\n\n  "))
    assert env.c.get_digest(did)["summary"] == SUMMARY and env.c.get_digest(did)["scope"] == SCOPE


# ------------------------------------------------------------------ verdicts


def test_faithful_summary_attested(env):
    did = env.register()
    r = env.audit(did)
    assert r["outcome"] == "FAITHFUL" and r["defects"] == 0 and r["status"] == "FAITHFUL"
    rc = env.c.get_receipt(did, 1)
    assert rc["source_digest"] == source_digest() and rc["findings"] == [] and rc["ungrounded"] == []
    assert len(rc["fingerprint"]) == 64
    d = env.c.get_digest(did)
    assert env.c.is_faithful(did) is True and env.c.status_of(did) == "FAITHFUL"
    assert env.c.reliance_status(did, d["last_ok_ts"] + 10, 3600) == "RELIABLE"
    assert env.c.attests(did, d["summary_hash"], d["last_ok_ts"] + 10, 3600) is True
    assert env.c.receipt_matches(did, d["definition_hash"], d["summary_hash"], source_digest()) is True


def test_omission_is_incomplete_and_blocks(env):
    did = env.register()
    r = env.audit(did, reply=audit_json(findings=[OMISSION]))
    assert r["outcome"] == "INCOMPLETE" and r["defects"] == 4
    assert env.c.is_faithful(did) is False
    d = env.c.get_digest(did)
    assert env.c.reliance_status(did, d["last_ok_ts"], 3600) == "BLOCKED"
    assert env.c.attests(did, d["summary_hash"], d["last_ok_ts"], 3600) is False
    assert env.c.get_receipt(did, 1)["findings"] == [OMISSION]


def test_contradiction_is_misleading(env):
    did = env.register()
    r = env.audit(did, page=SOURCE_CONTRA, reply=audit_json(support=SUPPORT[:2], findings=[CONTRADICTION]))
    assert r["outcome"] == "MISLEADING" and r["defects"] == 2 and env.c.status_of(did) == "MISLEADING"


def test_addition_is_misleading(env):
    did = env.register()
    r = env.audit(did, reply=audit_json(support=[SUPPORT[0], SUPPORT[2]], findings=[ADDITION]))
    assert r["outcome"] == "MISLEADING" and r["defects"] == 8


def test_combined_defects_bitmask(env):
    did = env.register()
    r = env.audit(did, page=SOURCE_CONTRA, reply=audit_json(support=SUPPORT[:2], findings=[CONTRADICTION, OMISSION]))
    assert r["defects"] == 2 | 4 and r["outcome"] == "MISLEADING"


def test_wrong_figure_refused_without_model(env):
    did = env.register(SUMMARY_WRONG_FIGURE)
    calls = []
    orig = env.vm._match_llm_mock
    env.vm._match_llm_mock = lambda *a, **k: (calls.append(a), orig(*a, **k))[1]
    r = env.audit(did)
    assert calls == []  # the deterministic floor decided; no model call was made
    assert r["outcome"] == "MISLEADING" and r["defects"] == 1
    rc = env.c.get_receipt(did, 1)
    assert rc["ungrounded"] == ["7%"] and rc["findings"] == []


def test_figure_normalisation_commas_percent_and_addresses(env):
    src = ("Fund holds 1,500,000 USD at 0xAbCdEf0123456789 with a 2.5 % fee. Lock is 30 days. "
           "Early exit pays a penalty of 4 %. Withdrawals can be paused.")
    summ = ("The fund holds 1500000 USD at 0xabcdef0123456789. The fee is 2.5%. "
            "Lock is 30 days. Early exit pays 4% penalty.")
    did = env.register(summ)
    support = [{"summary_quote": "holds 1500000 USD", "source_quote": "holds 1,500,000 USD"},
               {"summary_quote": "The fee is 2.5%", "source_quote": "with a 2.5 % fee"},
               {"summary_quote": "Lock is 30 days", "source_quote": "Lock is 30 days"},
               {"summary_quote": "Early exit pays 4% penalty", "source_quote": "Early exit pays a penalty of 4 %"}]
    r = env.audit(did, page=src, reply=audit_json(support=support))
    assert r["outcome"] == "FAITHFUL"


def test_list_markers_are_not_figures(env):
    summ = "1. Deposits are locked for 30 days.\n2. The annual yield is 5%.\n3. Early withdrawal carries a 2% penalty."
    did = env.register(summ)
    assert env.audit(did)["outcome"] == "FAITHFUL"


def test_html_source_is_stripped(env):
    page = "<html><script>var x=999;</script><body><p>" + SOURCE.replace(". ", ".</p><p>") + "</p></body></html>"
    did = env.register()
    r = env.audit(did, page=page, reply=audit_json())
    assert r["outcome"] == "FAITHFUL"  # 999 inside script is not a source figure, nor a summary figure


# ------------------------------------------------------------------ fail closed


@pytest.mark.parametrize("reply", [
    "not json at all",
    json.dumps({"support": [], "findings": []}),  # sentences unaccounted for
    json.dumps({"findings": []}),  # support missing
    json.dumps({"support": SUPPORT}),  # findings missing
    audit_json(support=SUPPORT[:2]),  # last sentence unaccounted for
    audit_json(support=[{"summary_quote": "locked for 30 days", "source_quote": "invented quote not in source"}] + SUPPORT[1:]),
    audit_json(support=[{"summary_quote": "not in the summary", "source_quote": "locked for 30 days"}] + SUPPORT[1:]),
    audit_json(findings=[{"kind": "MAYBE", "summary_quote": "x" * 8, "source_quote": ""}]),
    audit_json(findings=[{"kind": "OMISSION", "summary_quote": "", "source_quote": "invented clause not in source"}]),
    audit_json(findings=[OMISSION | {"extra": 1}]),
    audit_json(findings=[OMISSION] * 7),  # more than MAX_FINDINGS
    audit_json(support=SUPPORT + [SUPPORT[0]] * 10),  # more than MAX_SUPPORT
    audit_json(support=[dict(SUPPORT[0], summary_quote=5)] + SUPPORT[1:]),
    audit_json(findings="none"),
    json.dumps([1, 2, 3]),
])
def test_unclassifiable_model_output_fails_closed(env, reply):
    did = env.ready()
    before = env.c.get_digest(did)
    r = env.audit(did, reply=reply)
    assert r["outcome"] == "UNCLASSIFIED" and r["defects"] == 0
    after = env.c.get_digest(did)
    assert after["status"] == "FAITHFUL" == before["status"]  # prior verdict untouched, not upgraded
    assert after["nonok_streak"] == 1 and after["last_fingerprint"] == before["last_fingerprint"]
    assert env.c.get_receipt(did, 2)["outcome"] == "UNCLASSIFIED"


def test_fenced_json_is_recovered(env):
    did = env.register()
    r = env.audit(did, reply="```json\n" + audit_json() + "\n```")
    assert r["outcome"] == "FAITHFUL"


def test_model_cannot_upgrade_unclassified_into_faithful_by_silence(env):
    did = env.register()
    r = env.audit(did, reply=json.dumps({"support": [], "findings": []}))
    assert r["outcome"] == "UNCLASSIFIED" and env.c.status_of(did) == "UNAUDITED"
    assert env.c.is_faithful(did) is False
    assert env.c.reliance_status(did, 10**9, 3600) == "UNKNOWN"


def test_unreachable_source_degrades_reliance_without_changing_verdict(env):
    did = env.ready()
    ok_ts = env.c.get_digest(did)["last_ok_ts"]
    assert env.audit_down(did)["outcome"] == "UNREACHABLE"
    assert env.c.status_of(did) == "FAITHFUL" and env.c.get_digest(did)["nonok_streak"] == 1
    assert env.c.reliance_status(did, ok_ts + 5, 3600) == "RELIABLE"
    env.audit_down(did)
    env.audit_down(did)
    assert env.c.get_digest(did)["nonok_streak"] == 3
    assert env.c.reliance_status(did, ok_ts + 5, 3600) == "UNKNOWN"
    assert env.c.attests(did, env.c.get_digest(did)["summary_hash"], ok_ts + 5, 3600) is False


def test_http_error_status_is_unreachable(env):
    did = env.register()
    assert env.audit(did, status=404)["outcome"] == "UNREACHABLE"
    assert env.audit(did, status=503)["outcome"] == "UNREACHABLE"
    assert env.c.status_of(did) == "UNAUDITED"


def test_empty_body_is_unreachable(env):
    did = env.register()
    assert env.audit(did, page="   ")["outcome"] == "UNREACHABLE"


def test_oversize_source_is_refused_and_blocks_reliance(env):
    did = env.ready()
    ok_ts = env.c.get_digest(did)["last_ok_ts"]
    r = env.audit(did, page=SOURCE + " filler" * 3000)
    assert r["outcome"] == "OVERSIZE"
    assert env.c.get_digest(did)["nonok_streak"] == 3  # immediately UNKNOWN
    assert env.c.reliance_status(did, ok_ts + 5, 3600) == "UNKNOWN"


def test_recovery_after_unreachable(env):
    did = env.ready()
    env.audit_down(did)
    assert env.audit(did)["outcome"] == "FAITHFUL"
    assert env.c.get_digest(did)["nonok_streak"] == 0


def test_source_change_flips_a_previously_faithful_summary(env):
    did = env.ready()
    assert env.c.is_faithful(did) is True
    # the source quietly changes: 30 -> 90 days; the summary figure is now ungrounded
    r = env.audit(did, page=SOURCE_REWRITTEN)
    assert r["outcome"] == "MISLEADING" and env.c.is_faithful(did) is False
    d = env.c.get_digest(did)
    assert d["last_source_digest"] == source_digest(SOURCE_REWRITTEN)
    assert env.c.receipt_matches(did, d["definition_hash"], d["summary_hash"], source_digest()) is False
    assert env.c.receipt_matches(did, d["definition_hash"], d["summary_hash"], source_digest(SOURCE_REWRITTEN)) is True


# ------------------------------------------------------------------ lifecycle


def test_audit_cooldown_and_boundary(env):
    did = env.register()
    env.audit(did, dt=61)
    env.reset(); env.page(SOURCE); env.llm(audit_json())
    env.t += 59
    env.warp(env.t)
    env.as_(env.other)
    _raises(env.c.audit, did)
    env.t += 1  # exactly 60 s after the previous audit
    env.warp(env.t)
    assert env.c.audit(did)["outcome"] == "FAITHFUL"


def test_audit_unknown_and_inactive(env):
    env.as_(env.other)
    _raises(env.c.audit, 1)
    did = env.register()
    env.as_(env.owner)
    env.c.deactivate(did)
    _raises(env.c.audit, did)
    assert env.c.reliance_status(did, 10, 3600) == "UNKNOWN"


def test_only_owner_can_revise_or_deactivate(env):
    did = env.register()
    env.as_(env.other)
    _raises(env.c.revise, did, SUMMARY + " Extra claim sentence here.", match="only the owner")
    _raises(env.c.deactivate, did, match="only the owner")
    assert env.c.get_digest(did)["version"] == 1 and env.c.get_digest(did)["active"] is True


def test_revise_clears_verdict_and_pins_new_hash(env):
    did = env.ready()
    old = env.c.get_digest(did)
    env.as_(env.owner)
    v = env.c.revise(did, SUMMARY + " Acme may suspend withdrawals during a security incident.")
    assert v == 2
    d = env.c.get_digest(did)
    assert d["status"] == "UNAUDITED" and d["summary_hash"] != old["summary_hash"]
    assert d["last_fingerprint"] == "" and d["last_source_digest"] == "" and d["last_defects"] == 0
    assert env.c.attests(did, old["summary_hash"], old["last_ok_ts"], 3600) is False  # old pin no longer valid
    assert env.c.reliance_status(did, old["last_ok_ts"], 3600) == "UNKNOWN"
    assert env.c.get_receipt(did, 1)["summary_hash"] == old["summary_hash"]  # history keeps its own hash
    _raises(env.c.revise, did, SUMMARY + " Acme may suspend withdrawals during a security incident.")


def test_revise_rejects_bad_summary(env):
    did = env.register()
    env.as_(env.owner)
    _raises(env.c.revise, did, "tiny")
    _raises(env.c.revise, did, SUMMARY)  # unchanged
    assert env.c.get_digest(did)["version"] == 1


def test_revised_summary_can_be_audited_faithful(env):
    did = env.register(SUMMARY_WRONG_FIGURE)
    assert env.audit(did)["outcome"] == "MISLEADING"
    env.as_(env.owner)
    env.c.revise(did, SUMMARY)
    assert env.audit(did)["outcome"] == "FAITHFUL"
    assert env.c.get_receipt(did, 1)["version"] == 1 and env.c.get_receipt(did, 2)["version"] == 2


def test_receipts_ring_buffer_rotates(env):
    did = env.register()
    for _ in range(10):
        env.audit(did)
    assert env.c.get_digest(did)["receipt_count"] == 10
    _raises(env.c.get_receipt, did, 2)  # rotated out
    _raises(env.c.get_receipt, did, 0)
    _raises(env.c.get_receipt, did, 11)
    assert env.c.get_receipt(did, 3)["seq"] == 3 and env.c.get_receipt(did, 10)["seq"] == 10


def test_digests_are_independent(env):
    a = env.register()
    b = env.register(SUMMARY_WRONG_FIGURE)
    env.audit(a)
    env.audit(b)
    assert env.c.status_of(a) == "FAITHFUL" and env.c.status_of(b) == "MISLEADING"
    assert env.c.get_receipt(a, 1)["ungrounded"] == [] and env.c.get_receipt(b, 1)["ungrounded"] == ["7%"]


def test_reliance_freshness_boundary(env):
    did = env.ready()
    ts = env.c.get_digest(did)["last_ok_ts"]
    assert env.c.reliance_status(did, ts + 3600, 3600) == "RELIABLE"
    assert env.c.reliance_status(did, ts + 3601, 3600) == "STALE"
    _raises(env.c.reliance_status, did, ts, 0)
    _raises(env.c.reliance_status, did, ts, 365 * 24 * 3600 + 1)
    _raises(env.c.reliance_status, 99, ts, 3600)


def test_views_reject_unknown_ids(env):
    for fn, args in [(env.c.get_digest, (7,)), (env.c.status_of, (7,)), (env.c.is_faithful, (7,)),
                     (env.c.attests, (7, "x", 1, 3600)), (env.c.receipt_matches, (7, "a", "b", "c"))]:
        _raises(fn, *args)


def test_receipt_matches_requires_a_real_digest(env):
    did = env.register()
    d = env.c.get_digest(did)
    assert env.c.receipt_matches(did, d["definition_hash"], d["summary_hash"], "") is False  # never audited
