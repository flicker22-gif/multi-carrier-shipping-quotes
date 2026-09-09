# 快递聚合报价服务

输入包裹尺寸/重量和收寄地址，并发向多家运力（顺丰、EMS、圆通）取价，
返回按**价格**或**时效**排好序的报价列表。纯 Python 3.11 标准库实现，零三方依赖。

> 各家快递官网/开放平台均需账号鉴权、无统一公开询价接口，当前三家运力以
> **本地模拟费率卡**实现（覆盖同城/国内分区/国际分组）。接入真实 API 时只需
> 替换 `shipping/carriers/*.py` 中 `get_quotes()` 的实现（HTTP 层、聚合层无需改动）。

## 启动

```bash
python3 app.py 8000        # 默认 8000
```

## 接口

### POST /v1/quotes

请求：

```json
{
  "package": {"length_mm": 300, "width_mm": 200, "height_mm": 200, "weight_g": 2000},
  "origin":      {"country": "CN", "province": "广东省", "city": "深圳市"},
  "destination": {"country": "CN", "province": "北京市", "city": "北京市"},
  "sort_by": "price",
  "carriers": ["sf", "ems", "yto"]
}
```

- `package` 必填，尺寸 mm（0–5000），重量 g（0–100000）
- `origin` 可省略，默认广东深圳南山
- `sort_by`：`price`（默认，价低优先）/ `speed`（时效上界短优先）
- `carriers`：可省略表示全部

响应：

```json
{
  "route": "国内/二区(跨省)",
  "sort_by": "price",
  "count": 5,
  "quotes": [
    {"carrier_code": "yto", "carrier_name": "圆通速递", "service_code": "yto_economy",
     "service_name": "圆通经济包", "price": 12.5, "currency": "CNY",
     "transit_min_days": 3, "transit_max_days": 5, "billed_weight_kg": 2.0}
  ],
  "errors": [],
  "elapsed_ms": 2.84
}
```

单个运力取价失败会被隔离进 `errors`，不影响其余运力报价。

### GET /v1/health

```json
{"status": "ok", "carriers": ["sf", "ems", "yto"]}
```

## 计价规则

- 国内按 同城 / 一区(周边省份) / 二区(跨省) / 三区(新疆西藏等偏远) 分区
- 国际按 港澳台 / 亚洲 / 欧洲 / 北美 / 大洋洲 / 其他 分组
- 计费重 = max(实际重, 体积重) 向上取整到 kg；体积重 = 长×宽×高(cm³)/除数
  （顺丰 12000、圆通 8000、EMS 6000，抛货规则各不相同）
- 价格 = 首重 1kg + 续重单价 ×（计费重−1）；超出产品收寄限制的运力自动剔除

## 典型目的地实测结果（2kg，30×20×20cm，深圳发）

| 目的地 | 最便宜 | 最快 |
|---|---|---|
| 深圳同城 | 圆通标准 ￥9 | 顺丰标快 1天 |
| 北京（二区） | 圆通经济包 ￥12.5 | 顺丰标快 1–2天 |
| 乌鲁木齐（三区） | 圆通经济包 ￥16 | 顺丰标快 2–3天 |
| 美国洛杉矶 | EMS e邮宝 ￥78 | 顺丰标快 5–8天 |

## 测试

```bash
python3 -m unittest discover -s tests -v
```

29 个用例：计价（体积重/首续重）、分区解析、聚合排序、运力故障隔离、
超限收寄、HTTP 端到端（含 400/404 校验）。

## 代码结构

```
shipping/
  models.py        # 请求/报价模型与入参校验
  geography.py     # 地址归一化、国内分区、国际分组
  pricing.py       # 体积重/计费重/首续重计价
  carriers/        # 各运力客户端（真实 API 的替换点）
    base.py        #   基类 + 产品费率卡
    sf.py ems.py yto.py
  service.py       # 线程池并发取价、错误隔离、排序
  http_app.py      # stdlib HTTP 接口
tests/             # unittest 用例
app.py             # 入口
```
