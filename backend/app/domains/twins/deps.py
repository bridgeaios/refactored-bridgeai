"""FastAPI Depends() factories for the twins domain."""
from __future__ import annotations
from functools import lru_cache
from app.domains.twins.services import TwinsServices


@lru_cache(maxsize=1)
def _twins_singleton() -> TwinsServices:
    return TwinsServices()


def get_twins() -> TwinsServices:
    return _twins_singleton()
