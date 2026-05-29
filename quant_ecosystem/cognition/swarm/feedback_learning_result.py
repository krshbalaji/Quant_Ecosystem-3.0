from dataclasses import dataclass


@dataclass(frozen=True)
class FeedbackLearningResult:
    pattern_count: int