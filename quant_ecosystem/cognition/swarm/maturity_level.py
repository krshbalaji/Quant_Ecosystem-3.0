from enum import Enum


class MaturityLevel(str, Enum):
    EMERGING = "emerging"
    DEVELOPING = "developing"
    OPERATIONAL = "operational"
    INSTITUTIONAL = "institutional"
    SOVEREIGN = "sovereign"