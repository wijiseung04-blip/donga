# syntax=docker/dockerfile:1

# 1단계: 의존성 설치 후 테스트. 테스트가 실패하면 이미지가 만들어지지 않는다.
FROM python:3.15-slim AS test
WORKDIR /app
COPY requirements.txt pytest.ini ./
RUN pip install --no-cache-dir -r requirements.txt
COPY src ./src
COPY tests/test_main.py tests/test_server.py ./tests/
RUN pytest -q tests/test_main.py tests/test_server.py

# 2단계: 실행에 필요한 소스만 담은 경량 이미지
FROM python:3.15-slim
LABEL org.opencontainers.image.source="https://github.com/wijiseung04-blip/donga" \
      org.opencontainers.image.description="donga 예제 앱 (Python HTTP 서버)" \
      org.opencontainers.image.licenses="MIT"
WORKDIR /app
COPY --from=test /app/src ./src
ENV PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    PORT=8080
RUN useradd --create-home --uid 10001 appuser
USER appuser
EXPOSE 8080
# 로컬 Docker·Compose용 헬스체크 (Cloud Run은 배포 설정의 startup/liveness probe를 사용)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/healthz', timeout=2)"
CMD ["python", "-m", "donga_app.server"]
