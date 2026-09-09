"""请求 / 报价数据模型与入参校验。"""

from dataclasses import dataclass, field
from typing import Any, Optional


class ValidationError(ValueError):
    """入参不合法（对应 HTTP 400）。"""


@dataclass(frozen=True)
class Package:
    """包裹信息，尺寸单位 mm，重量单位 g。"""

    length_mm: float
    width_mm: float
    height_mm: float
    weight_g: float

    @classmethod
    def from_dict(cls, data: Any) -> "Package":
        if not isinstance(data, dict):
            raise ValidationError("package 必须是对象")
        try:
            length = float(data["length_mm"])
            width = float(data["width_mm"])
            height = float(data["height_mm"])
            weight_g = float(data["weight_g"])
        except KeyError as exc:
            raise ValidationError(f"package 缺少字段: {exc.args[0]}") from None
        except (TypeError, ValueError):
            raise ValidationError("package 的尺寸和重量必须是数字") from None

        for name, value in (
            ("length_mm", length),
            ("width_mm", width),
            ("height_mm", height),
        ):
            if not 0 < value <= 5000:
                raise ValidationError(f"{name} 必须在 (0, 5000] mm 之间")
        if not 0 < weight_g <= 100_000:
            raise ValidationError("weight_g 必须在 (0, 100000] g 之间")
        return cls(length, width, height, weight_g)

    def to_dict(self) -> dict:
        return {
            "length_mm": self.length_mm,
            "width_mm": self.width_mm,
            "height_mm": self.height_mm,
            "weight_g": self.weight_g,
        }


@dataclass(frozen=True)
class Address:
    """收/发件地址。country 留空按中国大陆 CN 处理。"""

    country: str = "CN"
    province: str = ""
    city: str = ""
    district: str = ""

    @classmethod
    def from_dict(cls, data: Any) -> "Address":
        if data is None:
            return cls()
        if not isinstance(data, dict):
            raise ValidationError("地址必须是对象")
        return cls(
            country=str(data.get("country") or "CN").strip(),
            province=str(data.get("province") or "").strip(),
            city=str(data.get("city") or "").strip(),
            district=str(data.get("district") or "").strip(),
        )

    def to_dict(self) -> dict:
        return {
            "country": self.country,
            "province": self.province,
            "city": self.city,
            "district": self.district,
        }


@dataclass(frozen=True)
class QuoteRequest:
    package: Package
    destination: Address
    origin: Address = field(default_factory=lambda: Address("CN", "广东省", "深圳市", "南山区"))
    carriers: Optional[tuple[str, ...]] = None  # None = 全部运力
    sort_by: str = "price"  # price | speed

    @classmethod
    def from_dict(cls, data: Any) -> "QuoteRequest":
        if not isinstance(data, dict):
            raise ValidationError("请求体必须是 JSON 对象")
        if "destination" not in data:
            raise ValidationError("缺少 destination")
        package = Package.from_dict(data.get("package"))
        destination = Address.from_dict(data["destination"])
        origin = Address.from_dict(data.get("origin")) if data.get("origin") else Address()

        carriers = data.get("carriers")
        if carriers is not None:
            if not isinstance(carriers, list) or not carriers:
                raise ValidationError("carriers 必须是非空数组")
            carriers = tuple(str(c).strip().lower() for c in carriers)

        sort_by = str(data.get("sort_by", "price")).strip().lower()
        if sort_by not in ("price", "speed"):
            raise ValidationError("sort_by 只支持 price / speed")
        return cls(package, destination, origin, carriers, sort_by)


@dataclass(frozen=True)
class Quote:
    """单个运力产品的报价。"""

    carrier_code: str
    carrier_name: str
    service_code: str
    service_name: str
    price: float
    transit_min_days: int
    transit_max_days: int
    billed_weight_kg: float
    currency: str = "CNY"

    def to_dict(self) -> dict:
        return {
            "carrier_code": self.carrier_code,
            "carrier_name": self.carrier_name,
            "service_code": self.service_code,
            "service_name": self.service_name,
            "price": self.price,
            "currency": self.currency,
            "transit_min_days": self.transit_min_days,
            "transit_max_days": self.transit_max_days,
            "billed_weight_kg": self.billed_weight_kg,
        }
