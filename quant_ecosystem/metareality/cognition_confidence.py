from dataclasses import dataclass


@dataclass
class CognitionConfidence:

    confidence_score: float

    uncertainty_score: float

    blindspot_risk: float