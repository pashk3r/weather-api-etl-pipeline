import os
from dataclasses import dataclass


@dataclass(frozen=True)
class City:
    id: int
    name: str
    latitude: float
    longitude: float


CITIES = (
    City(1, "Minsk", 53.9006, 27.5590),
    City(2, "Mogilev", 53.8945, 30.3306),
    City(3, "Brest", 52.0976, 23.6877),
    City(4, "Grodno", 53.6667, 23.8167),
    City(5, "Gomel", 52.4411, 31.0000),
    City(6, "Vitebsk", 55.1904, 30.2049),
)


