FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/models/hf-cache \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    HF_HUB_DISABLE_TELEMETRY=1 \
    OMP_NUM_THREADS=2 \
    MKL_NUM_THREADS=2 \
    OPENBLAS_NUM_THREADS=2

WORKDIR /app

COPY pyproject.toml ./
COPY requirements-runtime.lock ./
COPY src/ ./src/
COPY configs/ ./configs/
COPY LICENSE LICENSE-MIT-LEGACY.txt ./
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir --require-hashes -r requirements-runtime.lock \
    && python -m pip install --no-cache-dir --no-deps .

RUN addgroup --system --gid 10001 ats \
    && adduser --system --uid 10001 --ingroup ats --home /nonexistent ats \
    && mkdir -p /tmp/ats-analysis /models \
    && chown -R 10001:10001 /tmp/ats-analysis

USER 10001:10001
EXPOSE 8000
CMD ["python", "-m", "src.app.asgi"]
