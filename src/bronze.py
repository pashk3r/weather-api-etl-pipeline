import json
from datetime import date, datetime, timezone
from io import BytesIO
from typing import Any

from minio import Minio

from src.config import CITIES, City, Settings


class BronzeStorage:
    def __init__(self, settings: Settings) -> None:
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=False,
        )
        self.bucket = settings.minio_bucket

    # Метод сохраняет сырые данные в MinIO в формате JSON
    def save(
        self,
        city: City,
        processing_date: date,
        run_id: str,
        request_params: dict[str, Any],
        raw_response: dict[str, Any],
    ) -> str:
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)

        key = f"weather-forecast/bronze/year={processing_date:%Y}/month={processing_date:%m}/day={processing_date:%d}/{city.name.lower()}.json"
        document = {
            "metadata": {
                "city_id": city.id,
                "city": city.name,
                "latitude": city.latitude,
                "longitude": city.longitude,
                "request_params": request_params,
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "processing_date": processing_date.isoformat(),
                "pipeline_run_id": run_id,
            },
            "raw_response": raw_response,
        }
        body = json.dumps(document, ensure_ascii=False).encode()
        self.client.put_object(self.bucket, key, BytesIO(body), len(body), content_type="application/json")
        return key

    # Метод читает данные из MinIO по ключу и возвращает их в виде словаря
    def read(self, key: str) -> dict[str, Any]:
        response = self.client.get_object(self.bucket, key)
        try:
            return json.loads(response.read())
        finally:
            response.close()
            response.release_conn()

    # Метод проверяет, что в хранилище Bronze есть данные для всех шести 
    # городов и что у каждого документа есть почасовые данные
    def validate(self, keys: list[str]) -> None:
        documents = [self.read(key) for key in keys]
        city_ids = {document.get("metadata", {}).get("city_id") for document in documents}
        if city_ids != {city.id for city in CITIES}:
            raise ValueError("В Bronze должны быть указаны достоверные данные по всем шести городам")
        if any(not document.get("raw_response", {}).get("hourly") for document in documents):
            raise ValueError("В Bronze документе нет почасовых данных")
