#!/bin/bash
DB_OWNER=admin
DB_NAME=${@:(-2):1}
DUMP_FILE=${@: -1}

if [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]] ; then
    echo "Usage: `basename $0` [OPTION] name-of-database path-to-dump-file"
    exit 0
fi

if [[ "$1" == "-k" || "$1" == "--kill-connections" ]] ; then
    echo "TERMINATING DATABASE CONNECTIONS..."
    docker exec -i coldfront-db-1 \
    psql -U $DB_OWNER -c "SELECT pg_terminate_backend(pid) 
    FROM pg_stat_activity 
    WHERE pid <> pg_backend_pid() AND datname = '$DB_NAME';" $DB_NAME
fi

echo DROPPING DATABASE...
docker exec -i coldfront-db-1 \
psql -U $DB_OWNER -c "DROP DATABASE $DB_NAME;" postgres

echo CREATING DATABASE...
docker exec -i coldfront-db-1 \
psql -U $DB_OWNER -c "CREATE DATABASE $DB_NAME OWNER $DB_OWNER;" postgres

echo LOADING DATABASE...
docker exec -i coldfront-db-1 \
pg_restore -U $DB_OWNER -d $DB_NAME < $DUMP_FILE

echo MODIFYING PERMISSIONS...
docker exec -i coldfront-db-1 \
psql -U $DB_OWNER -c "ALTER SCHEMA public OWNER TO $DB_OWNER;" $DB_NAME

echo DONE.