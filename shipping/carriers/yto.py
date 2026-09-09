"""圆通速递（模拟公开费率卡）。

国内经济型最便宜，时效稍慢；国际线路覆盖有限。
"""

from ..geography import Route
from ..models import Quote, QuoteRequest
from .base import CarrierClient, ProductSpec, Rate


class YTOCarrier(CarrierClient):
    code = "yto"
    name = "圆通速递"

    products = (
        ProductSpec(
            service_code="yto_standard",
            service_name="圆通标准快递",
            volumetric_divisor=8000,
            max_weight_g=50_000,
            max_side_mm=1200,
            rates={
                "same": Rate(8.0, 1.0, 1, 2),
                1: Rate(10.0, 2.0, 2, 3),
                2: Rate(12.0, 3.5, 2, 4),
                3: Rate(15.0, 5.0, 3, 6),
                "hk_mo_tw": Rate(25.0, 8.0, 3, 5),
                "asia": Rate(65.0, 20.0, 5, 9),
                "north_america": Rate(110.0, 35.0, 7, 12),
                "europe": Rate(115.0, 36.0, 8, 14),
            },
        ),
        ProductSpec(
            service_code="yto_economy",
            service_name="圆通经济包",
            volumetric_divisor=8000,
            max_weight_g=30_000,
            max_side_mm=1000,
            rates={
                1: Rate(8.0, 1.5, 3, 5),
                2: Rate(10.0, 2.5, 3, 5),
                3: Rate(12.0, 4.0, 4, 7),
            },
        ),
    )

    def get_quotes(self, request: QuoteRequest, route: Route) -> list[Quote]:
        # 真实接入：圆通开放平台下单询价接口（需 appkey）
        return self._quote_from_rate_card(request, route)
