"""运力客户端基类与产品费率模型。"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from ..geography import Route
from ..models import Quote, QuoteRequest
from ..pricing import apply_fuel_surcharge, billable_weight_kg, continued_weight_price


class CarrierError(RuntimeError):
    """运力侧取价失败（网络错误、接口报错等）。"""


@dataclass(frozen=True)
class Rate:
    """某分区下的首重价 / 续重单价 / 时效。"""

    first_kg: float
    extra_per_kg: float
    min_days: int
    max_days: int


@dataclass(frozen=True)
class ProductSpec:
    """一个运力产品（如顺丰标快）的费率卡与收寄限制。"""

    service_code: str
    service_name: str
    volumetric_divisor: int
    max_weight_g: int
    max_side_mm: int
    rates: dict          # key: "same" / 国内 zone(1,2,3) / 国际分组名
    fuel_pct: float = 0.0

    def rate_for(self, route: Route) -> Optional[Rate]:
        if route.kind == "same_city":
            return self.rates.get("same")
        if route.kind == "domestic":
            return self.rates.get(route.zone)
        return self.rates.get(route.group)


class CarrierClient(ABC):
    """运力客户端。接入真实 API 时实现/覆盖 get_quotes 即可。"""

    code: str = ""
    name: str = ""
    products: tuple[ProductSpec, ...] = ()

    @abstractmethod
    def get_quotes(self, request: QuoteRequest, route: Route) -> list[Quote]:
        """返回该运力所有可承运产品的报价；不可承运的产品直接跳过。"""

    # ---- 给本地费率卡实现复用的通用流程 ----
    def _quote_from_rate_card(
        self, request: QuoteRequest, route: Route
    ) -> list[Quote]:
        package = request.package
        longest_side = max(
            package.length_mm, package.width_mm, package.height_mm
        )
        quotes: list[Quote] = []
        for product in self.products:
            rate = product.rate_for(route)
            if rate is None:
                continue  # 该产品不覆盖此路由分区
            if (
                package.weight_g > product.max_weight_g
                or longest_side > product.max_side_mm
            ):
                continue  # 超收寄限制，不可承运
            billed_kg = billable_weight_kg(package, product.volumetric_divisor)
            price = continued_weight_price(
                rate.first_kg, rate.extra_per_kg, billed_kg
            )
            price = apply_fuel_surcharge(price, product.fuel_pct)
            quotes.append(
                Quote(
                    carrier_code=self.code,
                    carrier_name=self.name,
                    service_code=product.service_code,
                    service_name=product.service_name,
                    price=price,
                    transit_min_days=rate.min_days,
                    transit_max_days=rate.max_days,
                    billed_weight_kg=billed_kg,
                )
            )
        return quotes
