FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        mosquitto \
        mosquitto-clients \
        nginx \
        snmpd \
        supervisor \
        iproute2 \
        tcpdump \
        openssl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /opt/iot/server

COPY requirements.txt /tmp/requirements.txt
RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt

COPY . /opt/iot/server
COPY configs/mosquitto.conf /etc/mosquitto/mosquitto.conf
COPY configs/nginx.conf /etc/nginx/nginx.conf
COPY configs/snmpd.conf /etc/snmp/snmpd.conf

RUN mkdir -p /data/logs && mkdir -p /run/supervisor
RUN openssl req -x509 -nodes -days 365 -subj "/CN=iot-server" \
    -newkey rsa:2048 \
    -keyout /etc/nginx/selfsigned.key \
    -out /etc/nginx/selfsigned.crt

ENV PYTHONPATH=/opt/iot

VOLUME ["/data"]

EXPOSE 80 443 104 161/udp 162/udp 502 554 5683/udp 47808/udp 5060/udp 1883

CMD ["supervisord", "-c", "/opt/iot/server/supervisord.conf"]
