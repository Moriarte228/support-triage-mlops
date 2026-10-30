#!/bin/bash
# Read-only role for the assistant. Runs once, on the first start of an empty database.
set -euo pipefail

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE ROLE assistant_ro LOGIN PASSWORD '${ASSISTANT_DB_PASSWORD}';
    ALTER ROLE assistant_ro SET default_transaction_read_only = on;
    GRANT CONNECT ON DATABASE ${POSTGRES_DB} TO assistant_ro;
    GRANT USAGE ON SCHEMA reference TO assistant_ro;
    GRANT SELECT ON ALL TABLES IN SCHEMA reference TO assistant_ro;
    ALTER DEFAULT PRIVILEGES IN SCHEMA reference GRANT SELECT ON TABLES TO assistant_ro;
EOSQL
