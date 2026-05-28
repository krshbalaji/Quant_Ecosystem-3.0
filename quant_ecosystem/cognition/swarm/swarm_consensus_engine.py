from typing import Dict, List


class SwarmConsensusEngine:

    def compute_consensus(
        self,
        votes: List[Dict],
    ) -> Dict:

        if not votes:
            return {
                "consensus": None,
                "confidence": 0.0,
                "participants": 0,
            }

        scorebook = {}

        for vote in votes:
            option = vote["decision"]
            weight = float(vote.get("weight", 1.0))

            scorebook.setdefault(option, 0.0)
            scorebook[option] += weight

        winner = max(scorebook.items(), key=lambda x: x[1])

        total_weight = sum(scorebook.values())

        confidence = (
            winner[1] / total_weight
            if total_weight > 0
            else 0.0
        )

        return {
            "consensus": winner[0],
            "confidence": confidence,
            "participants": len(votes),
        }