"""
quant_ecosystem/genome_library/genome_library.py
=================================================
Stable re-export shim so SystemFactory can always do:

    from quant_ecosystem.genome_library.genome_library import GenomeLibrary

The authoritative implementation lives in alpha_genome/genome_library.py
which already has all enhanced features (GenomeRecord, top_genomes,
update_fitness, store_record, ResearchMemoryLayer bridge, etc.).
"""
import os
import json

from quant_ecosystem.alpha_genome.genome_library import (  # noqa: F401
    AlphaGenomeLibrary,
    GenomeLibrary,
    GenomeRecord,
)

__all__ = ["GenomeLibrary", "AlphaGenomeLibrary", "GenomeRecord"]

def save_genome(self, genome):

    path = os.path.join(self.storage_path, f"{genome.id}.json")

    with open(path, "w") as f:
        json.dump(genome.to_dict(), f)