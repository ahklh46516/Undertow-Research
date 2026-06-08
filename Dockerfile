# Undertow — the engine and the static site in one image.
#
#   docker run --rm -p 8000:8000 ghcr.io/nickbauman77/undertow-research:latest
#   open http://localhost:8000/            (whitepaper)
#   open http://localhost:8000/terminal.html  (dashboard)
#
# On start the engine recomputes a fresh snapshot (falling back to the bundled
# data.json if offline), then serves web/.

FROM python:3.12-slim

LABEL org.opencontainers.image.title="Undertow Research" \
      org.opencontainers.image.description="The macro layer for on-chain markets." \
      org.opencontainers.image.source="https://github.com/nickbauman77/Undertow-Research" \
      org.opencontainers.image.licenses="MIT"

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY engine/ ./engine/
COPY web/ ./web/

EXPOSE 8000

CMD ["sh", "-c", "python -m engine.pipeline || true; python -m http.server 8000 --directory web"]
