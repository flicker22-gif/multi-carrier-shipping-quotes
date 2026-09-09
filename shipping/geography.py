"""地址归一化、国内分区与国际分区。

真实场景这里的数据一般来自行政区表 / 运力分区表；
当前用可维护的字典覆盖常见目的地，未知省份按最远区兜底，
未知国家直接报错，避免静默给出错误报价。
"""

from dataclasses import dataclass

from .models import Address, ValidationError

# ---- 国家 / 地区别名 -------------------------------------------------------

COUNTRY_ALIASES = {
    "中国": "CN", "中国内地": "CN", "中国大陆": "CN", "国内": "CN", "cn": "CN",
    "香港": "HK", "香港特别行政区": "HK", "hk": "HK",
    "澳门": "MO", "澳门特别行政区": "MO", "mo": "MO",
    "台湾": "TW", "中国台湾": "TW", "tw": "TW",
    "美国": "US", "美利坚合众国": "US", "us": "US", "usa": "US",
    "加拿大": "CA", "ca": "CA",
    "日本": "JP", "jp": "JP",
    "韩国": "KR", "kr": "KR",
    "新加坡": "SG", "sg": "SG",
    "泰国": "TH", "th": "TH",
    "马来西亚": "MY", "my": "MY",
    "英国": "GB", "gb": "GB", "uk": "GB",
    "德国": "DE", "de": "DE",
    "法国": "FR", "fr": "FR",
    "俄罗斯": "RU", "ru": "RU",
    "澳大利亚": "AU", "澳洲": "AU", "au": "AU",
}

# ---- 国内省份分区（以华南出发为基准）--------------------------------------
# zone 1: 周边一区；zone 2: 跨省二区；zone 3: 偏远三区

_ZONE1 = {
    "广东省", "广西壮族自治区", "福建省", "湖南省", "江西省", "海南省",
}
_ZONE2 = {
    "北京市", "天津市", "上海市", "重庆市", "河北省", "山西省",
    "江苏省", "浙江省", "安徽省", "山东省", "河南省", "湖北省",
    "四川省", "贵州省", "云南省", "陕西省",
}
_ZONE3 = {
    "辽宁省", "吉林省", "黑龙江省", "内蒙古自治区", "甘肃省",
    "宁夏回族自治区", "青海省", "西藏自治区", "新疆维吾尔自治区",
}

PROVINCE_ALIASES = {
    "北京": "北京市", "天津": "天津市", "上海": "上海市", "重庆": "重庆市",
    "河北": "河北省", "山西": "山西省", "辽宁": "辽宁省", "吉林": "吉林省",
    "黑龙江": "黑龙江省", "江苏": "江苏省", "浙江": "浙江省", "安徽": "安徽省",
    "福建": "福建省", "江西": "江西省", "山东": "山东省", "河南": "河南省",
    "湖北": "湖北省", "湖南": "湖南省", "广东": "广东省", "海南": "海南省",
    "四川": "四川省", "贵州": "贵州省", "云南": "云南省", "陕西": "陕西省",
    "甘肃": "甘肃省", "青海": "青海省",
    "内蒙": "内蒙古自治区", "内蒙古": "内蒙古自治区",
    "广西": "广西壮族自治区", "西藏": "西藏自治区",
    "宁夏": "宁夏回族自治区", "新疆": "新疆维吾尔自治区",
}

ZONE_NAMES = {
    "same": "同城",
    1: "一区(周边)",
    2: "二区(跨省)",
    3: "三区(偏远)",
}

# ---- 国际分组 --------------------------------------------------------------

_INTL_GROUPS = {
    "HK": "hk_mo_tw", "MO": "hk_mo_tw", "TW": "hk_mo_tw",
    "JP": "asia", "KR": "asia", "SG": "asia", "TH": "asia", "MY": "asia",
    "GB": "europe", "DE": "europe", "FR": "europe", "RU": "europe",
    "US": "north_america", "CA": "north_america",
    "AU": "oceania",
}
INTL_GROUP_NAMES = {
    "hk_mo_tw": "港澳台",
    "asia": "亚洲",
    "europe": "欧洲",
    "north_america": "北美",
    "oceania": "大洋洲",
    "other": "其他地区",
}


@dataclass(frozen=True)
class Route:
    kind: str          # same_city | domestic | international
    zone: int | None   # 国内分区
    group: str | None  # 国际分组
    description: str


def normalize_country(raw: str) -> str:
    value = (raw or "").strip()
    if not value:
        return "CN"
    upper = value.upper()
    if upper in set(COUNTRY_ALIASES.values()):
        return upper
    code = COUNTRY_ALIASES.get(value.lower())
    if code:
        return code
    # 未收录但形如 ISO 两位代码：按国际“其他地区”分组保守处理
    if len(value) == 2 and value.isascii() and value.isalpha():
        return upper
    raise ValidationError(f"暂不支持的目的地国家/地区: {value}")


def normalize_province(raw: str) -> str:
    value = (raw or "").strip()
    if not value:
        raise ValidationError("国内目的地必须填写 province")
    if value in PROVINCE_ALIASES.values():
        return value
    return PROVINCE_ALIASES.get(value, value)


def normalize_city(raw: str) -> str:
    return (raw or "").strip().removesuffix("市")


def domestic_zone(province: str) -> int:
    canonical = normalize_province(province)
    if canonical in _ZONE1:
        return 1
    if canonical in _ZONE2:
        return 2
    if canonical in _ZONE3:
        return 3
    # 未收录的省份按最远分区保守计价
    return 3


def international_group(country_code: str) -> str:
    return _INTL_GROUPS.get(country_code, "other")


def resolve_destination(origin: Address, destination: Address) -> Route:
    """把一对收发件地址解析成报价用的路由分区。"""
    dst_country = normalize_country(destination.country)
    src_country = normalize_country(origin.country)

    if dst_country != "CN":
        if src_country != "CN":
            raise ValidationError("当前仅支持从中国大陆发件")
        group = international_group(dst_country)
        return Route(
            kind="international",
            zone=None,
            group=group,
            description=f"国际/{INTL_GROUP_NAMES[group]}",
        )

    province = normalize_province(destination.province)
    same_city = bool(
        origin.country == "CN"
        and normalize_city(origin.city)
        and normalize_city(origin.city) == normalize_city(destination.city)
    )
    if same_city:
        return Route("same_city", None, None, ZONE_NAMES["same"])

    zone = domestic_zone(province)
    return Route("domestic", zone, None, f"国内/{ZONE_NAMES[zone]}")
