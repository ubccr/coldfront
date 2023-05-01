#!/bin/bash
# $1 = database name
# $2 = dump file
docker exec -i coldfront-db-1 pg_restore --verbose --clean -U admin -d $1 < $2
