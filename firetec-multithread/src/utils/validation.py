"""Validações de entrada e normalização de dados."""
from typing import Iterable, List


def parse_switch_ips(value: str, default: List[str]) -> List[str]:
    if not value:
        return default
    ips = [item.strip() for item in value.split(",") if item.strip()]
    return ips or default


def unique_preserve_order(items: Iterable[str]) -> List[str]:
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
