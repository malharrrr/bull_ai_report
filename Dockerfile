FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim AS runner

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libfreetype6 \
    libpng16-16 \
    libjpeg62-turbo \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

RUN mkdir uploads outputs

COPY templates/ ./templates/
COPY static/ ./static/
COPY app.py extractor.py analyst_agent.py report_generator.py logging_config.py ./

EXPOSE 5000

ENV PYTHONUNBUFFERED=1 \
    FLASK_ENV=production

CMD ["gunicorn", \
     "--bind", "0.0.0.0:5000", \
     "--timeout", "120", \
     "--workers", "2", \
     "--worker-class", "sync", \
     "--keep-alive", "5", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "100", \
     "app:app"]