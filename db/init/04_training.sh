#!/bin/bash
# Training data loaded by Airflow, and the etl_writer role that may write only there.
# Runs automatically on the first start of an empty database. On an existing database run it once by hand:
#   docker exec acme-db bash /docker-entrypoint-initdb.d/04_training.sh
set -euo pipefail

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE SCHEMA IF NOT EXISTS training;

    CREATE TABLE IF NOT EXISTS training.labeled_requests (
        id          bigserial PRIMARY KEY,
        batch_id    text NOT NULL,          -- "initial", "batch_01", ...
        text        text NOT NULL CHECK (length(text) > 0),
        intent      text NOT NULL,
        loaded_at   timestamptz NOT NULL DEFAULT now()
    );
    CREATE INDEX IF NOT EXISTS labeled_requests_batch_idx ON training.labeled_requests (batch_id);

    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'etl_writer') THEN
            CREATE ROLE etl_writer LOGIN PASSWORD '${ETL_DB_PASSWORD}';
        END IF;
    END
    \$\$;
    GRANT CONNECT ON DATABASE ${POSTGRES_DB} TO etl_writer;
    GRANT USAGE ON SCHEMA training TO etl_writer;
    GRANT SELECT, INSERT, DELETE ON training.labeled_requests TO etl_writer;
    GRANT USAGE ON SEQUENCE training.labeled_requests_id_seq TO etl_writer;
EOSQL
