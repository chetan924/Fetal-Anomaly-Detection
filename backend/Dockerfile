# =============================================================================
# FETALAI v1.0 — PRODUCTION MULTI-STAGE DOCKER ARCHITECTURE
# =============================================================================
# Hardened non-root microservice images optimized for low memory & security:
# - Stage 'gateway': ML-Free Gateway (~150MB RSS, no PyTorch/YOLO/VTK)
# - Stage 'worker-pytorch': PyTorch CPU Workers (Plane, Brain, Lung, Placenta, Heart)
# - Stage 'worker-yolo': Ultralytics YOLO Workers (Spine, Bone)
# - Stage 'worker-face': Headless VTK Mesh Processing Worker (Face 3D)
# - Stage 'all-in-one': Universal production runtime (default)
# =============================================================================

# -----------------------------------------------------------------------------
# Base Image: Python 3.10 Slim with Non-Root Security User
# -----------------------------------------------------------------------------
FROM python:3.10-slim AS base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    WEB_CONCURRENCY=1

# Install core runtime dependencies (curl for healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create dedicated non-root application user
RUN groupadd -g 1000 fetalai && \
    useradd -u 1000 -g fetalai -m -s /bin/bash fetalai && \
    mkdir -p /app/storage/scans /app/storage/explainability /app/storage/worker_logs /app/storage/masks && \
    chown -R fetalai:fetalai /app

# -----------------------------------------------------------------------------
# Stage 1: Gateway (ML-Free, Memory-Optimized < 150MB RSS)
# -----------------------------------------------------------------------------
FROM base AS gateway

ENV PORT=8000

COPY requirements-gateway.txt ./
RUN pip install --no-cache-dir -r requirements-gateway.txt

COPY --chown=fetalai:fetalai . ./

USER fetalai
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]

# -----------------------------------------------------------------------------
# Stage 2: PyTorch CPU Worker (Plane, Brain, Lung, Placenta, Heart)
# -----------------------------------------------------------------------------
FROM base AS worker-pytorch

COPY requirements.txt ./
RUN pip install --no-cache-dir \
    fastapi==0.141.1 \
    uvicorn==0.52.1 \
    python-multipart==0.0.32 \
    pillow==12.2.0 \
    numpy==2.2.6 \
    scipy==1.15.3 \
    scikit-learn==1.7.2 \
    joblib==1.5.3 \
    httpx==0.28.1 \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    torch==2.12.1+cpu \
    torchvision==0.27.1+cpu

COPY --chown=fetalai:fetalai . ./

USER fetalai

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8100}/health || exit 1

CMD ["sh", "-c", "uvicorn app.workers.plane.worker:app --host 0.0.0.0 --port ${PORT:-8100} --workers 1"]

# -----------------------------------------------------------------------------
# Stage 3: YOLO Worker (Spine, Bone)
# -----------------------------------------------------------------------------
FROM base AS worker-yolo

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir \
    fastapi==0.141.1 \
    uvicorn==0.52.1 \
    python-multipart==0.0.32 \
    pillow==12.2.0 \
    numpy==2.2.6 \
    httpx==0.28.1 \
    ultralytics==8.4.32 \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    torch==2.12.1+cpu \
    torchvision==0.27.1+cpu

COPY --chown=fetalai:fetalai . ./

USER fetalai

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8101}/health || exit 1

CMD ["sh", "-c", "uvicorn app.workers.spine.worker:app --host 0.0.0.0 --port ${PORT:-8101} --workers 1"]

# -----------------------------------------------------------------------------
# Stage 4: Face 3D / VTK Worker
# -----------------------------------------------------------------------------
FROM base AS worker-face

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir \
    fastapi==0.141.1 \
    uvicorn==0.52.1 \
    python-multipart==0.0.32 \
    numpy==2.2.6 \
    pandas==2.3.3 \
    scikit-learn==1.7.2 \
    joblib==1.5.3 \
    httpx==0.28.1 \
    vtk==9.7.0

COPY --chown=fetalai:fetalai . ./

USER fetalai

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8107}/health || exit 1

CMD ["sh", "-c", "uvicorn app.workers.face.worker:app --host 0.0.0.0 --port ${PORT:-8107} --workers 1"]

# -----------------------------------------------------------------------------
# Stage 5: All-In-One Universal Image (Default)
# -----------------------------------------------------------------------------
FROM base AS all-in-one

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=fetalai:fetalai . ./

USER fetalai
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
