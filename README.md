# donga

동아대학교 OSS프로그래밍 수업용 프로젝트입니다.

## 프로젝트 개요

이 저장소는 OSS 프로그래밍 과정을 위한 초기 프로젝트 구조를 제공합니다. 기본적인 Python 개발 환경을 갖추고 있으며, 간단한 함수와 테스트를 포함한 시작점으로 사용할 수 있습니다.

## 구조

- `src/donga_app/`: 애플리케이션 코드
- `tests/`: 자동화 테스트
- `.gitignore`: Python 개발 환경에서 자주 생성되는 불필요한 파일 제외
- `LICENSE`: MIT 라이선스

## 시작하기

1. 가상 환경 생성
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```
2. 의존성 설치
   ```bash
   pip install -r requirements.txt
   ```
3. 실행 예시
   ```bash
   python -c "from donga_app.main import greet; print(greet('OSS'))"
   ```
4. 테스트 실행
   ```bash
   pytest
   ```

## 기본 기능

`greet(name)` 함수는 간단한 인사 메시지를 반환합니다.
