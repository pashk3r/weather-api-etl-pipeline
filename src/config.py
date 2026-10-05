import os
from dataclasses import dataclass

# Класс для создания объекта города, который мы будем использовать в нашем пайплайне
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


# Класс для хранения настроек пайплайна
@dataclass(frozen=True)
class Settings:
    minio_endpoint: str = os.getenv("MINIO_ENDPOINT", "minio:9000")
    minio_access_key: str = os.environ["MINIO_ROOT_USER"]
    minio_secret_key: str = os.environ["MINIO_ROOT_PASSWORD"]
    dwh_dsn: str = os.environ["DWH_DSN"]
    open_meteo_url: str = "https://api.open-meteo.com/v1/forecast"
    minio_bucket: str = "weather"
