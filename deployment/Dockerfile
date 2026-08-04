FROM python:3.11-slim

WORKDIR /app

# git is needed by the mirror-drift engine (git ls-remote) and the proposal-opener.
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt

# EVERYTHING the self-heal loop imports or shells out to MUST be in the image, or the
# scheduler's jobs ImportError at runtime while the heartbeat stays green (a lie). The
# preflight in automation.scheduler fails fast if any of these is missing.
COPY automation/ ./automation/
COPY registry/ ./registry/
COPY third_party/ ./third_party/   # vendored procyber.semantic kernel (the responder's core)
COPY engines/ ./engines/           # mirror_drift_engine etc. (executors + detectors)
COPY tools/ ./tools/               # check_/lift_/generate_/validate_ CLIs the detectors run

ENV PYTHONUNBUFFERED=1

EXPOSE 5000
