FROM python:3.12

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app
COPY requirements.txt ./
RUN pip3 install -r requirements.txt
RUN pip3 install setuptools
RUN pip3 install debugpy
COPY . .

RUN echo "yes" | python3 ./manage.py initial_setup
RUN python3 ./manage.py load_test_data

ENV DEBUG=True
ENV DJANGO_DEBUG=True
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
