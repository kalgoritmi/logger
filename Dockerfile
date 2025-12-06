FROM python:3.11-slim AS base

WORKDIR /app

RUN useradd -m -u 1000 logger && \
    chown -R logger:logger /app

COPY --chown=logger:logger simple_logger.py .
COPY --chown=logger:logger utilities.py .

RUN mkdir -p logs && chown -R logger:logger logs

USER logger

FROM base AS test

COPY --chown=logger:logger test_simple_logger.py .
COPY --chown=logger:logger test_utilities.py .

# Default command for test stage
CMD ["python", "-m", "unittest", "discover", "-v"]

FROM base AS run

# Default command runs the demo
CMD ["python", "simple_logger.py"]
