from dataclasses import dataclass


@dataclass(frozen=True)
class FederationCognitionGovernanceReport:
    governance_action: str
    review_required: bool