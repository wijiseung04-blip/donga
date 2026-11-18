# syntax=docker/dockerfile:1

# 1단계: 의존성 설치 후 테스트. 테스트가 실패하면 이미지가 만들어지지 않는다.
FROM python:3.15-slim AS test
WORKDIR /app
COPY requirements.txt pytest.ini ./
RUN pip install --no-cache-dir -r requirements.txt
COPY src ./src
COPY tests/test_main.py ./tests/
RUN pytest -q tests/test_main.py

# 2단계: 실행에 필요한 소스만 담은 경량 이미지
FROM python:3.15-slim
LABEL org.opencontainers.image.source="https://github.com/wijiseung04-blip/donga" \
      org.opencontainers.image.description="donga 예제 앱 (Python)" \
      org.opencontainers.image.licenses="MIT"
WORKDIR /app
COPY --from=test /app/src ./src
RUN useradd --create-home --uid 10001 appuser
USER appuser
ENTRYPOINT ["python", "src/donga_app/main.py"]
