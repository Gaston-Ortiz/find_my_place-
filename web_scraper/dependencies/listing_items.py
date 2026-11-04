"""Items yielded by the listings spider and stored by the Postgres pipeline."""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ApiPageItem:
    """One /api/busqueda response, stored as returned in `raw_api_responses`."""

    category: int
    page: int
    request_params: dict[str, Any]
    http_status: int
    response: Optional[dict[str, Any]]


@dataclass
class ListingItem:
    """Column values for one ad in `listings`.

    `values` only holds the columns this crawl filled: when the ad page was not
    fetched (`has_detail` False), the columns that come from it keep their stored
    values.
    """

    category: int
    values: dict[str, Any]
    field_sources: dict[str, str] = field(default_factory=dict)
    has_detail: bool = False
