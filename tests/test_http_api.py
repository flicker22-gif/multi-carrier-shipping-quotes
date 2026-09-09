import json
import threading
import unittest
import urllib.error
import urllib.request

from shipping.http_app import make_server


class HTTPApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = make_server("127.0.0.1", 0)
        cls.base = f"http://127.0.0.1:{cls.httpd.server_address[1]}"
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def _post(self, payload):
        req = urllib.request.Request(
            self.base + "/v1/quotes",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))

    def _get(self, path):
        with urllib.request.urlopen(self.base + path, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))

    BASE_BODY = {
        "package": {"length_mm": 200, "width_mm": 150, "height_mm": 100, "weight_g": 1000},
        "origin": {"country": "CN", "province": "广东省", "city": "深圳市"},
        "destination": {"country": "CN", "province": "北京市", "city": "北京市"},
    }

    def test_health(self):
        status, body = self._get("/v1/health")
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ok")
        self.assertEqual(set(body["carriers"]), {"sf", "ems", "yto"})

    def test_quotes_end_to_end_default_sort_price(self):
        status, body = self._post(self.BASE_BODY)
        self.assertEqual(status, 200)
        self.assertEqual(body["route"], "国内/二区(跨省)")
        self.assertEqual(body["sort_by"], "price")
        prices = [q["price"] for q in body["quotes"]]
        self.assertEqual(prices, sorted(prices))
        self.assertEqual(body["quotes"][0]["carrier_code"], "yto")
        self.assertEqual(body["errors"], [])
        self.assertIsInstance(body["elapsed_ms"], (int, float))

    def test_quotes_sort_by_speed(self):
        body_req = dict(self.BASE_BODY, sort_by="speed")
        status, body = self._post(body_req)
        self.assertEqual(status, 200)
        max_days = [q["transit_max_days"] for q in body["quotes"]]
        self.assertEqual(max_days, sorted(max_days))
        self.assertEqual(body["quotes"][0]["carrier_code"], "sf")

    def test_international_destination(self):
        payload = {
            **self.BASE_BODY,
            "destination": {"country": "US", "city": "Los Angeles"},
        }
        status, body = self._post(payload)
        self.assertEqual(status, 200)
        self.assertEqual(body["route"], "国际/北美")
        self.assertTrue(body["count"] >= 3)

    def test_bad_dimensions_returns_400(self):
        payload = {
            **self.BASE_BODY,
            "package": {"length_mm": -1, "width_mm": 150, "height_mm": 100, "weight_g": 1000},
        }
        status, body = self._post(payload)
        self.assertEqual(status, 400)
        self.assertEqual(body["error"], "validation_error")

    def test_missing_destination_returns_400(self):
        status, body = self._post({"package": self.BASE_BODY["package"]})
        self.assertEqual(status, 400)

    def test_invalid_json_returns_400(self):
        req = urllib.request.Request(
            self.base + "/v1/quotes",
            data=b"{not json",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.assertRaises(urllib.error.HTTPError) as cm:
            urllib.request.urlopen(req, timeout=5)
        self.assertEqual(cm.exception.code, 400)

    def test_unknown_route_returns_404(self):
        with self.assertRaises(urllib.error.HTTPError) as cm:
            urllib.request.urlopen(self.base + "/v1/nope", timeout=5)
        self.assertEqual(cm.exception.code, 404)

    def test_unknown_carrier_returns_400(self):
        status, body = self._post({**self.BASE_BODY, "carriers": ["dhl"]})
        self.assertEqual(status, 400)


if __name__ == "__main__":
    unittest.main()
