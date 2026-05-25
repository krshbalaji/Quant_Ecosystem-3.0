from quant_ecosystem.governance import (
    adaptive_policy_engine,
    approval_workflow,
)


def test_allow_policy():
    result = (
        adaptive_policy_engine
        .evaluate_policy(
            {"risk_score": 20}
        )
    )

    assert result["action"] == "ALLOW"


def test_review_policy():
    result = (
        adaptive_policy_engine
        .evaluate_policy(
            {"risk_score": 70}
        )
    )

    assert result["action"] == "REVIEW"


def test_block_policy():
    result = (
        adaptive_policy_engine
        .evaluate_policy(
            {"risk_score": 95}
        )
    )

    assert result["action"] == "BLOCK"


def test_override():
    result = (
        adaptive_policy_engine
        .emergency_override(
            True
        )
    )

    assert result["override"] is True


def test_request_create():
    result = (
        approval_workflow
        .create_request(
            "D1",
            {"symbol": "SBIN"},
        )
    )

    assert result["status"] == "PENDING"


def test_approve():
    req = (
        approval_workflow
        .create_request(
            "D1",
            {},
        )
    )

    result = (
        approval_workflow
        .approve(req)
    )

    assert result["status"] == "APPROVED"


def test_reject():
    req = (
        approval_workflow
        .create_request(
            "D1",
            {},
        )
    )

    result = (
        approval_workflow
        .reject(req)
    )

    assert result["status"] == "REJECTED"


def test_execute_gate():
    policy = {
        "action": "REVIEW",
        "approval_required": True,
    }

    req = (
        approval_workflow
        .create_request(
            "D1",
            {},
        )
    )

    approval_workflow.approve(req)

    result = (
        approval_workflow
        .execute_gate(
            policy,
            req,
        )
    )

    assert result is True