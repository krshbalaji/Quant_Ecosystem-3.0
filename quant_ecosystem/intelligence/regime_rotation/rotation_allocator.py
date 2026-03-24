class RotationAllocator:

    def rotation_pressure(self, mismatch_score):

        if mismatch_score < 0.3:
            return 0.1

        if mismatch_score < 0.6:
            return 0.4

        return 0.8