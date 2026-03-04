"""Idea generation for Alpha Factory."""

from __future__ import annotations

from typing import Dict, Iterable, List


class IdeaGenerator:
    """Generates candidate genomes from mutation/cross/random paths."""

    def generate(
        self,
        genome_generator,
        parent_genomes: Iterable[Dict],
        random_count: int = 10,
        mutation_variants: int = 3,
        cross_children: int = 10,
    ) -> List[Dict]:
        parents = [dict(item) for item in list(parent_genomes or []) if item]
        out: List[Dict] = []
        out.extend(genome_generator.generate_random(count=max(1, int(random_count))))
        if parents:
            out.extend(genome_generator.generate_from_mutation(parents, variants_per_base=max(1, int(mutation_variants))))
            out.extend(genome_generator.generate_from_crossbreeding(parents, children_count=max(1, int(cross_children))))
        return out

