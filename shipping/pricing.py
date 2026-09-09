"""计价工具：体积重、计费重、首重+续重阶梯价。"""

import math

from .models import Package

# 各运力体积重除数不同（cm³/kg），在产品费率卡里指定
# 顺丰 12000，EMS 6000，圆通 8000 等


def volumetric_weight_kg(package: Package, divisor: int) -> float:
    """体积重 = 长*宽*高(cm³) / 除数。"""
    volume_cm3 = (
        package.length_mm
        * package.width_mm
        * package.height_mm
        / 1000.0  # mm³ -> cm³
    )
    return volume_cm3 / divisor


def billable_weight_kg(package: Package, divisor: int) -> float:
    """计费重取实际重与体积重的较大值，向上取整到 kg。"""
    actual_kg = package.weight_g / 1000.0
    vol_kg = volumetric_weight_kg(package, divisor)
    return float(max(math.ceil(actual_kg), math.ceil(vol_kg)))


def continued_weight_price(
    first_kg_price: float,
    extra_per_kg: float,
    billed_weight_kg: float,
) -> float:
    """首重 1kg 价 + 续重单价 * (计费重 - 1)，续重不足 1kg 按 1kg 计。"""
    extra_kg = max(0, math.ceil(billed_weight_kg) - 1)
    return round(first_kg_price + extra_per_kg * extra_kg, 2)


def apply_fuel_surcharge(price: float, fuel_pct: float) -> float:
    if not fuel_pct:
        return price
    return round(price * (1 + fuel_pct / 100), 2)
