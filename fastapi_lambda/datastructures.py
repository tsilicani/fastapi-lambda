"""
Data structures for Lambda-native requests.

Replaces starlette.datastructures with Lambda-compatible implementations.
Original: https://github.com/encode/starlette/blob/master/starlette/datastructures.py
"""

from typing import NamedTuple, Optional


class Address(NamedTuple):
    """Client address (compatible with Starlette) - named tuple with host and port."""

    host: Optional[str]
    """Host IP address."""
    port: int = 0
    """Port is always 0 as it's not provided by API Gateway."""
