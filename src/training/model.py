"""Train a candidate router, log it to MLflow, promote it if it beats the champion."""

import mlflow.sklearn
from mlflow.exceptions import MlflowException
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.pipeline import FeatureUnion, Pipeline

import mlflow
from mlflow import MlflowClient
from src.preprocess import TARGET

EXPERIMENT = "router-retraining"
MODEL_NAME = "intent-router"
ALIAS = "champion"
MIN_GAIN = 0.005  # a new model must be at least this much better on val macro-F1


def build_pipeline() -> Pipeline:
    """The baseline from notebooks/02_baseline.ipynb: word + char TF-IDF, logistic regression."""
    word = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)
    char = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=2, sublinear_tf=True)
    return Pipeline(
        [("features", FeatureUnion([("word", word), ("char", char)])), ("clf", LogisticRegression(max_iter=3000))]
    )


def train_candidate(train_df, val_df, batch_ids: list[str]) -> dict:
    mlflow.set_experiment(EXPERIMENT)
    with mlflow.start_run(run_name=f"retrain-{len(batch_ids)}-batches") as run:
        model = build_pipeline().fit(train_df["text"], train_df[TARGET])
        pred = model.predict(val_df["text"])
        f1 = float(f1_score(val_df[TARGET], pred, average="macro"))
        mlflow.log_params(
            {"model": "logreg", "features": "word+char", "train_rows": len(train_df),
             "batches": len(batch_ids), "last_batch": batch_ids[-1]}
        )
        mlflow.log_metrics({"val_macro_f1": f1, "val_accuracy": float(accuracy_score(val_df[TARGET], pred))})
        info = mlflow.sklearn.log_model(model, name="model")
    return {"run_id": run.info.run_id, "model_uri": info.model_uri, "val_macro_f1": f1}


def champion_score(client: MlflowClient) -> float | None:
    try:
        version = client.get_model_version_by_alias(MODEL_NAME, ALIAS)
    except MlflowException:
        return None  # no registered model or no champion yet
    return float(version.tags["val_macro_f1"])


def promote_if_better(candidate: dict, min_gain: float = MIN_GAIN) -> dict:
    client = MlflowClient()
    current = champion_score(client)
    f1 = candidate["val_macro_f1"]

    if current is not None and f1 < current + min_gain:
        client.set_tag(candidate["run_id"], "decision", "kept_champion")
        return {"decision": "kept_champion", "champion_f1": current, "candidate_f1": f1}

    version = mlflow.register_model(candidate["model_uri"], MODEL_NAME)
    client.set_model_version_tag(MODEL_NAME, version.version, "val_macro_f1", f"{f1:.6f}")
    client.set_registered_model_alias(MODEL_NAME, ALIAS, version.version)
    client.set_tag(candidate["run_id"], "decision", "promoted")
    return {"decision": "promoted", "version": int(version.version), "previous_f1": current, "candidate_f1": f1}
