"""
Data structures for Lambda-native requests.

Replaces starlette.datastructures with Lambda-compatible implementations.
Original: https://github.com/encode/starlette/blob/master/starlette/datastructures.py
"""

from typing import NamedTuple, Optional


class Address(NamedTuple):
    """Client address (compatible with Starlette) - named tuple with host and port."""

    host: Optional[str]
    port: int = 0
