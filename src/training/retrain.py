"""One retraining step without Airflow (the DAG runs the same functions as separate tasks).

Run from the project root:  python -m src.training.retrain
"""

import json

from src.training.data import (
    load_batch,
    load_training_set,
    loaded_in_order,
    next_batch_id,
    read_batch,
    read_val,
    validate_batch,
)
from src.training.model import promote_if_better, train_candidate


def run_once() -> dict:
    batch_id = next_batch_id()
    if batch_id is None:
        return {"status": "nothing to do: all batches are loaded"}
    clean, report = validate_batch(read_batch(batch_id))
    load_batch(batch_id, clean)
    candidate = train_candidate(load_training_set(), read_val(), loaded_in_order())
    return {"batch": batch_id, "validation": report, "candidate": candidate, **promote_if_better(candidate)}


if __name__ == "__main__":
    print(json.dumps(run_once(), indent=2, default=str))
