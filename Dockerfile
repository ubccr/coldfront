# Builder Image
FROM python:3.9-slim-bullseye

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        default-libmysqlclient-dev \
        libpq-dev \
        git \
        pkg-config && \
    apt-get clean -y


WORKDIR /opt
COPY . .
RUN pip3 install -r ./requirements.txt
RUN python setup.py build
RUN python setup.py install
RUN pip3 install ./




COPY entrypoint2.sh /opt

ENV DJANGO_SETTINGS_MODULE="coldfront.config.database"

EXPOSE 8000


CMD [ "/opt/entrypoint2.sh" ]