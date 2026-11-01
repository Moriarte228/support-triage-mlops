"""Continuous training of the intent router.

Each run takes the next labelled batch, checks it, loads it into Postgres, retrains
the router on everything loaded so far and promotes the new model in the MLflow
Model Registry if it beats the current champion on the validation set.

The logic lives in src/training; this file only orders the steps. Heavy imports
(pandas, sklearn, mlflow) happen inside the tasks: Airflow re-reads this file
every few seconds and must not load them just to draw the graph.
"""

from datetime import datetime, timedelta

from airflow.sdk import dag, task

try:
    from airflow.sdk.exceptions import AirflowSkipException
except ImportError:  # older Airflow versions
    from airflow.exceptions import AirflowSkipException


@dag(
    dag_id="retrain_router",
    schedule="@daily",
    start_date=datetime(2026, 10, 1),
    catchup=False,       # do not run once for every day since start_date
    max_active_runs=1,   # batches must be loaded one after another
    default_args={"retries": 1, "retry_delay": timedelta(minutes=1)},
    tags=["mlops", "router"],
)
def retrain_router():
    @task
    def pick_batch() -> str:
        from src.training.data import next_batch_id

        batch_id = next_batch_id()
        if batch_id is None:
            raise AirflowSkipException("all batches are already loaded")
        return batch_id

    @task
    def validate_batch(batch_id: str) -> dict:
        from src.training.data import read_batch, validate_batch

        _, report = validate_batch(read_batch(batch_id))  # raises BatchError: the run fails, nothing is loaded
        return report

    @task
    def load_batch(batch_id: str, report: dict) -> int:
        from src.training.data import load_batch, read_batch, validate_batch

        clean, _ = validate_batch(read_batch(batch_id))  # DataFrames do not travel between tasks: read again
        return load_batch(batch_id, clean)

    @task
    def train(rows_loaded: int) -> dict:
        from src.training.data import load_training_set, loaded_in_order, read_val
        from src.training.model import train_candidate

        return train_candidate(load_training_set(), read_val(), loaded_in_order())

    @task
    def promote(candidate: dict) -> dict:
        from src.training.model import promote_if_better

        return promote_if_better(candidate)

    batch_id = pick_batch()
    report = validate_batch(batch_id)
    rows = load_batch(batch_id, report)
    promote(train(rows))


retrain_router()
