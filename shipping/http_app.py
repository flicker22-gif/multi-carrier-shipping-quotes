"""HTTP 接口（标准库 http.server 实现）。

POST /v1/quotes   聚合报价
GET  /v1/health   健康检查 / 已接入运力列表
"""

import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .carriers import build_default_carriers
from .models import QuoteRequest, ValidationError
from .service import QuoteService

logger = logging.getLogger("shipping")

MAX_BODY_BYTES = 64 * 1024


class QuoteHTTPHandler(BaseHTTPRequestHandler):
    server_version = "ShippingQuote/1.0"
    service: QuoteService = None  # 由 make_server 注入

    # ---- 工具 ----
    def _write_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        logger.info("%s - %s", self.address_string(), fmt % args)

    # ---- 路由 ----
    def do_GET(self):
        if self.path.split("?")[0] == "/v1/health":
            self._write_json(200, {
                "status": "ok",
                "carriers": self.service.carrier_codes,
            })
        else:
            self._write_json(404, {"error": "not_found", "message": self.path})

    def do_POST(self):
        if self.path.split("?")[0] != "/v1/quotes":
            self._write_json(404, {"error": "not_found", "message": self.path})
            return
        self._handle_quotes()

    def _handle_quotes(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            self._write_json(400, {"error": "bad_request", "message": "非法 Content-Length"})
            return
        if length <= 0:
            self._write_json(400, {"error": "bad_request", "message": "请求体为空"})
            return
        if length > MAX_BODY_BYTES:
            self._write_json(413, {"error": "payload_too_large", "message": "请求体超过 64KB"})
            return

        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._write_json(400, {"error": "bad_request", "message": "请求体不是合法 JSON"})
            return

        try:
            request = QuoteRequest.from_dict(data)
            result = self.service.quote(request)
        except ValidationError as exc:
            self._write_json(400, {"error": "validation_error", "message": str(exc)})
            return
        except ValueError as exc:  # 未知运力等
            self._write_json(400, {"error": "validation_error", "message": str(exc)})
            return
        except Exception:
            logger.exception("quote failed")
            self._write_json(500, {"error": "internal_error", "message": "服务内部错误"})
            return

        self._write_json(200, result)


def make_server(host: str = "0.0.0.0", port: int = 8000) -> ThreadingHTTPServer:
    service = QuoteService(build_default_carriers())

    class _Handler(QuoteHTTPHandler):
        pass

    _Handler.service = service
    httpd = ThreadingHTTPServer((host, port), _Handler)
    return httpd


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    import sys

    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    httpd = make_server("0.0.0.0", port)
    logger.info("报价服务启动: http://0.0.0.0:%d/v1/quotes", port)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.shutdown()


if __name__ == "__main__":
    main()
