"""donga 예제 앱의 HTTP 서버.

Cloud Run 같은 컨테이너 플랫폼에서 실행하기 위한 최소 서버로, 표준 라이브러리만 사용한다.

- GET /         인사말과 배포 버전(JSON)
- GET /healthz  헬스체크용 상태(JSON)
"""

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from donga_app.main import greet

APP_VERSION = os.environ.get("APP_VERSION", "dev")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/healthz":
            self._send_json(200, {"status": "ok", "version": APP_VERSION})
        elif self.path == "/":
            self._send_json(200, {"message": greet(), "version": APP_VERSION})
        else:
            self._send_json(404, {"error": "not found"})

    def _send_json(self, status, body):
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        # 기본 접근 로그 대신 한 줄 형식으로 표준 출력에 남긴다 (Cloud Logging에서 수집)
        print(f"{self.command} {self.path} {args[1] if len(args) > 1 else ''}", flush=True)


def create_server(port):
    return ThreadingHTTPServer(("0.0.0.0", port), Handler)


def main():
    port = int(os.environ.get("PORT", "8080"))
    server = create_server(port)
    print(f"donga server listening on :{port} (version {APP_VERSION})", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
