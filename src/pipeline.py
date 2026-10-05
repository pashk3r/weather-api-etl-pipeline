from datetime import date

from src.api import OpenMeteoClient
from src.bronze import BronzeStorage
from src.config import CITIES, Settings
from src.transformer import WeatherTransformer
from src.warehouse import WeatherWarehouse


# Класс для управления процессом ETL погодных данных
class WeatherPipeline:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        self.api = OpenMeteoClient(self.settings.open_meteo_url)
        self.bronze = BronzeStorage(self.settings)
        self.transformer = WeatherTransformer()
        self.warehouse = WeatherWarehouse(self.settings.dwh_dsn)

    # Метод для извлечения данных в Bronze-хранилище
    def extract_to_bronze(self, processing_date: date, run_id: str) -> list[str]:
        keys = []
        for city in CITIES:
            payload, params = self.api.fetch(city, processing_date)
            keys.append(self.bronze.save(city, processing_date, run_id, params, payload))
        return keys

    # Метод для загрузки данных в Silver-хранилище
    def load_silver(self, keys: list[str], processing_date: date) -> None:
        records = [
            record
            for key in keys
            for record in self.transformer.transform(self.bronze.read(key), processing_date)
        ]
        self.warehouse.replace_observations(records, processing_date)
