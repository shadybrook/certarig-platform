# Simulator / stranger path only. Do not run this image privileged against GPIO.
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY certarig ./certarig
COPY config ./config
COPY skills ./skills
COPY studio ./studio
RUN pip install --no-cache-dir .
ENV CERTARIG_OPERATOR_KEY=sim-operator-key-000001 \
    CERTARIG_AGENT_KEY=sim-agent-key-0000000001 \
    CERTARIG_AUDITOR_KEY=sim-auditor-key-000001
EXPOSE 8080
CMD ["certarig", "sim", "serve", "--bind", "0.0.0.0", "--port", "8080"]
