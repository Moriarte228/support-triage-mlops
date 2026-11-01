# Airflow plus the libraries the training code needs.
# Versions come from the project's .venv: a model trained here must load in the assistant.
FROM apache/airflow:3.3.0
COPY requirements-airflow.txt /tmp/requirements-airflow.txt
RUN pip install --no-cache-dir "apache-airflow==3.3.0" -r /tmp/requirements-airflow.txt
