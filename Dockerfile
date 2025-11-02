
# Minimal Dockerfile for Scam_GEO Banking
FROM python:3.11-slim

# System deps for tesseract and graphviz
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr graphviz fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy project
COPY ./src /app/src
COPY ./pyproject.toml ./README.md* ./requirements.txt* /app/

# Install Python deps
RUN pip install --no-cache-dir -e /app

ENV PYTHONPATH=/app/src
ENV LOG_LEVEL=INFO

CMD ["python", "-m", "scamgeo_banking.cli.app", "--help"]
