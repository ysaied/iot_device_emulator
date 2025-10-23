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
COPY . /opt/iot/client
COPY configs /opt/iot/configs

RUN find /opt/iot/client -type f -name "*.sh" -exec chmod +x {} \; && \
    find /opt/iot/client/device_scripts -type f -name "*.py" -exec chmod +x {} \;

ENV PYTHONPATH=/opt/iot

WORKDIR /opt/iot/client
ENTRYPOINT ["./entrypoint.sh"]
