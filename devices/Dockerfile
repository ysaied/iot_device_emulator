FROM python:3.11-slim AS builder

ENV VIRTUAL_ENV=/opt/venv
RUN python -m venv "${VIRTUAL_ENV}"
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential gcc && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip && pip install --no-cache-dir -r /tmp/requirements.txt

FROM python:3.11-slim AS runtime

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        iproute2 \
        iputils-ping \
        isc-dhcp-client \
        supervisor \
        curl \
        ffmpeg \
        tcpdump && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder "${VIRTUAL_ENV}" "${VIRTUAL_ENV}"

WORKDIR /opt/iot
COPY . /opt/iot/devices
COPY configs /opt/iot/configs

RUN find /opt/iot/devices -type f -name "*.sh" -exec chmod +x {} \; && \
    find /opt/iot/devices/scripts -type f -name "*.py" -exec chmod +x {} \;

ENV PYTHONPATH=/opt/iot

WORKDIR /opt/iot/devices
ENTRYPOINT ["./entrypoint.sh"]
