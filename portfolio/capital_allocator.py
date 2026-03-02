class CapitalAllocator:

    def allocate(self, strategies):

        total_score = sum([s["score"] for s in strategies])

        allocation = {}

        for s in strategies:

            weight = s["score"] / total_score

            allocation[s["name"]] = round(weight, 4)

        return allocation