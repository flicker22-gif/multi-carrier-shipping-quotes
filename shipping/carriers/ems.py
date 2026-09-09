"""EMS（模拟公开费率卡）。

国际线路覆盖最全，国内偏远地区（新疆/西藏）是优势产品；
体积重除数 6000（抛货更吃亏）。
"""

from ..geography import Route
from ..models import Quote, QuoteRequest
from .base import CarrierClient, ProductSpec, Rate


class EMSCarrier(CarrierClient):
    code = "ems"
    name = "中国邮政 EMS"

    products = (
        ProductSpec(
            service_code="ems_standard",
            service_name="EMS 标准快递",
            volumetric_divisor=6000,
            max_weight_g=40_000,
            max_side_mm=1500,
            rates={
                "same": Rate(10.0, 1.0, 1, 2),
                1: Rate(12.0, 3.0, 2, 3),
                2: Rate(15.0, 5.0, 2, 4),
                3: Rate(18.0, 6.0, 3, 5),  # 偏远覆盖强、不加价
                "hk_mo_tw": Rate(28.0, 10.0, 3, 5),
                "asia": Rate(70.0, 22.0, 4, 7),
                "north_america": Rate(120.0, 38.0, 7, 10),
                "europe": Rate(130.0, 40.0, 7, 12),
                "oceania": Rate(120.0, 38.0, 7, 12),
                "other": Rate(160.0, 50.0, 8, 15),  # 覆盖最广
            },
        ),
        ProductSpec(
            service_code="ems_economy",
            service_name="EMS 国际 e 邮宝",
            volumetric_divisor=8000,
            max_weight_g=20_000,
            max_side_mm=1000,
            rates={
                "asia": Rate(45.0, 12.0, 7, 15),
                "north_america": Rate(60.0, 18.0, 10, 20),
                "europe": Rate(65.0, 20.0, 10, 20),
                "oceania": Rate(60.0, 18.0, 10, 20),
            },
        ),
    )

    def get_quotes(self, request: QuoteRequest, route: Route) -> list[Quote]:
        # 真实接入：https://www.ems.com.cn/ 开放接口（需客户代码）
        return self._quote_from_rate_card(request, route)
