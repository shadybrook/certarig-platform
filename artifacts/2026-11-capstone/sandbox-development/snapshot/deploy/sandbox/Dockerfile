# Built only after the host preflight. Jobs never download packages.
FROM python:3.12-slim-bookworm AS compiler
RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl ca-certificates libreadline-dev bison flex && rm -rf /var/lib/apt/lists/*
RUN curl -fsSL https://downloads.sourceforge.net/project/ngspice/ng-spice-rework/47/ngspice-47.tar.gz -o /tmp/ngspice.tar.gz && echo '894e649651f1838a14095e5a5439e7d3aa63e87ede14d283173fda4fcdef675f  /tmp/ngspice.tar.gz' | sha256sum -c - && tar -xzf /tmp/ngspice.tar.gz -C /tmp && cd /tmp/ngspice-47 && ./configure --with-x=no --disable-debug --enable-cider --enable-xspice && make -j2 && make install
FROM python:3.12-slim-bookworm
LABEL org.certarig.sandbox="v1"
COPY --from=compiler /usr/local/bin/ngspice /usr/local/bin/ngspice
COPY --from=compiler /usr/local/share/ngspice /usr/local/share/ngspice
COPY --from=compiler /usr/local/lib/ngspice /usr/local/lib/ngspice
RUN apt-get update && apt-get install -y --no-install-recommends libreadline8 libgomp1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY pyproject.toml README.md ./
COPY certarig ./certarig
COPY config ./config
COPY skills ./skills
RUN pip install --no-cache-dir --no-deps -e . && mkdir -p /out /scratch && chown 10001:10001 /out /scratch
ENV CERTARIG_SANDBOX_WORKER=1 PYTHONDONTWRITEBYTECODE=1
USER 10001:10001
CMD ["python", "-m", "certarig.sandbox.worker"]
