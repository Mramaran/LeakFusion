# --- Stage 1: build the React UI --------------------------------------------
FROM node:20-slim AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

# --- Stage 2: Python API that also serves the built UI ----------------------
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
# libgomp1: OpenMP runtime needed by xgboost / scikit-learn wheels.
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && apt-get clean

# Hugging Face Spaces run containers as uid 1000.
RUN useradd -m -u 1000 user
WORKDIR /app

COPY requirements-api.txt ./
RUN pip install -r requirements-api.txt

COPY --chown=user leakfusion/ ./leakfusion/
# Stage 1 re-exports physical constants from syn-engine/src (see
# leakfusion/src/residuals/constants.py), so ship that package too.
COPY --chown=user syn-engine/src/ ./syn-engine/src/
COPY --chown=user --from=web /web/dist ./web/dist

# Models are not in git; they must be present in leakfusion/models/ at build time.
RUN test -f leakfusion/models/calibration.json \
    && test -f leakfusion/models/cusum_config.json \
    || (echo "ERROR: leakfusion/models/ is missing model files (see README)" && exit 1)

USER user
EXPOSE 7860
CMD ["uvicorn", "leakfusion.api.main:app", "--host", "0.0.0.0", "--port", "7860"]
