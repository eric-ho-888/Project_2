FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DAGSTER_HOME=/opt/dagster/dagster_home
ENV PYTHONPATH=/opt/sg-ev/dagster

WORKDIR /opt/sg-ev

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

COPY dagster/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY ingestion/ /opt/sg-ev/ingestion/
COPY dbt/sg_ev/ /opt/sg-ev/dbt/sg_ev/
COPY dagster/sg_ev_dagster/ /opt/sg-ev/dagster/sg_ev_dagster/
COPY workspace.yaml /opt/sg-ev/workspace.yaml

RUN mkdir -p /opt/dagster/dagster_home /opt/dagster/.dbt

RUN dbt deps --project-dir /opt/sg-ev/dbt/sg_ev

EXPOSE 3000 4000
