FROM python:3.8

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app
COPY requirements.txt ./
RUN pip3 install -r requirements.txt
COPY . .

RUN python3 ./manage.py initial_setup
RUN python3 ./manage.py load_test_data

ENV DEBUG=True

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
