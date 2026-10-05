from datetime import timedelta

import pendulum
from airflow.sdk import dag, task

from src.pipeline import WeatherPipeline


def _processing_date(context):
    return context["data_interval_start"].in_timezone("Europe/Minsk").date()


@dag(
    dag_id="weather_etl_pipeline",
    schedule="0 0 * * *",
    start_date=pendulum.datetime(2026, 1, 1, tz="Europe/Minsk"),
    catchup=False,
    max_active_runs=1,
    is_paused_upon_creation=False,
    default_args={"retries": 3, "retry_delay": timedelta(minutes=2), "execution_timeout": timedelta(minutes=10)},
)
def weather_etl_pipeline():
    @task
    def extract_to_bronze(**context):
        return WeatherPipeline().extract_to_bronze(_processing_date(context), context["run_id"])

    @task
    def validate_bronze(keys):
        WeatherPipeline().bronze.validate(keys)
        return keys

    @task
    def load_to_silver(keys, **context):
        WeatherPipeline().load_silver(keys, _processing_date(context))

    @task
    def validate_silver(**context):
        WeatherPipeline().warehouse.validate_silver(_processing_date(context))

    @task
    def build_gold_mart(**context):
        WeatherPipeline().warehouse.build_daily_summary(_processing_date(context))

    @task
    def validate_gold(**context):
        WeatherPipeline().warehouse.validate_gold(_processing_date(context))

    bronze = extract_to_bronze()
    valid_bronze = validate_bronze(bronze)
    loaded = load_to_silver(valid_bronze)
    silver_ok = validate_silver()
    gold = build_gold_mart()
    gold_ok = validate_gold()
    
    loaded >> silver_ok >> gold >> gold_ok


weather_etl_pipeline()
