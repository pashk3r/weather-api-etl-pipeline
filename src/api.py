from datetime import date
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.config import City
from src.fields import HOURLY_FIELDS


# Класс для взаимодействия с Open-Meteo API 
class OpenMeteoClient:
    def __init__(self, base_url: str, timeout: int = 30) -> None:
        self.base_url = base_url
        self.timeout = timeout
        retry = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
        )
        self.session = requests.Session()
        self.session.mount("https://", HTTPAdapter(max_retries=retry))

    # Запрашивает почасовой прогноз для города за выбранную дату
    def fetch(self, city: City, processing_date: date) -> tuple[dict[str, Any], dict[str, Any]]:
        params = {
            "latitude": city.latitude,
            "longitude": city.longitude,
            "hourly": ",".join(HOURLY_FIELDS),
            "timezone": "Europe/Minsk",
            "start_date": processing_date.isoformat(),
            "end_date": processing_date.isoformat(),
        }
        
        response = self.session.get(self.base_url, params=params, timeout=self.timeout)
        response.raise_for_status()
        payload = response.json()

        if not payload:
            raise ValueError(f"Open-Meteo вернуло пустой ответ для {city.name}")
        return payload, params
