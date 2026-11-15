# Reviewed base index pins both supported Linux architectures; see api-inputs.json.
FROM python:3.13-slim-bookworm@sha256:a5a7017efc5969e00ae2b91c8eb0631049a569652aa4ffc4501769049ae45c72 AS dependencies
ENV PYTHONDONTWRITEBYTECODE=1 PIP_DISABLE_PIP_VERSION_CHECK=1
COPY docker/api-requirements.lock /tmp/api-requirements.lock
# Wheels only: no unpinned build backend/compiler or dependency upgrade.
RUN python -m pip --isolated install --no-cache-dir --no-compile \
      --index-url https://pypi.org/simple --only-binary=:all: --require-hashes \
      --target /opt/api-deps -r /tmp/api-requirements.lock \
 && PYTHONPATH=/opt/api-deps python -m pip check

# Test-only target proves Docker's actual context filtering, never a serving image.
FROM scratch AS context-audit
COPY . /context/

FROM python:3.13-slim-bookworm@sha256:a5a7017efc5969e00ae2b91c8eb0631049a569652aa4ffc4501769049ae45c72 AS api
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/opt/api-deps:/app
WORKDIR /app
COPY --from=dependencies /opt/api-deps /opt/api-deps
# Copy reviewed Python sources directly: no local-package build tools are invoked.
COPY src/opponent_intelligence/ /app/opponent_intelligence/
COPY docker/api-inputs.json docker/api-requirements.lock /usr/share/nfl-oi/
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:8000/openapi.json', timeout=2).close()"
# Factory validates explicit operator configuration and loads once before serving.
CMD ["python", "-m", "uvicorn", "opponent_intelligence.api:app_from_env", "--factory", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--lifespan", "on", "--no-proxy-headers"]
