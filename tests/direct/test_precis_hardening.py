"""Forged-leader tests: a well-formed but substantively false leader result must be rejected.

`direct_vm.run_validator` feeds the validator a leader result of our choosing while the validator
re-fetches the (mocked) source and re-judges it itself.
"""
import copy

import pytest

from conftest import (
    ADDITION, CONTRADICTION, OMISSION, SOURCE, SOURCE_CONTRA, SOURCE_REWRITTEN, SUMMARY, SUMMARY_WRONG_FIGURE,
    SUPPORT, audit_json, source_digest,
)


def _obs(reach="OK", verdict="FAITHFUL", defects=0, ungrounded=None, findings=None, claims=3, digest=None):
    if reach != "OK":
        return {"reach": reach, "verdict": "", "defects": 0, "ungrounded": [], "findings": [],
                "claims": 0, "source_digest": ""}
    return {"reach": "OK", "verdict": verdict, "defects": defects, "ungrounded": ungrounded or [],
            "findings": findings or [], "claims": claims, "source_digest": digest or source_digest()}


def _validate(env, leader_result):
    return env.vm.run_validator(leader_result=leader_result)


def _armed(env, page=SOURCE, reply=None, summary=SUMMARY):
    """Run one real audit so the audit validator is the registered one, then re-arm mocks."""
    did = env.register(summary)
    env.audit(did, page=page, reply=reply)
    env.reset()
    env.page(page)
    env.llm(reply if reply is not None else audit_json())
    return did


# ----------------------------------------------------------- honest results


def test_honest_faithful_accepted(env):
    _armed(env)
    assert _validate(env, _obs()) is True


def test_honest_omission_accepted(env):
    _armed(env, reply=audit_json(findings=[OMISSION]))
    assert _validate(env, _obs(verdict="INCOMPLETE", defects=4, findings=[OMISSION])) is True


def test_honest_contradiction_accepted(env):
    _armed(env, page=SOURCE_CONTRA, reply=audit_json(support=SUPPORT[:2], findings=[CONTRADICTION]))
    assert _validate(env, _obs(verdict="MISLEADING", defects=2, findings=[CONTRADICTION],
                               digest=source_digest(SOURCE_CONTRA))) is True


def test_honest_figure_refusal_accepted(env):
    _armed(env, summary=SUMMARY_WRONG_FIGURE)
    assert _validate(env, _obs(verdict="MISLEADING", defects=1, ungrounded=["7%"])) is True


def test_honest_unreachable_accepted(env):
    _armed(env)
    env.reset()  # validator also cannot read the source
    assert _validate(env, _obs(reach="UNREACHABLE")) is True


# ----------------------------------------------------------- substantively false leaders


def test_forged_faithful_rejected_when_validator_sees_contradiction(env):
    _armed(env, page=SOURCE_CONTRA, reply=audit_json(support=SUPPORT[:2], findings=[CONTRADICTION]))
    assert _validate(env, _obs(digest=source_digest(SOURCE_CONTRA))) is False


def test_forged_faithful_rejected_when_validator_sees_wrong_figure(env):
    _armed(env, summary=SUMMARY_WRONG_FIGURE)
    assert _validate(env, _obs()) is False  # leader hid the 7% figure


def test_forged_misleading_rejected_when_validator_finds_it_faithful(env):
    _armed(env)
    forged = _obs(verdict="MISLEADING", defects=2, findings=[CONTRADICTION])
    assert _validate(env, forged) is False  # grounded in neither the validator's source nor verdict


def test_forged_incomplete_rejected_when_validator_finds_it_faithful(env):
    _armed(env)
    assert _validate(env, _obs(verdict="INCOMPLETE", defects=4, findings=[OMISSION])) is False


def test_forged_figure_refusal_rejected_when_figures_are_grounded(env):
    _armed(env)
    forged = _obs(verdict="MISLEADING", defects=1, ungrounded=["7%"])
    assert _validate(env, forged) is False


def test_forged_figure_list_must_match_exactly(env):
    _armed(env, summary=SUMMARY_WRONG_FIGURE)
    assert _validate(env, _obs(verdict="MISLEADING", defects=1, ungrounded=["8%"])) is False
    assert _validate(env, _obs(verdict="MISLEADING", defects=1, ungrounded=["7%", "99"])) is False


def test_invented_finding_quote_rejected(env):
    _armed(env, reply=audit_json(findings=[OMISSION]))
    invented = {"kind": "OMISSION", "summary_quote": "", "source_quote": "Acme owns all deposits forever"}
    assert _validate(env, _obs(verdict="INCOMPLETE", defects=4, findings=[invented])) is False
    invented_summary = {"kind": "ADDITION", "summary_quote": "this sentence is not in the summary", "source_quote": ""}
    assert _validate(env, _obs(verdict="MISLEADING", defects=8, findings=[invented_summary])) is False


def test_source_digest_must_match_validators_snapshot(env):
    _armed(env)
    assert _validate(env, _obs(digest="0" * 64)) is False
    assert _validate(env, _obs(digest=source_digest(SOURCE_REWRITTEN))) is False


def test_leader_cannot_censor_by_claiming_unclassified(env):
    _armed(env)  # validator can classify -> must reject an UNCLASSIFIED claim
    assert _validate(env, _obs(reach="UNCLASSIFIED")) is False


def test_unclassified_accepted_only_when_validator_cannot_classify_either(env):
    _armed(env)
    env.reset(); env.page(SOURCE); env.llm("not json")
    assert _validate(env, _obs(reach="UNCLASSIFIED")) is True


def test_leader_cannot_claim_unreachable_when_source_is_readable(env):
    _armed(env)
    assert _validate(env, _obs(reach="UNREACHABLE")) is False
    assert _validate(env, _obs(reach="OVERSIZE")) is False


def test_leader_cannot_claim_ok_when_validator_cannot_read(env):
    _armed(env)
    env.reset()
    assert _validate(env, _obs()) is False


def test_unreachable_vs_oversize_must_agree(env):
    _armed(env)
    env.reset(); env.page(SOURCE + " filler" * 3000)
    assert _validate(env, _obs(reach="OVERSIZE")) is True
    assert _validate(env, _obs(reach="UNREACHABLE")) is False


# ----------------------------------------------------------- malformed leader results


def _bad(**over):
    o = _obs()
    o.update(over)
    return o


@pytest.mark.parametrize("name,forged", [
    ("not_a_dict", [1, 2, 3]),
    ("none", None),
    ("string", "FAITHFUL"),
    ("missing_key", {k: v for k, v in _obs().items() if k != "claims"}),
    ("extra_key", _bad(extra=1)),
    ("unknown_reach", _bad(reach="MAYBE")),
    ("unknown_verdict", _bad(verdict="GREAT")),
    ("lowercase_verdict", _bad(verdict="faithful")),
    ("bool_defects", _bad(defects=False)),
    ("float_defects", _bad(defects=0.0)),
    ("string_defects", _bad(defects="0")),
    ("hex_defects", _bad(defects="0x0")),
    ("negative_defects", _bad(defects=-1)),
    ("unknown_defect_bit", _bad(defects=16, verdict="MISLEADING")),
    ("bool_claims", _bad(claims=True)),
    ("float_claims", _bad(claims=3.0)),
    ("zero_claims", _bad(claims=0)),
    ("too_many_claims", _bad(claims=9)),
    ("short_digest", _bad(source_digest="abc")),
    ("uppercase_digest", _bad(source_digest=source_digest().upper())),
    ("verdict_defects_mismatch", _bad(verdict="FAITHFUL", defects=2, findings=[CONTRADICTION])),
    ("faithful_with_findings", _bad(findings=[OMISSION])),
    ("defect_bit_without_finding", _bad(verdict="INCOMPLETE", defects=4)),
    ("finding_without_defect_bit", _bad(verdict="FAITHFUL", defects=0, findings=[OMISSION])),
    ("figure_bit_without_figures", _bad(verdict="MISLEADING", defects=1)),
    ("figures_without_figure_bit", _bad(ungrounded=["7%"])),
    ("figure_refusal_with_findings", _bad(verdict="MISLEADING", defects=1 | 4, ungrounded=["7%"], findings=[OMISSION])),
    ("too_many_figures", _bad(verdict="MISLEADING", defects=1, ungrounded=[str(i) for i in range(9)])),
    ("non_string_figure", _bad(verdict="MISLEADING", defects=1, ungrounded=[7])),
    ("empty_figure", _bad(verdict="MISLEADING", defects=1, ungrounded=[""])),
    ("bad_finding_kind", _bad(verdict="MISLEADING", defects=2, findings=[dict(CONTRADICTION, kind="BAD")])),
    ("contradiction_missing_quote", _bad(verdict="MISLEADING", defects=2, findings=[dict(CONTRADICTION, source_quote="")])),
    ("omission_with_summary_quote", _bad(verdict="INCOMPLETE", defects=4, findings=[dict(OMISSION, summary_quote="x")])),
    ("addition_with_source_quote", _bad(verdict="MISLEADING", defects=8, findings=[dict(ADDITION, source_quote="x")])),
    ("finding_not_dict", _bad(verdict="INCOMPLETE", defects=4, findings=["omission"])),
    ("finding_extra_key", _bad(verdict="INCOMPLETE", defects=4, findings=[dict(OMISSION, extra=1)])),
    ("too_many_findings", _bad(verdict="INCOMPLETE", defects=4, findings=[OMISSION] * 7)),
    ("not_ok_with_verdict", {**_obs(reach="UNREACHABLE"), "verdict": "FAITHFUL"}),
    ("not_ok_with_digest", {**_obs(reach="UNREACHABLE"), "source_digest": source_digest()}),
    ("not_ok_with_defects", {**_obs(reach="UNREACHABLE"), "defects": 4}),
    ("truthy_string_bool_digest", _bad(source_digest=True)),
])
def test_malformed_leader_results_rejected(env, name, forged):
    _armed(env)
    assert _validate(env, copy.deepcopy(forged)) is False


def test_leader_error_result_rejected(env):
    _armed(env)
    from genlayer.gl.vm import UserError  # noqa: F401  (the SDK type a failed leader produces)

    assert _validate(env, ValueError("leader crashed")) is False
