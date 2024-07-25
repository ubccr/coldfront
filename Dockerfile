FROM python:3.9-slim-bullseye


RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    && apt-get install -y netcat \
    && apt-get install -y default-libmysqlclient-dev build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 config --user set global.progress_bar off

WORKDIR /opt
COPY requirements.txt ./
RUN pip3 install --upgrade pip
RUN pip3 install -r /opt/requirements.txt
COPY . .
RUN python3 setup.py build
RUN python3 setup.py install
RUN pip3 install /opt
ENV DEBUG="True"

EXPOSE 8000


CMD [ "/opt/entrypoint.sh" ]