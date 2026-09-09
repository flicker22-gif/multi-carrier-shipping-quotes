"""聚合报价服务：并发向多家运力取价，聚合后排序。"""

from concurrent.futures import ThreadPoolExecutor
import logging
import time

from .carriers.base import CarrierClient
from .geography import resolve_destination
from .models import Quote, QuoteRequest

logger = logging.getLogger("shipping")


class QuoteService:
    def __init__(
        self,
        carriers: list[CarrierClient],
        max_workers: int = 8,
        timeout: float = 5.0,
    ):
        self._carriers = {c.code: c for c in carriers}
        self._max_workers = max_workers
        self.timeout = timeout

    @property
    def carrier_codes(self) -> list[str]:
        return list(self._carriers)

    def quote(self, request: QuoteRequest) -> dict:
        # 分区解析在请求阶段完成，unknown 国家这里会抛 ValidationError
        route = resolve_destination(request.origin, request.destination)

        wanted = request.carriers
        if wanted:
            unknown = [c for c in wanted if c not in self._carriers]
            if unknown:
                raise ValueError(f"未知运力: {', '.join(unknown)}")
            carriers = [self._carriers[c] for c in dict.fromkeys(wanted)]
        else:
            carriers = list(self._carriers.values())

        start = time.perf_counter()
        quotes, errors = self._fetch_concurrently(carriers, request, route)
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

        if request.sort_by == "speed":
            # 先最快（承诺时效上界小者优先），同速则取更便宜
            quotes.sort(key=lambda q: (q.transit_max_days, q.price))
        else:
            # 先最便宜，同价取更快
            quotes.sort(key=lambda q: (q.price, q.transit_max_days))

        return {
            "route": route.description,
            "sort_by": request.sort_by,
            "count": len(quotes),
            "quotes": [q.to_dict() for q in quotes],
            "errors": errors,
            "elapsed_ms": elapsed_ms,
        }

    def _fetch_concurrently(
        self,
        carriers: list[CarrierClient],
        request: QuoteRequest,
        route,
    ) -> tuple[list[Quote], list[dict]]:
        """线程池并发取价；单个运力失败被收集进 errors，不影响整体。"""
        quotes: list[Quote] = []
        errors: list[dict] = []

        def _fetch(carrier: CarrierClient) -> tuple[str, list[Quote] | Exception]:
            try:
                return carrier.code, carrier.get_quotes(request, route)
            except Exception as exc:
                logger.warning("carrier %s quote failed: %s", carrier.code, exc)
                return carrier.code, exc

        with ThreadPoolExecutor(max_workers=self._max_workers) as pool:
            futures = [pool.submit(_fetch, c) for c in carriers]
            for future in futures:
                code, result = future.result(timeout=self.timeout)
                if isinstance(result, Exception):
                    errors.append({"carrier": code, "message": str(result)})
                else:
                    quotes.extend(result)
        return quotes, errors
