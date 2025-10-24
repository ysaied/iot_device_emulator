FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends iproute2 && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/iot/hub

COPY requirements.txt /tmp/requirements.txt
RUN python -m pip install --upgrade pip && pip install --no-cache-dir -r /tmp/requirements.txt

COPY . /opt/iot/hub

ENV PYTHONPATH=/opt/iot/hub

ENTRYPOINT ["./entrypoint.sh"]
