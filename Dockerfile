FROM python:3.11-slim AS base

WORKDIR /app

# Copy source files
COPY simple_logger.py .
COPY utilities.py .

# Create logs directory
RUN mkdir -p logs

FROM base AS test

# Copy test files
COPY test_simple_logger.py .

# Run tests as build step (fails build if tests fail)
RUN echo "Running basic functionality tests..." && \
    python -m unittest test_simple_logger -v && \
    echo "\n✅ All tests passed!"

# Default command for test stage
CMD ["python", "-m", "unittest", "discover", "-v"]

FROM base AS run

# Default command runs the demo
CMD ["python", "simple_logger.py"]
