FROM ubuntu:latest

RUN apt-get update && \
    apt-get install -y python3 python3-dev python3-pip

RUN pip3 install jinja2 pyyaml

WORKDIR /app
