#!/bin/sh
# Crée la base dédiée aux tests d'intégration du backend.
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE emmaus_test OWNER "$POSTGRES_USER";
EOSQL
