"""运力客户端：每家运力一个实现。

当前三个实现走本地费率卡（MockCarrierClient 风格），接口边界与将来
调用各家官网/开放平台完全一致——接入真实报价时只需替换 get_quotes
内部实现（如 httpx 调顺丰开放平台、EMS 下单询价接口），
服务层和 HTTP 层无需改动。
"""

from .base import CarrierClient, CarrierError, ProductSpec, Rate
from .sf import SFCarrier
from .ems import EMSCarrier
from .yto import YTOCarrier


def build_default_carriers() -> list[CarrierClient]:
    return [SFCarrier(), EMSCarrier(), YTOCarrier()]


__all__ = [
    "CarrierClient",
    "CarrierError",
    "ProductSpec",
    "Rate",
    "SFCarrier",
    "EMSCarrier",
    "YTOCarrier",
    "build_default_carriers",
]
