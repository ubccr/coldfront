#!/bin/bash

docker build -f bootstrap/development/docker/images/app-config.Dockerfile -t coldfront-app-config bootstrap/development/docker
docker build -f bootstrap/development/docker/images/app-base.Dockerfile -t coldfront-app-base .
docker build -f bootstrap/development/docker/images/app-shell.Dockerfile -t coldfront-app-shell .
docker build -f bootstrap/development/docker/images/web.Dockerfile -t coldfront-web .
docker build -f bootstrap/development/docker/images/email-server.Dockerfile -t coldfront-email-server .
docker build -f bootstrap/development/docker/images/db-postgres-shell.Dockerfile -t coldfront-db-postgres-shell .
