from typing import Dict, List, Optional

from .knowledge_pattern import KnowledgePattern


class KnowledgeRegistry:

    def __init__(self) -> None:
        self._patterns: Dict[str, KnowledgePattern] = {}

    def register(
        self,
        pattern: KnowledgePattern,
    ) -> None:

        key = pattern.pattern_id or pattern.category
        self._patterns[key] = pattern

    def get(
        self,
        pattern_id: str,
    ) -> Optional[KnowledgePattern]:

        return self._patterns.get(pattern_id)

    def all(
        self,
    ) -> List[KnowledgePattern]:

        return list(self._patterns.values())

    def count(
        self,
    ) -> int:

        return len(self._patterns)

    def clear(
        self,
    ) -> None:

        self._patterns.clear()

    def find_by_category(
        self,
        category: str,
    ) -> List[KnowledgePattern]:

        return [
            pattern
            for pattern in self._patterns.values()
            if pattern.category == category
        ]

    def keys(
        self,
    ) -> List[str]:

        return list(self._patterns.keys())
