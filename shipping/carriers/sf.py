"""顺丰（模拟公开费率卡）。"""

from ..geography import Route
from ..models import Quote, QuoteRequest
from .base import CarrierClient, ProductSpec, Rate


class SFCarrier(CarrierClient):
    code = "sf"
    name = "顺丰速运"

    # 顺丰标快：首重/续重价偏高，时效快；体积重除数 12000
    # 顺丰卡航：陆运，便宜但慢，仅国内
    products = (
        ProductSpec(
            service_code="sf_standard",
            service_name="顺丰标快",
            volumetric_divisor=12000,
            max_weight_g=80_000,
            max_side_mm=1500,
            rates={
                "same": Rate(12.0, 2.0, 1, 1),
                1: Rate(14.0, 4.0, 1, 2),
                2: Rate(18.0, 6.0, 1, 2),
                3: Rate(22.0, 9.0, 2, 3),
                "hk_mo_tw": Rate(30.0, 12.0, 2, 4),
                "asia": Rate(80.0, 25.0, 3, 5),
                "north_america": Rate(150.0, 45.0, 5, 8),
                "europe": Rate(160.0, 48.0, 6, 9),
                "oceania": Rate(140.0, 42.0, 6, 9),
                "other": Rate(200.0, 60.0, 7, 12),
            },
        ),
        ProductSpec(
            service_code="sf_freight",
            service_name="顺丰卡航",
            volumetric_divisor=12000,
            max_weight_g=100_000,
            max_side_mm=3000,
            rates={
                "same": Rate(10.0, 1.5, 1, 2),
                1: Rate(12.0, 2.5, 2, 3),
                2: Rate(15.0, 4.0, 2, 4),
                3: Rate(18.0, 6.0, 3, 5),
            },
        ),
    )

    def get_quotes(self, request: QuoteRequest, route: Route) -> list[Quote]:
        # 真实接入：POST https://open.sf-express.com/...（需签名鉴权）
        return self._quote_from_rate_card(request, route)
