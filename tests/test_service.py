import unittest

from shipping.carriers import build_default_carriers
from shipping.carriers.base import CarrierClient, CarrierError
from shipping.models import (
    Address,
    Package,
    QuoteRequest,
)
from shipping.service import QuoteService

ORIGIN = Address("CN", "广东省", "深圳市", "南山区")
SMALL_1KG = Package(200, 150, 100, 1000)


def req(destination, package=SMALL_1KG, sort_by="price", carriers=None, origin=ORIGIN):
    return QuoteRequest(
        package=package,
        destination=destination,
        origin=origin,
        carriers=carriers,
        sort_by=sort_by,
    )


class QuoteServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = QuoteService(build_default_carriers())

    def _codes_prices(self, result):
        return [(q["carrier_code"], q["service_code"], q["price"]) for q in result["quotes"]]

    def test_same_city_sorted_by_price(self):
        result = self.service.quote(req(Address("CN", "广东省", "深圳市", "福田区")))
        self.assertEqual(result["route"], "同城")
        prices = [q["price"] for q in result["quotes"]]
        self.assertEqual(prices, sorted(prices))
        # 同城最便宜是圆通标准 8 元，排在第一
        self.assertEqual(result["quotes"][0]["carrier_code"], "yto")
        self.assertEqual(result["quotes"][0]["price"], 8.0)

    def test_cross_province_beijing(self):
        result = self.service.quote(req(Address("CN", "北京市", "北京市", "朝阳区")))
        self.assertIn("二区", result["route"])
        prices = [q["price"] for q in result["quotes"]]
        self.assertEqual(prices, sorted(prices))
        # 经济件最便宜：圆通经济包 10 元；时效件选顺丰标快
        cheapest = result["quotes"][0]
        self.assertEqual((cheapest["carrier_code"], cheapest["service_code"]),
                         ("yto", "yto_economy"))
        fastest = self.service.quote(
            req(Address("CN", "北京市", "北京市", "朝阳区"), sort_by="speed")
        )["quotes"][0]
        self.assertEqual((fastest["carrier_code"], fastest["service_code"]),
                         ("sf", "sf_standard"))
        self.assertEqual(fastest["transit_max_days"], 2)

    def test_remote_xinjiang_sf_fastest_yto_cheapest(self):
        result = self.service.quote(req(Address("CN", "新疆维吾尔自治区", "乌鲁木齐市")))
        self.assertIn("三区", result["route"])
        self.assertEqual(result["quotes"][0]["price"], 12.0)  # 圆通经济包
        by_speed = self.service.quote(
            req(Address("CN", "新疆", "乌鲁木齐市"), sort_by="speed")
        )
        self.assertEqual(by_speed["quotes"][0]["carrier_code"], "sf")
        self.assertEqual(by_speed["quotes"][0]["transit_max_days"], 3)
        # EMS 对偏远不额外抬价，18元首重，价格介于顺丰与圆通之间
        ems = [q for q in result["quotes"] if q["carrier_code"] == "ems"]
        self.assertEqual(ems[0]["price"], 18.0)

    def test_international_usa(self):
        result = self.service.quote(req(Address("US", "CA", "Los Angeles")))
        self.assertEqual(result["route"], "国际/北美")
        prices = [q["price"] for q in result["quotes"]]
        self.assertEqual(prices, sorted(prices))
        # e 邮宝只做国际且最便宜；圆通经济包无国际线，不出现在结果里
        cheapest = result["quotes"][0]
        self.assertEqual((cheapest["carrier_code"], cheapest["service_code"]),
                         ("ems", "ems_economy"))
        self.assertEqual(cheapest["price"], 60.0)
        # 按时效：顺丰标快 5-8 天最快
        fastest = self.service.quote(
            req(Address("美国", "", "洛杉矶"), sort_by="speed")
        )["quotes"][0]
        self.assertEqual((fastest["carrier_code"], fastest["service_code"]),
                         ("sf", "sf_standard"))

    def test_hong_kong_routes(self):
        result = self.service.quote(req(Address("香港")))
        self.assertEqual(result["route"], "国际/港澳台")
        self.assertTrue(result["quotes"])
        prices = [q["price"] for q in result["quotes"]]
        self.assertEqual(prices, sorted(prices))

    def test_volumetric_weight_changes_billing(self):
        # 40x40x40cm 的抛货，实重仅 2kg
        bulky = Package(400, 400, 400, 2000)
        result = self.service.quote(req(Address("CN", "浙江省", "杭州市"), package=bulky))
        billed = {q["carrier_code"]: q["billed_weight_kg"] for q in result["quotes"]}
        # 体积重：SF 64000/12000→6kg，EMS 64000/6000→11kg，YTO 64000/8000→8kg
        self.assertEqual(billed["sf"], 6)
        self.assertEqual(billed["ems"], 11)
        self.assertEqual(billed["yto"], 8)
        # 顺丰标快 = 18 + 5*6
        sf = next(q for q in result["quotes"] if q["service_code"] == "sf_standard")
        self.assertEqual(sf["price"], 48.0)

    def test_overweight_only_sf_freight_accepted(self):
        heavy = Package(400, 400, 400, 90_000)  # 90kg
        result = self.service.quote(req(Address("CN", "浙江省", "杭州市"), package=heavy))
        services = {(q["carrier_code"], q["service_code"]) for q in result["quotes"]}
        self.assertEqual(services, {("sf", "sf_freight")})

    def test_carrier_filter(self):
        result = self.service.quote(req(Address("CN", "浙江省", "杭州市"), carriers=["sf"]))
        self.assertTrue(result["quotes"])
        self.assertTrue(all(q["carrier_code"] == "sf" for q in result["quotes"]))
        with self.assertRaises(ValueError):
            self.service.quote(req(Address("CN", "浙江省", "杭州市"), carriers=["dhl"]))

    def test_one_carrier_failure_is_isolated(self):
        class BrokenCarrier(CarrierClient):
            code = "broken"
            name = "故障运力"
            products = ()

            def get_quotes(self, request, route):
                raise CarrierError("上游 503")

        service = QuoteService(build_default_carriers() + [BrokenCarrier()])
        result = service.quote(req(Address("CN", "浙江省", "杭州市")))
        self.assertTrue(result["quotes"])  # 其余运力报价不受影响
        self.assertEqual(result["errors"],
                         [{"carrier": "broken", "message": "上游 503"}])

    def test_no_quotes_for_unsupported_intl_product(self):
        # 圆通经济包只覆盖国内，国际目的地不应出现
        result = self.service.quote(req(Address("JP", "", "Tokyo")))
        self.assertFalse(
            any(q["service_code"] == "yto_economy" for q in result["quotes"])
        )
        self.assertTrue(any(q["carrier_code"] == "yto" for q in result["quotes"]))


if __name__ == "__main__":
    unittest.main()
