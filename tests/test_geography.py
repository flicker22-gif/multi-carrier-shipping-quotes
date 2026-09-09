import unittest

from shipping.geography import domestic_zone, resolve_destination
from shipping.models import Address, ValidationError


class GeographyTests(unittest.TestCase):
    def test_domestic_zones(self):
        self.assertEqual(domestic_zone("广东省"), 1)
        self.assertEqual(domestic_zone("广东"), 1)
        self.assertEqual(domestic_zone("北京市"), 2)
        self.assertEqual(domestic_zone("新疆"), 3)
        self.assertEqual(domestic_zone("西藏自治区"), 3)

    def test_same_city(self):
        origin = Address("CN", "广东省", "深圳市", "南山区")
        dst = Address("CN", "广东省", "深圳市", "宝安区")
        route = resolve_destination(origin, dst)
        self.assertEqual(route.kind, "same_city")

    def test_domestic_cross_province(self):
        origin = Address("CN", "广东省", "深圳市", "南山区")
        route = resolve_destination(origin, Address("CN", "北京市", "北京市", "朝阳区"))
        self.assertEqual(route.kind, "domestic")
        self.assertEqual(route.zone, 2)

        route = resolve_destination(origin, Address("CN", "新疆维吾尔自治区", "乌鲁木齐市"))
        self.assertEqual(route.zone, 3)

    def test_international_groups(self):
        origin = Address(city="深圳市")
        self.assertEqual(
            resolve_destination(origin, Address("US", "加利福尼亚", "洛杉矶")).group,
            "north_america",
        )
        self.assertEqual(
            resolve_destination(origin, Address("日本", "", "东京")).group, "asia"
        )
        self.assertEqual(
            resolve_destination(origin, Address("香港")).group, "hk_mo_tw"
        )
        # 未收录的两位代码按“其他地区”兜底，不报错
        self.assertEqual(
            resolve_destination(origin, Address("BR")).group, "other"
        )

    def test_invalid_country(self):
        with self.assertRaises(ValidationError):
            resolve_destination(Address(city="深圳"), Address("火星", "", "基地"))

    def test_domestic_requires_province(self):
        with self.assertRaises(ValidationError):
            resolve_destination(Address(city="深圳"), Address("CN", "", "北京"))


if __name__ == "__main__":
    unittest.main()
