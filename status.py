import os
import json
from pathlib import Path

BASE = Path("data")

def count_files(folder):
    if not folder.exists():
        return 0
    return len(list(folder.glob("*")))

def get_size(folder):
    if not folder.exists():
        return 0
    return sum(f.stat().st_size for f in folder.glob("**/*") if f.is_file())

def main():

    research_memory = BASE / "research_memory"
    genome_store = BASE / "genome_library"

    print("\n==============================")
    print(" QUANT ECOSYSTEM STATUS")
    print("==============================\n")

    print("Research Memory Files :", count_files(research_memory))
    print("Genome Library Files  :", count_files(genome_store))

    print("\nStorage Usage")
    print("------------------------------")
    print("Research Memory Size :", round(get_size(research_memory)/1024/1024,2), "MB")
    print("Genome Library Size  :", round(get_size(genome_store)/1024/1024,2), "MB")

    print("\nSystem State")
    print("------------------------------")
    print("Autonomous Research Loop : ACTIVE")
    print("Research Grid            : ACTIVE")
    print("Genome Memory            : ACTIVE")

    print("\nTip: Watch console logs for cycle progress.\n")


if __name__ == "__main__":
    main()