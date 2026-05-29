from .diplomatic_position import DiplomaticPosition


class DiplomaticAlignmentEngine:

    def evaluate_alignment(
        self,
        left: DiplomaticPosition,
        right: DiplomaticPosition,
        domain: str,
    ) -> float:

        left_weight = left.strategic_weight(domain)
        right_weight = right.strategic_weight(domain)

        difference = abs(left_weight - right_weight)

        alignment = max(0.0, 1.0 - difference)

        return round(alignment, 4)