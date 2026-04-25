from __future__ import annotations

from .base import ConflictProfile


PROFILE = ConflictProfile(
    name="manufacturing",
    synonyms={
        # qty
        "số lượng": "qty",
        "so luong": "qty",
        "数量": "qty",
        "quantity": "qty",
        # stock
        "tồn kho": "stock",
        "ton kho": "stock",
        "在庫": "stock",
        "inventory": "stock",
        # capacity
        "công suất": "capacity",
        "cong suat": "capacity",
        "能力": "capacity",
        # station
        "trạm": "station",
        "tram": "station",
        "工位": "station",
        "cell": "station",
        # step / process
        "công đoạn": "step",
        "cong doan": "step",
        "工程": "step",
        "process": "step",
        # leadtime
        "lead time": "leadtime",
        "納期": "leadtime",
        "lt": "leadtime",
    },
    comparable_numeric_keys=frozenset(
        {
            "qty",
            "version",
            "warehouse_id",
            "station",
            "leadtime",
            "capacity",
            "date_effective",
            "stock",
            "step",
            "limit",
            "days",
            "hours",
        }
    ),
    ignore_numeric_contexts=frozenset(
        {
            "page",
            "line",
            "manifest",
            "section",
            "year",
            "copyright",
            "source",
            "ref",
            "timestamp",
            "id",
        }
    ),
)
