# ---------- Stage 1: Builder ----------
FROM python:3.11-slim-bookworm AS builder

WORKDIR /app

RUN pip install --no-cache-dir "poetry==2.2.1" "poetry-plugin-export"

COPY pyproject.toml poetry.lock* ./

# Export deps (ignore torch for now, install separately later)
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes

# Create venv and install deps
RUN python -m venv /venv \
 && /venv/bin/pip install --no-cache-dir -r requirements.txt \
 && /venv/bin/pip install --no-cache-dir torch==2.2.2+cpu -f https://download.pytorch.org/whl/cpu/torch_stable.html

COPY . .

# ---------- Stage 2: Runtime ----------
FROM python:3.11-slim-bookworm AS runtime

WORKDIR /app

# Install system runtime libs needed by torch/numpy
RUN apt-get update && apt-get install -y --no-install-recommends \
      libopenblas0-pthread libomp5 \
 && rm -rf /var/lib/apt/lists/*

# Copy virtualenv and project files from builder
COPY --from=builder /venv /venv
COPY --from=builder /app /app

# Ensure venv is active by default
ENV PATH="/venv/bin:$PATH"

# Run bot directly with python
CMD ["python", "src/quantumforge_rag_bot/company_docs_bot.py"]
