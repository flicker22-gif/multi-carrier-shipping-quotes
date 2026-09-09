import unittest

from shipping.models import Package
from shipping.pricing import (
    apply_fuel_surcharge,
    billable_weight_kg,
    continued_weight_price,
    volumetric_weight_kg,
)


class PricingTests(unittest.TestCase):
    def test_volumetric_weight(self):
        # 30*20*20 cm = 12000 cm³
        pkg = Package(300, 200, 200, 1500)
        self.assertAlmostEqual(volumetric_weight_kg(pkg, 12000), 1.0)
        self.assertAlmostEqual(volumetric_weight_kg(pkg, 6000), 2.0)
        self.assertAlmostEqual(volumetric_weight_kg(pkg, 8000), 1.5)

    def test_billable_weight_takes_heavier_and_rounds_up(self):
        # 实重 1.5kg、体积重 0.25kg -> 按实重向上取整 2kg
        dense = Package(200, 150, 100, 1500)
        self.assertEqual(billable_weight_kg(dense, 12000), 2)

        # 抛货：实重 0.8kg，体积重 1.5kg(/8000) -> 2kg
        bulky = Package(300, 200, 200, 800)
        self.assertEqual(billable_weight_kg(bulky, 8000), 2)
        # 同包裹用顺丰除数 12000 -> 体积重 1kg，按实重向上取整 1kg
        self.assertEqual(billable_weight_kg(bulky, 12000), 1)

    def test_continued_weight_price(self):
        self.assertEqual(continued_weight_price(12, 2, 1), 12)       # 首重
        self.assertEqual(continued_weight_price(12, 2, 2), 14)       # 1 个续重
        self.assertEqual(continued_weight_price(18, 6, 3), 30)       # 2 个续重
        self.assertEqual(continued_weight_price(18, 6, 3.2), 36)     # ceil 后 3 续重

    def test_fuel_surcharge(self):
        self.assertEqual(apply_fuel_surcharge(100, 0), 100)
        self.assertEqual(apply_fuel_surcharge(100, 10), 110)
        self.assertEqual(apply_fuel_surcharge(99.99, 8), 107.99)


if __name__ == "__main__":
    unittest.main()
