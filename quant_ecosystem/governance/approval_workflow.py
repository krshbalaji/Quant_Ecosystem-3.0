class ApprovalWorkflow:

    def create_request(
        self,
        decision_id,
        decision_payload,
    ):
        return {
            "decision_id": decision_id,
            "payload": decision_payload,
            "status": "PENDING",
        }

    def approve(
        self,
        request,
        approver="SYSTEM",
    ):
        request["status"] = "APPROVED"
        request["approver"] = approver
        return request

    def reject(
        self,
        request,
        approver="SYSTEM",
    ):
        request["status"] = "REJECTED"
        request["approver"] = approver
        return request

    def execute_gate(
        self,
        policy_result,
        approval_request=None,
    ):
        if policy_result["action"] == "BLOCK":
            return False

        if policy_result[
            "approval_required"
        ]:
            if not approval_request:
                return False

            return (
                approval_request["status"]
                == "APPROVED"
            )

        return True


approval_workflow = ApprovalWorkflow()