from typing import Dict, List, Optional

from .learning_pattern import LearningPattern


class LearningPatternRegistry:

    def __init__(self) -> None:
        self._patterns: Dict[str, LearningPattern] = {}

    def register(
        self,
        pattern: LearningPattern,
    ) -> None:

        self._patterns[pattern.pattern_id] = pattern

    def get(
        self,
        pattern_id: str,
    ) -> Optional[LearningPattern]:

        return self._patterns.get(pattern_id)

    def all(
        self,
    ) -> List[LearningPattern]:

        return list(self._patterns.values())

    def count(
        self,
    ) -> int:

        return len(self._patterns)

    def clear(
        self,
    ) -> None:

        self._patterns.clear()

    def find_by_type(
        self,
        pattern_type: str,
    ) -> List[LearningPattern]:

        return [
            pattern
            for pattern in self._patterns.values()
            if pattern.pattern_type == pattern_type
        ]

    def keys(
        self,
    ) -> List[str]:

        return list(self._patterns.keys())
