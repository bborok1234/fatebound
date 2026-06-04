"""콘텐츠 로더 — 번들된 data/*.json을 읽어 인덱스 제공(SSOT는 JSON, 20 §6)."""
from __future__ import annotations
import json
from pathlib import Path
from functools import lru_cache

_DATA = Path(__file__).parent / "data"


def _load(name: str):
    with open(_DATA / name, encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def items() -> list[dict]:
    return _load("items.json")


@lru_cache(maxsize=1)
def monsters() -> list[dict]:
    return _load("monsters.json")


@lru_cache(maxsize=1)
def zones() -> list[dict]:
    return _load("zones.json")


@lru_cache(maxsize=1)
def events() -> list[dict]:
    try:
        return _load("events.json")
    except FileNotFoundError:
        return []


def items_for_build(build: str) -> list[dict]:
    return [it for it in items() if it.get("build") == build]


def item_by_id(item_id: str) -> dict | None:
    return next((it for it in items() if it.get("item_id") == item_id), None)


def monsters_for_zone(zone_id: str) -> list[dict]:
    return [m for m in monsters() if m.get("zone_id") == zone_id]


def zone_by_id(zone_id: str) -> dict | None:
    return next((z for z in zones() if z.get("zone_id") == zone_id), None)


def events_for_zone(zone_id: str) -> list[dict]:
    return [e for e in events() if e.get("zone") in (zone_id, "any")]
